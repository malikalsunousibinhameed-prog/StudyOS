import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path


def connect(database_path):
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db(database_path):
    Path(database_path).parent.mkdir(parents=True, exist_ok=True)
    with connect(database_path) as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL CHECK(length(trim(title)) > 0),
                subject TEXT NOT NULL CHECK(length(trim(subject)) > 0),
                description TEXT,
                due_date TEXT NOT NULL,
                priority TEXT NOT NULL CHECK(priority IN ('Low', 'Medium', 'High')),
                completed INTEGER NOT NULL DEFAULT 0 CHECK(completed IN (0, 1)),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS study_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                duration_seconds INTEGER NOT NULL CHECK(duration_seconds > 0),
                completed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """)


def add_assignment(database_path, values):
    with connect(database_path) as db:
        db.execute(
            """INSERT INTO assignments (title, subject, description, due_date, priority)
               VALUES (?, ?, ?, ?, ?)""",
            (values["title"], values["subject"], values["description"] or None,
             values["due_date"], values["priority"]),
        )


def get_assignment(database_path, assignment_id):
    with connect(database_path) as db:
        row = db.execute("SELECT * FROM assignments WHERE id = ?", (assignment_id,)).fetchone()
        return dict(row) if row else None


def update_assignment(database_path, assignment_id, values):
    with connect(database_path) as db:
        db.execute(
            """UPDATE assignments
               SET title = ?, subject = ?, description = ?, due_date = ?, priority = ?
               WHERE id = ?""",
            (values["title"], values["subject"], values["description"] or None,
             values["due_date"], values["priority"], assignment_id),
        )


def update_assignment_completion(database_path, assignment_id, completed):
    with connect(database_path) as db:
        db.execute("UPDATE assignments SET completed = ? WHERE id = ?", (int(completed), assignment_id))


def delete_assignment(database_path, assignment_id):
    with connect(database_path) as db:
        db.execute("DELETE FROM assignments WHERE id = ?", (assignment_id,))


def get_assignments(database_path, status="all", search="", sort="due_date"):
    today = date.today().isoformat()
    where = []
    params = []
    if status == "pending":
        where.append("completed = 0 AND due_date >= ?")
        params.append(today)
    elif status == "completed":
        where.append("completed = 1")
    elif status == "overdue":
        where.append("completed = 0 AND due_date < ?")
        params.append(today)
    if search:
        where.append("(title LIKE ? OR subject LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])
    order_by = {
        "due_date": "completed ASC, due_date ASC",
        "priority": "completed ASC, CASE priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END, due_date ASC",
        "created_at": "created_at DESC",
    }.get(sort, "completed ASC, due_date ASC")
    sql = "SELECT * FROM assignments"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += f" ORDER BY {order_by}, id DESC"
    with connect(database_path) as db:
        return [dict(row) for row in db.execute(sql, params).fetchall()]


def _session_totals(db, start_date=None):
    if start_date:
        row = db.execute(
            "SELECT COALESCE(SUM(duration_seconds), 0) AS total FROM study_sessions WHERE date(completed_at) >= ?",
            (start_date,),
        ).fetchone()
    else:
        row = db.execute("SELECT COALESCE(SUM(duration_seconds), 0) AS total FROM study_sessions").fetchone()
    return int(row["total"])


def get_dashboard_data(database_path):
    today = date.today()
    with connect(database_path) as db:
        rows = [dict(r) for r in db.execute("SELECT * FROM assignments ORDER BY due_date ASC").fetchall()]
        pending = sum(not r["completed"] and r["due_date"] >= today.isoformat() for r in rows)
        overdue = sum(not r["completed"] and r["due_date"] < today.isoformat() for r in rows)
        completed = sum(bool(r["completed"]) for r in rows)
        week_start = (today - timedelta(days=today.weekday())).isoformat()
        study_week = _session_totals(db, week_start)

    open_items = [r for r in rows if not r["completed"]]
    def mission_score(item):
        try:
            days_left = (date.fromisoformat(item["due_date"]) - today).days
        except ValueError:
            days_left = 36500
        urgency = 100 if days_left < 0 else max(0, 40 - days_left * 5)
        priority = {"High": 30, "Medium": 15, "Low": 0}.get(item["priority"], 0)
        return urgency + priority, item["due_date"]
    mission = sorted(open_items, key=lambda item: (-mission_score(item)[0], mission_score(item)[1]))[:3]
    for item in mission:
        days_left = (date.fromisoformat(item["due_date"]) - today).days
        if days_left < 0:
            item["mission_reason"] = "Overdue — give this your attention."
        elif days_left == 0:
            item["mission_reason"] = "Due today."
        elif item["priority"] == "High":
            item["mission_reason"] = f"High priority — due in {days_left} day{'s' if days_left != 1 else ''}."
        else:
            item["mission_reason"] = f"Due in {days_left} day{'s' if days_left != 1 else ''}."
    upcoming = sorted(open_items, key=lambda item: (item["due_date"], item["id"]))[:5]
    return {
        "pending": pending, "overdue": overdue, "completed": completed,
        "study_week_seconds": study_week, "mission": mission, "upcoming": upcoming,
        "total_assignments": len(rows),
    }


def get_statistics(database_path):
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    chart_start = today - timedelta(days=6)
    with connect(database_path) as db:
        rows = [dict(r) for r in db.execute("SELECT * FROM assignments").fetchall()]
        total_seconds = _session_totals(db)
        week_seconds = _session_totals(db, week_start.isoformat())
        sessions = db.execute(
            """SELECT date(completed_at) AS session_date, SUM(duration_seconds) AS seconds
               FROM study_sessions WHERE date(completed_at) >= ?
               GROUP BY date(completed_at)""",
            (chart_start.isoformat(),),
        ).fetchall()
    session_map = {r["session_date"]: int(r["seconds"]) for r in sessions}
    chart = []
    for offset in range(7):
        day = chart_start + timedelta(days=offset)
        seconds = session_map.get(day.isoformat(), 0)
        chart.append({"label": day.strftime("%a"), "date": day.isoformat(), "seconds": seconds,
                      "minutes": seconds // 60})
    return {
        "total": len(rows),
        "pending": sum(not r["completed"] and r["due_date"] >= today.isoformat() for r in rows),
        "completed": sum(bool(r["completed"]) for r in rows),
        "overdue": sum(not r["completed"] and r["due_date"] < today.isoformat() for r in rows),
        "total_seconds": total_seconds,
        "week_seconds": week_seconds,
        "chart": chart,
        "chart_max": max((item["seconds"] for item in chart), default=0),
    }

def add_study_session(database_path, duration_seconds):
    with connect(database_path) as db:
        db.execute(
            "INSERT INTO study_sessions (duration_seconds) VALUES (?)",
            (duration_seconds,),
        )


if __name__ == "__main__":
    import os
    path = os.environ.get("STUDYOS_DATABASE", "instance/studyos.sqlite3")
    init_db(path)
    print(f"StudyOS database initialized at {path}")
