# KnowledgeVault — Personal Knowledge Hub 📚

A Streamlit-based app to collect, search, and visualize your personal knowledge —
articles, books, videos, or notes.

---

## 🚀 Features (planned)
- Add notes with title, link, category, tags, and custom notes
- View items as a **table** or **cards**
- Search & filter by category, tags, or keywords
- Visualize insights (categories, timeline)
- Export (CSV/JSON) and Import data
- (Optional) Fetch metadata from links

---

## 📂 Project Structure

knowledge_vault/
├── app.py # main Streamlit app
├── requirements.txt # dependencies
├── data/ # CSV storage
├── modules/ # helper functions (data handling, charts)
├── assets/ # images/icons
└── README.md # documentation

markdown
Copy
Edit

---

## 📊 Data Schema

Each note will be stored in `data/knowledge_data.csv` with these columns:

- `id` → unique identifier (UUID)
- `title` → title of the item
- `category` → Article | Book | Video | Other
- `link` → optional URL
- `notes` → your personal notes
- `tags` → comma-separated labels
- `created_at` → timestamp (ISO)
- `updated_at` → timestamp (ISO)
- `source` → manual | metadata (future)

---

## ⚙️ Setup Instructions

1. Clone this repo (or create folder locally).
2. Install dependencies:
   ```bash
   pip install -r requirements.txtECHO is on.
