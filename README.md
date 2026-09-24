# Bowatt Research Agent

Small React + FastAPI research agent. It can upload text sources, search the web, and stream a markdown answer.

## Setup

Requirements:

- Node.js 24+
- Python 3.12+
- OpenAI API key
- Tavily API key

Create the backend env file:

```powershell
Copy-Item backend/.env.example backend/.env
```

Add your keys:

```txt
OPENAI_API_KEY=
TAVILY_API_KEY=
```

Run the backend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\pip install -e .
.\.venv\Scripts\uvicorn app.main:app --reload --port 8787
```

Run the frontend in another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open:

```txt
http://localhost:5173
```

## Docker

```powershell
npm --prefix frontend install
npm --prefix frontend run build
docker compose up --build
```

Frontend runs on `http://localhost:5173`.

## Architecture

The frontend is a small Vite/React app for uploads, prompts, and streamed markdown output. The backend is FastAPI with a LangGraph research agent. Uploaded text files are queued, embedded, and searched alongside Tavily web results.

I kept storage in memory to keep the project simple. With more time I would move uploaded files, queue state, and vectors into durable services.

## Example Queries

- `Summarize this uploaded document and list the main risks.`
- `Research recent battery storage trends and cite public sources.`
- `Compare this uploaded source against current web guidance.`

Expected output is a concise markdown report with citations, uploaded file references, and any gaps called out.

## Evaluation

I would evaluate the agent with a small set of repeatable prompts, checking source usage, citation quality, factual accuracy, latency, and failure handling. This would make it easier to compare model settings and catch regressions.

## Tests

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests
npm --prefix frontend run build
```

## Future Scope

- Store uploaded files and embeddings durably.
- Add a real job/status page for uploads.
- Add more evaluation prompts for citation quality and source usage.
- Extend the LangGraph flow into a multi-agent setup for planning, source review, web research, and final writing.
- Move from in-memory search to a production vector store.

## Local Env

These go in `backend/.env`:

```txt
OPENAI_API_KEY=
TAVILY_API_KEY=
LLM_MODEL=openai:gpt-5.1
OPENAI_REASONING_EFFORT=low
EMBEDDING_MODEL=openai:text-embedding-3-small
CORS_ORIGIN_REGEX=http://(localhost|127\.0\.0\.1)(:\d+)?
WEB_RESULTS=5
MAX_RESEARCH_STEPS=6
MAX_UPLOAD_BYTES=2000000
FIRST_CHUNK_WAIT=5
INGEST_WORKERS=4
```

Live test link: https://bowatt-research.vercel.app/
