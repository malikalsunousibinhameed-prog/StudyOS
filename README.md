# StudyOS

StudyOS is a small, local student productivity app for managing assignments and recording focused study sessions. It is built as a learning project using Python, Flask, SQLite, HTML, CSS, JavaScript, and Jinja.

## Features

- Create, edit, complete, reopen, and delete assignments.
- Search assignments and filter by status.
- Sort by due date, priority, or recently added.
- A dashboard with assignment totals and upcoming work.
- A deterministic Today's Mission list based on deadline urgency and priority.
- A 25-minute study timer.
- Record completed sessions and review seven-day study activity.
- Responsive layout for laptop and mobile screens.

## Project structure

- `app.py` — Flask routes, request validation, and template filters.
- `database.py` — SQLite setup and database operations.
- `templates/` — Jinja HTML templates.
- `static/css/style.css` — application styles.
- `static/js/` — timer and small frontend interactions.
- `tests/test_app.py` — automated backend and route tests.
- `instance/studyos.sqlite3` — created automatically the first time the app runs.

## Requirements

- Python 3.10 or newer.
- Windows PowerShell or another terminal.
- A web browser.

## Run on Windows

Open PowerShell in the `studyos` folder.

1. Check Python is installed:

   ```powershell
   py --version
   ```

   If that command is not recognized, install Python from https://www.python.org/downloads/ and select the option to add Python to PATH.

2. Create a virtual environment:

   ```powershell
   py -m venv .venv
   ```

3. Activate it:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

   If PowerShell blocks activation, you can run this command for the current terminal session only, then activate again:

   ```powershell
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   .\.venv\Scripts\Activate.ps1
   ```

4. Install the dependencies:

   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

5. Start the app:

   ```powershell
   python app.py
   ```

6. Open http://127.0.0.1:5000 in your browser.

7. To stop the server, return to PowerShell and press `Ctrl+C`.

The first run creates the SQLite database under `instance`. Existing data is not deleted on subsequent runs.

## Run tests

With the virtual environment activated:

```powershell
python -m unittest discover -s tests -v
```

The tests use a temporary database so they do not alter your normal StudyOS data.

## Today's Mission algorithm

The app ignores completed assignments. Each remaining assignment receives a simple score:

- Overdue work receives a strong urgency score.
- Upcoming deadlines receive more urgency as the due date approaches.
- High priority adds more points than Medium or Low priority.
- The three highest-scoring assignments are shown.

This algorithm is intentionally simple and deterministic. It does not use AI or an external service.

## Database design

`assignments` stores assignment details, completion status, and creation time. `study_sessions` stores the duration and completion time of sessions the user chooses to record. SQL statements use parameters rather than concatenating user input.

## Notes and limitations

- This is a local, single-user app. It has no accounts, cloud sync, or multi-user permissions.
- Assignment deadlines use the computer's local calendar date.
- The timer state lives in the current browser tab and resets after a refresh.
- The timer records a session after the countdown completes. The server validates the submitted duration, but a local single-user app is not a tamper-proof time-tracking system.
- The built-in Flask server is for local development, not public production hosting.
- The default secret key is only for local development. Set the `STUDYOS_SECRET_KEY` environment variable before any deployment.
- CSRF protection is enabled using Flask-WTF. Do not disable it outside tests.
