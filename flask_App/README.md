Instacart Flask App

Run locally (macOS / zsh):

1. Create and activate a virtual environment (recommended):

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Ensure DuckDB database `final_instacart.db` is present in the project root (one level above `flask_app`). If you have CSVs only, run the notebook cells that create the DuckDB DB or use the provided notebook `Instacart.ipynb` to load CSVs into `final_instacart.db`.

4. Run the app:

```bash
python app.py
```

5. Open `http://127.0.0.1:5000/` in your browser.

Notes:
- The app uses `plotly` to render interactive charts embedded in HTML.
- If the DB filename or location differs, edit `DB_PATH` in `app.py`.
