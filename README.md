# Deal CRM

A tiny, single-user deal CRM you run locally. Built with **Python + Flask +
SQLite** — minimal dependencies, plain HTML/CSS, no frontend framework.

Track acquisition/investment targets in one table: company name, estimated
EBITDA, estimated valuation, notes, and a Google Drive folder link. Add, edit,
delete, and sort. Data is stored in a local `deals.db` SQLite file and survives
restarts.

## Run it

```bash
cd crm
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Then open **http://127.0.0.1:5000** in your browser.

> On Windows, activate the virtualenv with `.venv\Scripts\activate` instead of
> `source .venv/bin/activate`.

## Notes

- **EBITDA and valuation** are stored as raw whole-dollar integers and displayed
  as currency (e.g. `$2,500,000`), so sorting works numerically. Input is
  forgiving — `$2,500,000` or `2500000` both work.
- Only **Company name** is required; every other field is optional.
- Click the **Company / EBITDA / Valuation** column headers to sort.
- The **Drive** link opens in a new tab.
- The database file `deals.db` is created automatically on first run and is
  git-ignored (it holds your data, not source code).
- No login/auth — intended for local, single-user use only.
