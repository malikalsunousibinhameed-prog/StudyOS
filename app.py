from datetime import date, datetime, timedelta
from pathlib import Path
import os

from flask import Flask, abort, flash, redirect, render_template, request, url_for
from flask_wtf.csrf import CSRFProtect
from database import (
    add_assignment, add_study_session, delete_assignment, get_assignment,
    get_assignments, get_dashboard_data, get_statistics, init_db, update_assignment,
    update_assignment_completion,
)

BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__, instance_relative_config=True)
app.config["SECRET_KEY"] = os.environ.get("STUDYOS_SECRET_KEY", "local-development-key-change-me")
app.config["DATABASE"] = str(Path(app.instance_path) / "studyos.sqlite3")
CSRFProtect(app)
os.makedirs(app.instance_path, exist_ok=True)
init_db(app.config["DATABASE"])

PRIORITIES = ("Low", "Medium", "High")


@app.template_filter("pretty_date")
def pretty_date(value):
    if not value:
        return "No date"
    try:
        return date.fromisoformat(value).strftime("%b %d, %Y")
    except (TypeError, ValueError):
        return value


@app.template_filter("duration")
def duration(seconds):
    seconds = max(0, int(seconds or 0))
    hours, remainder = divmod(seconds, 3600)
    minutes = remainder // 60
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes} min"


@app.context_processor
def inject_globals():
    return {"today_iso": date.today().isoformat(), "priorities": PRIORITIES}


def assignment_form_values():
    return {
        "title": request.form.get("title", "").strip(),
        "subject": request.form.get("subject", "").strip(),
        "description": request.form.get("description", "").strip(),
        "due_date": request.form.get("due_date", "").strip(),
        "priority": request.form.get("priority", "Medium").strip(),
    }


def validate_assignment(values):
    errors = []
    if not values["title"]:
        errors.append("Enter an assignment title.")
    elif len(values["title"]) > 120:
        errors.append("The title must be 120 characters or fewer.")
    if not values["subject"]:
        errors.append("Enter a subject.")
    elif len(values["subject"]) > 80:
        errors.append("The subject must be 80 characters or fewer.")
    if len(values["description"]) > 1000:
        errors.append("The description must be 1,000 characters or fewer.")
    try:
        date.fromisoformat(values["due_date"])
    except ValueError:
        errors.append("Choose a valid due date.")
    if values["priority"] not in PRIORITIES:
        errors.append("Choose a valid priority.")
    return errors


@app.route("/")
def dashboard():
    data = get_dashboard_data(app.config["DATABASE"])
    return render_template("dashboard.html", data=data)


@app.route("/assignments")
def assignments():
    status = request.args.get("status", "all")
    search = request.args.get("q", "").strip()
    sort = request.args.get("sort", "due_date")
    if status not in {"all", "pending", "completed", "overdue"}:
        status = "all"
    if sort not in {"due_date", "priority", "created_at"}:
        sort = "due_date"
    items = get_assignments(app.config["DATABASE"], status=status, search=search, sort=sort)
    return render_template("assignments.html", assignments=items, status=status, search=search, sort=sort)


@app.route("/assignments/new", methods=["GET", "POST"])
def new_assignment():
    values = {"title": "", "subject": "", "description": "", "due_date": "", "priority": "Medium"}
    errors = []
    if request.method == "POST":
        values = assignment_form_values()
        errors = validate_assignment(values)
        if not errors:
            add_assignment(app.config["DATABASE"], values)
            flash("Assignment added.", "success")
            return redirect(url_for("assignments"))
    return render_template("assignment_form.html", values=values, errors=errors, page_title="Add assignment")


@app.route("/assignments/<int:assignment_id>/edit", methods=["GET", "POST"])
def edit_assignment(assignment_id):
    existing = get_assignment(app.config["DATABASE"], assignment_id)
    if existing is None:
        abort(404)
    values = dict(existing)
    errors = []
    if request.method == "POST":
        values = assignment_form_values()
        errors = validate_assignment(values)
        if not errors:
            update_assignment(app.config["DATABASE"], assignment_id, values)
            flash("Changes saved.", "success")
            return redirect(url_for("assignments"))
    return render_template("assignment_form.html", values=values, errors=errors, page_title="Edit assignment", assignment_id=assignment_id)


@app.post("/assignments/<int:assignment_id>/toggle")
def toggle_assignment(assignment_id):
    existing = get_assignment(app.config["DATABASE"], assignment_id)
    if existing is None:
        abort(404)
    update_assignment_completion(app.config["DATABASE"], assignment_id, not bool(existing["completed"]))
    flash("Assignment status updated.", "success")
    return redirect(request.referrer or url_for("assignments"))


@app.post("/assignments/<int:assignment_id>/delete")
def remove_assignment(assignment_id):
    if get_assignment(app.config["DATABASE"], assignment_id) is None:
        abort(404)
    delete_assignment(app.config["DATABASE"], assignment_id)
    flash("Assignment deleted.", "success")
    return redirect(url_for("assignments"))


@app.post("/sessions")
def save_session():
    try:
        duration_seconds = int(request.form.get("duration_seconds", "0"))
    except ValueError:
        duration_seconds = 0
    # Accept only completed sessions of at least 25 minutes; the browser cannot save short sessions.
    if duration_seconds < 25 * 60 or duration_seconds > 25 * 60 + 10:
        flash("That study session could not be recorded. Please complete the timer first.", "error")
    else:
        add_study_session(app.config["DATABASE"], duration_seconds)
        flash("Study session recorded.", "success")
    return redirect(request.referrer or url_for("dashboard"))


@app.route("/statistics")
def statistics():
    return render_template("statistics.html", stats=get_statistics(app.config["DATABASE"]))


@app.route("/about")
def about():
    return render_template("about.html")


@app.errorhandler(404)
def not_found(_error):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=True)
