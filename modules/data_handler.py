# modules/data_handler.py
import os
from datetime import datetime
import pandas as pd


DATA_DIR = "data"
CSV_PATH = os.path.join(DATA_DIR, "knowledge_data.csv")


CATEGORY_OPTIONS = [
    "Book",
    "YouTube",
    "Article",
    "Course",
    "Research Paper",
    "Other"
]


COLUMNS = ["id", "title", "category", "link", "notes", "tags", "source", "date_added"]


def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)

def _ensure_schema(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure the DataFrame has all required columns and only those."""
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = "" if col != "id" else pd.NA
    df = df[COLUMNS]
    df["id"] = pd.to_numeric(df["id"], errors="coerce")
    return df


def load_data(csv_path: str) -> pd.DataFrame:
    """Load the CSV into a DataFrame, ensuring correct columns."""
    ensure_data_dir()
    if not os.path.exists(csv_path):
        return pd.DataFrame(columns=COLUMNS)
    df = pd.read_csv(csv_path)
    df = _ensure_schema(df)
    return df

def save_data(df, csv_path):
    temp_path = csv_path + ".tmp"

    
    df.to_csv(temp_path, index=False)

   
    try:
        os.replace(temp_path, csv_path)  # works on Windows & Linux
    except PermissionError:
        print(f"⚠️ Could not replace {csv_path}. Maybe it's open in Excel?")


def generate_id(df: pd.DataFrame) -> int:
    """Robust ID generator that ignores blanks and non-numeric IDs."""
    if df.empty or "id" not in df.columns:
        return 1
    numeric_ids = pd.to_numeric(df["id"], errors="coerce")
    max_id = numeric_ids.max()
    if pd.isna(max_id):
        return 1
    return int(max_id) + 1

def is_duplicate(df: pd.DataFrame, record: dict) -> bool:
    """Duplicate if same title+link (case-insensitive)."""
    title = (record.get("title") or "").strip().lower()
    link = (record.get("link") or "").strip().lower()
    if "title" not in df.columns or "link" not in df.columns:
        return False
    return not df[
        (df["title"].astype(str).str.strip().str.lower() == title) &
        (df["link"].astype(str).str.strip().str.lower() == link)
    ].empty

def add_record(df: pd.DataFrame, record: dict) -> pd.DataFrame:
    """Add a new record if not duplicate. Returns new DataFrame."""
    df = _ensure_schema(df)
    if is_duplicate(df, record):
        return df
    new_row = {
        "id": generate_id(df),
        "title": (record.get("title") or "").strip(),
        "category": record.get("category", "Other"),
        "link": (record.get("link") or "").strip(),
        "notes": (record.get("notes") or "").strip(),
        "tags": (record.get("tags") or "").strip(),
        "source": record.get("source", "manual"),
        "date_added": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    return _ensure_schema(df)

def update_record(df: pd.DataFrame, record_id: int, updates: dict) -> pd.DataFrame:
    """Update a record by id with provided fields in `updates`."""
    df = _ensure_schema(df)
    if df.empty:
        return df
    mask = df["id"] == record_id
    if not mask.any():
        return df
    for k, v in updates.items():
        if k in df.columns:
            df.loc[mask, k] = v
    return _ensure_schema(df)

def delete_record(df: pd.DataFrame, record_id: int) -> pd.DataFrame:
    """Delete a record by id."""
    df = _ensure_schema(df)
    if df.empty:
        return df
    df = df[df["id"] != record_id].copy()
    return _ensure_schema(df)

def merge_import(df: pd.DataFrame, import_df: pd.DataFrame) -> tuple[pd.DataFrame, int, int]:
    """
    Merge an imported DataFrame using add_record() (dedupe on title+link).
    Returns (new_df, added_count, skipped_count).
    """
    df = _ensure_schema(df)
    import_df = _ensure_schema(import_df)
    before = len(df)
    for _, row in import_df.iterrows():
        rec = {
            "title": row.get("title", ""),
            "category": row.get("category", "Other"),
            "link": row.get("link", ""),
            "notes": row.get("notes", ""),
            "tags": row.get("tags", ""),
            "source": row.get("source", "import"),
        }
        df = add_record(df, rec)
    after = len(df)
    added = after - before
    total = len(import_df)
    skipped = max(total - added, 0)
    return df, added, skipped

# -------------- Bulk / Maintenance --------------
def drop_duplicates_keep_first(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Remove duplicates by (title, link), keep first."""
    df = _ensure_schema(df)
    before = len(df)
    df = df.sort_values(["title", "link", "id"], na_position="last").drop_duplicates(
        subset=["title", "link"], keep="first"
    )
    after = len(df)
    removed = before - after
    return _ensure_schema(df), removed

def reassign_ids(df: pd.DataFrame) -> pd.DataFrame:
    """Reassign IDs to 1..N keeping current order by date_added then id."""
    df = _ensure_schema(df)
    if df.empty:
        return df
    # Order more predictably
    df = df.sort_values(by=["date_added", "id"], na_position="last").reset_index(drop=True)
    df["id"] = range(1, len(df) + 1)
    return _ensure_schema(df)

def clear_all() -> pd.DataFrame:
    """Return an empty DataFrame with schema (for clearing all)."""
    return pd.DataFrame(columns=COLUMNS)

def make_backup(df: pd.DataFrame) -> str:
    """Save a timestamped backup CSV in data/ and return its path."""
    ensure_data_dir()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(DATA_DIR, f"knowledge_backup_{ts}.csv")
    _ensure_schema(df).to_csv(path, index=False)
    return path
