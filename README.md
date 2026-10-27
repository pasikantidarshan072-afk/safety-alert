# Community Safety Alert — Python Full-Stack Demo

A Flask + SQLite web application for submitting missing-person / public-safety reports, reviewing them, approving public alerts, and receiving public tips. Ollama is used only to draft neutral reviewer notes.

## Important safety and privacy design
- This demo does **not** identify people by face, scan CCTV, track a child or suspect, or determine a person's live location.
- It does not connect to CCTV systems or location-provider APIs.
- Reports and photos remain private until an authorized reviewer approves them for public display.
- An authorized reviewer must verify facts and decide whether an alert should be published.
- Use official police channels and applicable laws for real cases. For immediate danger, contact local emergency services.
- Do not publish private contact details, unverified allegations, or sensitive information about a child. This demo is not production-ready.

## Requirements
- Python 3.10+
- Optional: Ollama installed and running for AI reviewer summaries.

## Run on Windows (PowerShell)
1. Extract the ZIP into a folder.
2. Open that folder in VS Code.
3. Open Terminal → New Terminal.
4. Create a virtual environment:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
   If PowerShell blocks activation, use Command Prompt and run:
   ```bat
   .venv\\Scripts\\activate.bat
   ```
5. Install packages:
   ```bash
   pip install -r requirements.txt
   ```
6. Start the app:
   ```bash
   python app.py
   ```
7. Open `http://127.0.0.1:5000` in your browser.

## Optional Ollama AI summaries
1. Install Ollama from its official website: https://ollama.com
2. In a terminal, pull a model:
   ```bash
   ollama pull llama3
   ```
3. Make sure Ollama is running, then start this app with `python app.py`.
4. In the admin dashboard, choose **AI review notes** on a report. AI text is only a draft; a human must verify it.

If you use another Ollama model, set `OLLAMA_MODEL` to its name before launching the app.

## Demo admin login
- Username: `admin`
- Password: `ChangeMe123!`

Change these before use. On Windows PowerShell:
```powershell
$env:ADMIN_USERNAME="your-admin-name"
$env:ADMIN_PASSWORD="use-a-long-unique-password"
$env:SECRET_KEY="use-a-long-random-secret"
python app.py
```

## Pages
- `/` — public, approved active alerts
- `/report` — submit a report for review
- `/admin/login` — reviewer login
- `/admin` — review cases, approve/close alerts, inspect tips, and request Ollama notes

## Before any real deployment
Add HTTPS, secure password hashing and account management, CSRF protection, audit logs, rate limiting, encrypted storage, retention/deletion policies, role-based access, professional security review, and a verified integration with authorized agencies. The included default login is for local demonstration only.
