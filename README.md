# RepoGrill

An AI interviewer that reads your GitHub repository and questions you about your own code, the way a real technical interviewer would.

## Status
Phase 1: repo analyzer (clone a repo, split its code into chunks)

## Run the backend
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Then open <http://127.0.0.1:8000/docs> to try the API.
