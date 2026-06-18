"""Local Deal CRM — a tiny single-user Flask + SQLite app.

Run with `python app.py` and open http://127.0.0.1:5000.
Data is stored in a local SQLite file (deals.db) next to this script.
"""

import sqlite3
from pathlib import Path

from flask import (
    Flask,
    flash,
    g,
    redirect,
    render_template,
    request,
    url_for,
)

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "deals.db"

app = Flask(__name__)
# This app is local and single-user; the key never leaves the machine.
app.secret_key = "local-deal-crm-dev-key"

# Columns the table may be sorted by. Whitelisted so the ORDER BY clause,
# which is built from user input, can never be used for SQL injection.
SORTABLE_COLUMNS = {"company_name", "ebitda", "valuation", "created_at"}
DEFAULT_SORT = "created_at"
DEFAULT_DIR = "desc"

FIELDS = ("company_name", "ebitda", "valuation", "notes", "drive_link")


# --- Database ---------------------------------------------------------------

def get_db():
    """Return a SQLite connection scoped to the current request."""
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Create the deals table if it does not exist yet."""
    conn = sqlite3.connect(DATABASE)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS deals (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT    NOT NULL,
            ebitda       INTEGER,
            valuation    INTEGER,
            notes        TEXT,
            drive_link   TEXT,
            created_at   TEXT DEFAULT (datetime('now'))
        )
        """
    )
    conn.commit()
    conn.close()


# --- Helpers ----------------------------------------------------------------

def parse_money(raw):
    """Parse a user-entered amount into whole dollars (int) or None.

    Forgiving of '$', commas and surrounding whitespace so "$2,500,000"
    stores as 2500000. Empty input becomes None. Raises ValueError for
    anything that is not a number.
    """
    if raw is None:
        return None
    cleaned = raw.replace("$", "").replace(",", "").strip()
    if cleaned == "":
        return None
    return int(round(float(cleaned)))


def form_values(source):
    """Normalize a Row, a submitted form, or None into a plain dict.

    Lets the form template read every field uniformly whether it is rendering
    a blank form, an existing deal, or a rejected submission to re-fill.
    """
    if source is None:
        return {field: "" for field in FIELDS}
    if isinstance(source, sqlite3.Row):
        return {field: (source[field] if source[field] is not None else "") for field in FIELDS}
    # request.form (a MultiDict)
    return {field: source.get(field, "") for field in FIELDS}


@app.template_filter("currency")
def currency(value):
    """Render an integer dollar amount as e.g. $2,500,000 ("—" when empty)."""
    if value is None or value == "":
        return "—"
    amount = int(value)
    sign = "-" if amount < 0 else ""
    return f"{sign}${abs(amount):,.0f}"


# --- Routes -----------------------------------------------------------------

@app.route("/")
def index():
    sort = request.args.get("sort", DEFAULT_SORT)
    direction = request.args.get("dir", DEFAULT_DIR).lower()
    if sort not in SORTABLE_COLUMNS:
        sort = DEFAULT_SORT
    if direction not in ("asc", "desc"):
        direction = DEFAULT_DIR

    deals = get_db().execute(
        f"SELECT * FROM deals ORDER BY {sort} {direction}, id DESC"
    ).fetchall()

    return render_template("index.html", deals=deals, sort=sort, direction=direction)


@app.route("/add", methods=["GET", "POST"])
def add():
    if request.method == "POST":
        error, values = _read_form(request.form)
        if error:
            flash(error, "error")
            return render_template(
                "form.html", deal=form_values(request.form),
                action=url_for("add"), title="Add deal",
            )
        db = get_db()
        db.execute(
            "INSERT INTO deals (company_name, ebitda, valuation, notes, drive_link) "
            "VALUES (?, ?, ?, ?, ?)",
            values,
        )
        db.commit()
        flash(f"Added “{values[0]}”.", "success")
        return redirect(url_for("index"))

    return render_template(
        "form.html", deal=form_values(None), action=url_for("add"), title="Add deal"
    )


@app.route("/edit/<int:deal_id>", methods=["GET", "POST"])
def edit(deal_id):
    db = get_db()
    deal = db.execute("SELECT * FROM deals WHERE id = ?", (deal_id,)).fetchone()
    if deal is None:
        flash("Deal not found.", "error")
        return redirect(url_for("index"))

    if request.method == "POST":
        error, values = _read_form(request.form)
        if error:
            flash(error, "error")
            return render_template(
                "form.html", deal=form_values(request.form),
                action=url_for("edit", deal_id=deal_id), title="Edit deal",
            )
        db.execute(
            "UPDATE deals SET company_name = ?, ebitda = ?, valuation = ?, "
            "notes = ?, drive_link = ? WHERE id = ?",
            (*values, deal_id),
        )
        db.commit()
        flash(f"Updated “{values[0]}”.", "success")
        return redirect(url_for("index"))

    return render_template(
        "form.html", deal=form_values(deal),
        action=url_for("edit", deal_id=deal_id), title="Edit deal",
    )


@app.route("/delete/<int:deal_id>", methods=["POST"])
def delete(deal_id):
    db = get_db()
    db.execute("DELETE FROM deals WHERE id = ?", (deal_id,))
    db.commit()
    flash("Deal deleted.", "success")
    return redirect(url_for("index"))


def _read_form(form):
    """Validate and parse a submitted form.

    Returns (error_message, None) on failure or (None, values_tuple) on success,
    where values_tuple matches the column order used by INSERT/UPDATE.
    """
    company_name = form.get("company_name", "").strip()
    if not company_name:
        return "Company name is required.", None
    try:
        ebitda = parse_money(form.get("ebitda"))
        valuation = parse_money(form.get("valuation"))
    except ValueError:
        return "EBITDA and valuation must be numbers.", None
    return None, (
        company_name,
        ebitda,
        valuation,
        form.get("notes", "").strip(),
        form.get("drive_link", "").strip(),
    )


# Initialize the database on import so it works under both `python app.py`
# and `flask run`.
init_db()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
