
import io
import json
from datetime import datetime

import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt

from modules.data_handler import (
    load_data, save_data, add_record, update_record, delete_record, merge_import,
    clear_all, drop_duplicates_keep_first, reassign_ids, ensure_data_dir, make_backup,
    CSV_PATH, CATEGORY_OPTIONS, COLUMNS, DATA_DIR
)

st.set_page_config(
    page_title="KnowledgeVault",
    page_icon="data/book_image1.jpg",
    layout="wide",
    initial_sidebar_state="expanded",
)

ensure_data_dir()

def _ensure_state():
    ss = st.session_state

    # active tab
    ss.setdefault("active_tab", "Table View")

    # fetch settings
    ss.setdefault("fetch_query", "")
    ss.setdefault("fetch_count", 6)
    ss.setdefault("fetch_books_on", True)
    ss.setdefault("fetch_yt_on", True)

    # inline search filters
    ss.setdefault("search_term", "")
    ss.setdefault("selected_category", "All")
    ss.setdefault("selected_tag", "All")

    # sidebar add/manage
    ss.setdefault("form_title", "")
    ss.setdefault("form_category", CATEGORY_OPTIONS[0] if CATEGORY_OPTIONS else "Other")
    ss.setdefault("form_link", "")
    ss.setdefault("form_notes", "")
    ss.setdefault("form_tags", "")

    # manage/edit
    #ss.setdefault("manage_title", "")
    # ss.setdefault("manage_category", CATEGORY_OPTIONS[0] if CATEGORY_OPTIONS else "Other")
    # ss.setdefault("manage_link", "")
    # ss.setdefault("manage_notes", "")
    # ss.setdefault("manage_tags", "")

    # bulk ops
    ss.setdefault("bulk_selected_ids", [])


_ensure_state()


st.title("KnowledgeVault — Personal Knowledge Hub")
st.caption("Add, search, auto-fetch, export/import, edit, delete, visualize, backup/restore, and bulk manage your learning resources.")


df = load_data(CSV_PATH)


VIDEO_CAT = "YouTube" if "YouTube" in CATEGORY_OPTIONS else ("Video" if "Video" in CATEGORY_OPTIONS else "Other")
BOOK_CAT = "Book" if "Book" in CATEGORY_OPTIONS else "Article"


def fetch_books(query: str, max_results: int = 6):
    if not query.strip():
        return []
    url = "https://www.googleapis.com/books/v1/volumes"
    params = {"q": query.strip(), "maxResults": max_results}
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        st.error(f"Google Books fetch failed: {e}")
        return []

    items = []
    for item in data.get("items", []):
        vi = item.get("volumeInfo", {})
        title = vi.get("title", "Untitled")
        link = vi.get("infoLink", "")
        desc = vi.get("description", "") or ""
        authors = ", ".join(vi.get("authors", [])) if vi.get("authors") else ""
        notes = f"Fetched via Google Books. {('Authors: '+authors+'. ') if authors else ''}{desc[:300]}".strip()
        items.append({
            "title": title,
            "link": link,
            "tags": query,
            "category": BOOK_CAT,
            "notes": notes,
            "source": "google_books",
        })
    return items

def fetch_youtube(query: str, max_results: int = 6):
    key = st.secrets.get("YOUTUBE_API_KEY", None)
    if not key or not query.strip():
        return []
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "q": query.strip(),
        "maxResults": max_results,
        "type": "video",
        "key": key,
        "safeSearch": "moderate"
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        st.error(f"YouTube fetch failed: {e}")
        return []

    items = []
    for item in data.get("items", []):
        snippet = item.get("snippet", {})
        title = snippet.get("title", "Untitled")
        video_id = (item.get("id") or {}).get("videoId", "")
        link = f"https://www.youtube.com/watch?v={video_id}" if video_id else ""
        desc = snippet.get("description", "") or ""
        notes = f"Fetched via YouTube. {desc[:300]}".strip()
        items.append({
            "title": title,
            "link": link,
            "tags": query,
            "category": VIDEO_CAT,
            "notes": notes,
            "source": "youtube",
        })
    return items


st.subheader("Auto-Fetch Knowledge")
fa, fb, fc, fd = st.columns([2, 1, 1, 1.5])

with fa:
    st.text_input("Topic (e.g., SQL, Python, AI)", key="fetch_query", placeholder="SQL, Python, AI ...")

with fb:
    st.number_input("Max per source", 1, 20, key="fetch_count")

with fc:
    st.checkbox("Books", key="fetch_books_on")
    st.checkbox("YouTube", key="fetch_yt_on")



st.markdown("""
    <style>
    .btnPrimary > button { background:#5b7fff; color:white; border:none; border-radius:8px; height:40px; font-weight:600; }
    .btnPrimary > button:hover { filter:brightness(0.95); }
    .btnSecondary > button { background:#f1f3ff; color:#2b2d42; border:none; border-radius:8px; height:40px; font-weight:600; }
    .btnSecondary > button:hover { filter:brightness(0.95); }
    </style>
    """, unsafe_allow_html=True)
st.markdown("""
    <style>
    /* Reduce spacing below inputs */
    div.stTextInput, div.stNumberInput {
        margin-bottom: 5px;
        padding-bottom: 0px;
    }

    /* Style buttons */
    div.stButton > button {
        background-color: #4CAF50; /* Green */
        color: white;
        border: none;
        padding: 10px 20px;
        text-align: center;
        font-size: 16px;
        border-radius: 8px;
        cursor: pointer;
        transition: 0.3s;
    }

    /* Hover effect */
    div.stButton > button:hover {
        background-color: #45a049;
        transform: scale(1.05);
    }

    /* Put buttons closer to input */
    .stButton {
        margin-top: -5px;
    }
    </style>
""", unsafe_allow_html=True)

a,b =st.columns([0.3,1])
with a:
    st.markdown('<div class="btnPrimary">', unsafe_allow_html=True)
    fetch_and_save = st.button(" Fetch & Save in table")
    st.markdown('</div>', unsafe_allow_html=True)
with b:
    st.markdown('<div class="btnSecondary">', unsafe_allow_html=True)
    preview_btn = st.button("Preview (Don’t save)")
    st.markdown('</div>', unsafe_allow_html=True)

def merge_new_records(df_in: pd.DataFrame, new_items: list[dict]) -> tuple[pd.DataFrame, int, int]:
    df_work = df_in.copy()
    before = len(df_work)
    for rec in new_items:
        df_work = add_record(df_work, rec)
    after = len(df_work)
    added = after - before
    skipped = len(new_items) - added
    return df_work, added, skipped

if fetch_and_save or preview_btn:
    q = st.session_state.fetch_query.strip()
    if not q:
        st.warning("Enter a topic to fetch.")
    else:
        fetched = []
        if st.session_state.fetch_books_on:
            fetched.extend(fetch_books(q, st.session_state.fetch_count))
        if st.session_state.fetch_yt_on:
            yt_items = fetch_youtube(q, st.session_state.fetch_count)
            if not yt_items and "YOUTUBE_API_KEY" not in st.secrets:
                st.info("YouTube results skipped (no YOUTUBE_API_KEY in secrets).")
            fetched.extend(yt_items)

        if not fetched:
            st.info("No items returned from the selected sources.")
        else:
            if preview_btn:
                st.success(f"Preview: {len(fetched)} items fetched for “{q}”. Not saved.")
                prev_df = pd.DataFrame(fetched)[["title","category","tags","link"]]
                st.dataframe(prev_df, use_container_width=True, hide_index=True)
            if fetch_and_save:
                new_df, added, skipped = merge_new_records(df, fetched)
                if added > 0:
                    save_data(new_df, CSV_PATH)
                    df = new_df
                st.success(f"Saved {added} new / {skipped} duplicates for “{q}”")

st.markdown("---")


st.subheader("Search in Your table")
a, b, c, d, e = st.columns([2, 1, 1, 1, 1.2])

with a:
    st.text_input("Search", key="search_term", placeholder="Search title/notes/tags/link")

with b:
    categories = ["All"] + sorted(df["category"].astype(str).unique().tolist())
    if st.session_state.selected_category not in categories:
        st.session_state.selected_category = "All"
    st.selectbox("Filter by Category", categories, key="selected_category")

with c:
    all_tags = sorted(set(
        t.strip() for tags in df["tags"].astype(str).tolist()
        for t in tags.split(",") if t.strip()
    ))
    tag_options = ["All"] + all_tags
    if st.session_state.selected_tag not in tag_options:
        st.session_state.selected_tag = "All"
    st.selectbox("Filter by Tag", tag_options, key="selected_tag")

with d:
    st.markdown("""
    <style>
    .primaryBtn > button { background:#4CAF50; color:white; border:none; height:40px; border-radius:8px; font-weight:600;}
    .primaryBtn > button:hover { filter:brightness(0.95); }
    .resetBtn > button { background:#f1f3ff; color:#2b2d42; border:none; height:40px; border-radius:8px; font-weight:600;}
    .resetBtn > button:hover { filter:brightness(0.95); }
    </style>
    """, unsafe_allow_html=True)
    st.markdown('<div class="primaryBtn">', unsafe_allow_html=True)
    do_search = st.button("Search")
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div class="resetBtn">', unsafe_allow_html=True)
    reset_btn = st.button("Reset")
    st.markdown('</div>', unsafe_allow_html=True)


   
quick_csv = st.button("Export Filtered CSV")


filtered_df = df.copy()
if do_search:
    term = st.session_state.search_term.strip().lower()
    if term:
        mask = []
        for _, row in filtered_df.iterrows():
            row_text = " ".join(map(str, row.values)).lower()
            mask.append(term in row_text)
        filtered_df = filtered_df[pd.Series(mask).values]

    cat = st.session_state.selected_category
    if cat != "All":
        filtered_df = filtered_df[filtered_df["category"] == cat]

    tag = st.session_state.selected_tag
    if tag != "All":
        filtered_df = filtered_df[filtered_df["tags"].str.contains(tag, case=False, na=False)]

if reset_btn:
    if "search_term" not in st.session_state:
        st.session_state.search_term = ""
        st.session_state.selected_category = "All"
        st.session_state.selected_tag = "All"
        st.rerun()

if quick_csv:
    buf = io.StringIO()
    (filtered_df if do_search else df).to_csv(buf, index=False)
    st.download_button(
        "Download Filtered CSV",
        buf.getvalue(),
        file_name="knowledge_filtered.csv",
        mime="text/csv",
        use_container_width=True
    )


with st.sidebar:
    st.subheader("Add Item")
    st.text_input("Title *", key="form_title", placeholder="e.g., Introduction to SQL")
    st.selectbox("Category", CATEGORY_OPTIONS, key="form_category")
    st.text_input("Link (optional)", key="form_link", placeholder="https://…")
    st.text_area("Notes", key="form_notes", placeholder="Key ideas, quotes, etc.")
    st.text_input("Tags (comma separated)", key="form_tags", placeholder="sql, databases, beginner")

    if st.button("Save (manual add)", use_container_width=True):
        title = st.session_state.form_title.strip()
        if not title:
            st.error("Title is required.")
        else:
            rec = {
                "title": title,
                "category": st.session_state.form_category,
                "link": (st.session_state.form_link or "").strip(),
                "notes": st.session_state.form_notes,
                "tags": st.session_state.form_tags,
                "source": "manual"
            }
            new_df = add_record(df.copy(), rec)
            if len(new_df) == len(df):
                st.warning("Duplicate (title+link) — not added.")
            else:
                save_data(new_df, CSV_PATH)
                st.success("Added!")
                st.rerun()

    st.divider()
    st.subheader("Manage Item (Edit/Delete)")
    if df.empty:
        st.info("No items yet.")
    else:
       
        options = [(int(row.id), f"{int(row.id)} — {row.title}")for _, row in df.sort_values("id").dropna(subset=["id"]).iterrows()]

        if "chosen" not in st.session_state:
            st.session_state.chosen = options[0]
       
        chosen = st.selectbox("Select item", options, format_func=lambda x: x[1],key="chosen")

        chosen_id = chosen[0] if isinstance(chosen, tuple) else None
        if chosen_id is not None:
            row = df[df["id"] == chosen_id].iloc[0]
            st.text_input("Title", value=str(row.get("title","")), key="manage_title")
            st.selectbox("Category", CATEGORY_OPTIONS, index=max(0, CATEGORY_OPTIONS.index(row["category"]) if row["category"] in CATEGORY_OPTIONS else 0), key="manage_category")
            st.text_input("Link", value=str(row.get("link","")), key="manage_link")
            st.text_area("Notes", value=str(row.get("notes","")), key="manage_notes")
            st.text_input("Tags", value=str(row.get("tags","")), key="manage_tags")

            c1, c2 = st.columns(2)
            with c1:
                if st.button(" Save changes", use_container_width=True):
                    updates = {
                        "title": st.session_state.manage_title.strip(),
                        "category": st.session_state.manage_category,
                        "link": (st.session_state.manage_link or "").strip(),
                        "notes": st.session_state.manage_notes,
                        "tags": st.session_state.manage_tags,
                    }
                    new_df = update_record(df.copy(), chosen_id, updates)
                    save_data(new_df, CSV_PATH)
                    st.success("Updated.")
                    st.rerun()
            with c2:
                if st.button(" Delete", use_container_width=True):
                    new_df = delete_record(df.copy(), chosen_id)
                    save_data(new_df, CSV_PATH)
                    st.success("Deleted.")
                    st.rerun()

    st.divider()
    st.subheader(" Bulk Operations")
    if not df.empty:
        # Multiselect IDs for bulk ops
        bulk_options = [(int(row.id), f"{int(row.id)} — {row.title}") for _, row in df.sort_values("id").dropna(subset=["id"]).iterrows()]

        st.multiselect("Select IDs for bulk actions", bulk_options, key="bulk_selected_ids", format_func=lambda x: x[1])
        b1, b2 = st.columns(2)
        with b1:
            if st.button(" Bulk Delete", use_container_width=True, type="secondary"):
                ids_to_delete = [pair[0] for pair in st.session_state.bulk_selected_ids]
                if ids_to_delete:
                    new_df = df[~df["id"].isin(ids_to_delete)].copy()
                    save_data(new_df, CSV_PATH)
                    st.success(f"Deleted {len(ids_to_delete)} items.")
                    st.rerun()
                else:
                    st.warning("No IDs selected.")
        with b2:
            if st.button("🪄 Remove Duplicates", use_container_width=True):
                new_df, removed = drop_duplicates_keep_first(df.copy())
                if removed > 0:
                    save_data(new_df, CSV_PATH)
                    st.success(f"Removed {removed} duplicate(s).")
                    st.rerun()
                else:
                    st.info("No duplicates found.")

        # Reassign IDs (compact)
        if st.button(" Reassign IDs (1..N)", use_container_width=True):
            new_df = reassign_ids(df.copy())
            save_data(new_df, CSV_PATH)
            st.success("IDs reassigned.")
            st.rerun()

        # Clear all (with confirm)
        st.markdown("—")
        confirm_clear = st.checkbox("I understand this will permanently delete all records.")
        if st.button(" Clear All", use_container_width=True, disabled=not confirm_clear):
            new_df = clear_all()
            save_data(new_df, CSV_PATH)
            st.success("All records cleared.")
            st.rerun()

    st.divider()
    st.subheader(" Export")
    
    csv_buf = io.StringIO()
    df.to_csv(csv_buf, index=False)
    st.download_button("Download CSV (All)", csv_buf.getvalue(), file_name="knowledge_data.csv", mime="text/csv", use_container_width=True)

    json_buf = io.StringIO()
    df.to_json(json_buf, orient="records", indent=2, force_ascii=False)
    st.download_button("Download JSON (All)", json_buf.getvalue(), file_name="knowledge_data.json", mime="application/json", use_container_width=True)

    # Excel export
    xlsx_bytes = io.BytesIO()
    with pd.ExcelWriter(xlsx_bytes, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Knowledge")
    st.download_button("Download Excel (All)", xlsx_bytes.getvalue(), file_name="knowledge_data.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

    # Export selected IDs (if any)
    if st.session_state.bulk_selected_ids:
        sel_ids = [pair[0] for pair in st.session_state.bulk_selected_ids]
        sel_df = df[df["id"].isin(sel_ids)].copy()
        sel_csv = io.StringIO()
        sel_df.to_csv(sel_csv, index=False)
        st.download_button("Download CSV (Selected IDs)", sel_csv.getvalue(), file_name="knowledge_selected.csv", mime="text/csv", use_container_width=True)

    st.divider()
    st.subheader("Import (CSV or JSON)")
    tmpl = pd.DataFrame(columns=COLUMNS)
    tmpl_csv_buf = io.StringIO()
    tmpl.to_csv(tmpl_csv_buf, index=False)
    st.download_button("Download CSV Template", tmpl_csv_buf.getvalue(), file_name="knowledge_template.csv", mime="text/csv", use_container_width=True)

    uploaded = st.file_uploader("Upload CSV/JSON", type=["csv", "json"])
    if uploaded is not None:
        try:
            if uploaded.type == "application/json" or uploaded.name.lower().endswith(".json"):
                data = json.load(uploaded)
                inc = pd.DataFrame(data)
            else:
                inc = pd.read_csv(uploaded)

            new_df, added, skipped = merge_import(df.copy(), inc)
            if added > 0:
                save_data(new_df, CSV_PATH)
            st.success(f"Imported: added {added}, skipped {skipped} duplicates.")
            st.button("Refresh data", on_click=st.experimental_rerun, use_container_width=True)
        except Exception as e:
            st.error(f"Import failed: {e}")

    st.divider()
    st.subheader("Backup & Restore")
    if st.button("Create Backup (timestamped)", use_container_width=True):
        path = make_backup(df)
        st.success(f"Backup saved: {path}")

    restore_file = st.file_uploader("Restore from CSV/JSON", type=["csv","json"], key="restore_upload")
    if restore_file is not None:
        try:
            if restore_file.name.lower().endswith(".json"):
                data = json.load(restore_file)
                restored = pd.DataFrame(data)
            else:
                restored = pd.read_csv(restore_file)

            # Ensure schema and save
            save_data(restored, CSV_PATH)
            st.success("Restore complete.")
            st.button("Reload", on_click=st.experimental_rerun, use_container_width=True)
        except Exception as e:
            st.error(f"Restore failed: {e}")

    st.divider()
    st.subheader("About")
    st.markdown(
        f"- Built with **Streamlit + Pandas**\n"
        f"- Data file: `data/knowledge_data.csv`\n"
        f"- Auto-Fetch: Google Books (free) + YouTube (API key)\n"
        f"- Full CRUD, Export/Import, Analytics, Bulk Ops, Backup/Restore\n"
        f"- Data directory: `{DATA_DIR}`"
    )


tab_table, tab_cards, tab_analytics = st.tabs(["Table View", "Card View", "Analytics"])


with tab_table:
    st.subheader("Table View")
    target_df = filtered_df if do_search else df
    if target_df.empty:
        st.info("No items to display.")
    else:
        display_cols = [c for c in target_df.columns if c not in ["id","updated_at","created_at","source","date_added","tags"]]
        safe_df = target_df[display_cols].copy().astype(str)
        st.markdown(
            """
            <style>
            table { border-collapse: collapse; width: 100%; }
            th, td { border: 1px solid #ddd; padding: 8px; }
            th { background-color: #5b7fff; color: white; text-align: left; }
            tr:hover { background-color: #f1f1f1; }
            </style>
            """,
            unsafe_allow_html=True
        )
        st.markdown(safe_df.to_html(index=False, escape=False), unsafe_allow_html=True)


st.markdown(
    """
    <style>
    .card {
        border:1px solid #ddd; border-radius:10px; padding:15px; margin-bottom:10px;
        box-shadow: 2px 2px 8px rgba(0,0,0,0.05); transition: all 0.2s ease-in-out;
    }
    .card:hover { background-color: #f6f8ff; box-shadow: 4px 4px 15px rgba(0,0,0,0.15); transform: translateY(-2px); }
    .card h6 { color:#5b7fff; margin:0 0 6px 0; }
    .card p { margin:6px 0; }
    </style>
    """,
    unsafe_allow_html=True
)

with tab_cards:
    st.subheader("Card View")
    target_df = filtered_df if do_search else df
    if target_df.empty:
        st.info("No items to display.")
    else:
        for _, row in target_df.iterrows():
            title = str(row.get("title", "Untitled")) or "Untitled"
            category = str(row.get("category", ""))
            tags = str(row.get("tags", "") or "")
            link = str(row.get("link", "") or "")
            notes = "" if pd.isna(row.get("notes", "")) else str(row.get("notes", ""))
            notes_html = f"<p><b>Notes:</b> {notes}</p>" if notes.strip() else ""
            link_html = f'<a href="{link}" target="_blank">🔗 Open Link</a>' if link else ""
            st.markdown(
                f"""
                <div class="card">
                    <h6>{title}</h6>
                    <p><b>Category:</b> {category}</p>
                    <p><b>Tags:</b> {tags or '—'}</p>
                    {notes_html}
                    {link_html}
                </div>
                """,
                unsafe_allow_html=True
            )


with tab_analytics:
    st.subheader("Analytics")
    if df.empty:
        st.info("No data to chart yet.")
    else:
        work = df.copy()
        work["date_added"] = pd.to_datetime(work["date_added"], errors="coerce")
        work["month"] = work["date_added"].dt.to_period("M").astype(str)

        c1, c2 = st.columns(2)

        with c1:
            st.markdown("**Items by Category**")
            counts = work["category"].astype(str).value_counts()
            fig1, ax1 = plt.subplots()
            ax1.pie(counts.values, labels=counts.index, autopct="%1.0f%%", startangle=90)
            ax1.axis("equal")
            st.pyplot(fig1, use_container_width=True)

        with c2:
            st.markdown("**Items per Month**")
            month_counts = work["month"].value_counts().sort_index()
            pretty_index = []
            for m in month_counts.index:
                try:
                    dt = datetime.strptime(m, "%Y-%m")
                    pretty_index.append(dt.strftime("%b %Y"))
                except Exception:
                    pretty_index.append(m)
            fig2, ax2 = plt.subplots()
            ax2.bar(pretty_index, month_counts.values)
            ax2.tick_params(axis="x", rotation=45)
            ax2.set_ylabel("Items")
            st.pyplot(fig2, use_container_width=True)


st.markdown("---")
st.caption("Complete build: Auto-Fetch • Filters • Export/Import • CRUD • Analytics • Bulk Ops • Backup/Restore")
