# RepoGrill

An AI interviewer that reads your GitHub repository and questions you about your own code, the way a real interviewer does in a project deep-dive round. It grades every answer and gives you a scorecard with what to revise.

## How it works
1. **Read** – clones the repo and splits the code into chunks, one per function or class (Python's `ast` module; other languages fall back to line-based chunks).
2. **Understand** – turns each chunk into an embedding with a local model (`BAAI/bge-small-en-v1.5` via fastembed), so code can be searched by meaning.
3. **Interview** – picks the most substantial function from each file and asks an LLM (Groq) to question you about it. After each answer, related code is retrieved with the embeddings (RAG) and the LLM decides whether to dig deeper.
4. **Grade** – every answer gets a score out of 10, what was right, and what was missed. The scorecard averages scores per topic and suggests what to revise.

## Tech stack
| Part | Tech |
|---|---|
| Frontend | React 19, Vite, Tailwind CSS |
| Backend | Python, FastAPI |
| AI | fastembed embeddings, Groq LLM API (`openai/gpt-oss-120b`) |

## Run it locally

**1. Backend**
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env   # then put your Groq API key in .env
uvicorn app.main:app --reload
```
API docs: <http://127.0.0.1:8000/docs>

**2. Frontend** (in a second terminal)
```bash
cd frontend
npm install
npm run dev
```
Open <http://localhost:5173>
