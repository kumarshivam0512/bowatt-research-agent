import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, StreamingResponse
from langchain.chat_models import init_chat_model
from langchain.embeddings import init_embeddings
from pydantic import BaseModel, Field, constr
from starlette.background import BackgroundTask

from app.agent import build, stream
from app.sources import Sources

log = logging.getLogger("uvicorn.error")
LLM_MODEL = os.getenv("LLM_MODEL", "openai:gpt-5.1")
DEFAULT_REASONING_EFFORT = os.getenv("OPENAI_REASONING_EFFORT")
MAX_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", 2_000_000))
FIRST_CHUNK_WAIT = float(os.getenv("FIRST_CHUNK_WAIT", 5))
REASONING_VALUES = "^(none|low|medium|high)$"


def chat_model_kwargs(reasoning_effort: str | None = None):
    kwargs = {"timeout": 120}
    effort = reasoning_effort or DEFAULT_REASONING_EFFORT
    if LLM_MODEL.startswith("openai:") and effort:
        kwargs["reasoning_effort"] = effort
    return kwargs


def graph_for(app: FastAPI, reasoning_effort: str | None):
    key = reasoning_effort or "default"
    if key not in app.state.graphs:
        llm = init_chat_model(LLM_MODEL, **chat_model_kwargs(reasoning_effort))
        app.state.graphs[key] = build(llm, app.state.sources)
    return app.state.graphs[key]


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.sources = Sources(init_embeddings(os.getenv("EMBEDDING_MODEL", "openai:text-embedding-3-small")))
    app.state.graphs = {}
    graph_for(app, None)
    workers = [asyncio.create_task(app.state.sources.work()) for _ in range(int(os.getenv("INGEST_WORKERS", "4")))]
    yield
    for w in workers:
        w.cancel()


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=os.getenv("CORS_ORIGIN_REGEX", r"http://(localhost|127\.0\.0\.1)(:\d+)?"),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def invalid(_, e: RequestValidationError):
    return PlainTextResponse("Invalid request: " + "; ".join(f"{x['loc'][-1]}: {x['msg']}" for x in e.errors()), 422)


class ResearchIn(BaseModel):
    request: constr(strip_whitespace=True, min_length=1, max_length=8000)
    reasoning_effort: str | None = Field(default=None, pattern=REASONING_VALUES)


async def pump(chunks, queue: asyncio.Queue):
    try:
        async for chunk in chunks:
            queue.put_nowait(chunk)
        queue.put_nowait(None)
    except Exception as e:
        log.exception("research failed")
        queue.put_nowait(e)


async def stop(task: asyncio.Task):
    if not task.done():
        log.info("research cancelled: client disconnected")
        task.cancel()


@app.post("/api/research")
async def research(body: ResearchIn, req: Request):
    queue = asyncio.Queue()
    # own task: LangGraph only stops its nodes on a plain cancel(), not on Starlette's anyio cancel scope
    graph = graph_for(req.app, body.reasoning_effort)
    task = asyncio.create_task(pump(stream(graph, body.request, list(req.app.state.sources.status)), queue))
    first = asyncio.ensure_future(queue.get())
    await asyncio.wait([first], timeout=FIRST_CHUNK_WAIT)
    if first.done() and isinstance(error := first.result(), Exception):
        return PlainTextResponse(f"Research failed: {error}", 502)

    async def chunks():
        item = await first
        while isinstance(item, str):
            yield item
            item = await queue.get()
        if item:
            yield f"\n\n> **Error:** research failed: {item}\n"

    return StreamingResponse(chunks(), media_type="text/markdown; charset=utf-8", background=BackgroundTask(stop, task))


@app.post("/api/sources")
async def upload(files: list[UploadFile], req: Request):
    accepted = []
    for f in files:
        name, data = f.filename or "untitled.txt", await f.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            return PlainTextResponse(f"{name} is larger than {MAX_BYTES} bytes", 413)
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            return PlainTextResponse(f"{name} is not UTF-8 text", 415)
        if not text.strip():
            return PlainTextResponse(f"{name} is empty", 400)
        accepted.append((name, text, {"name": name, "size": len(data), "type": f.content_type or "text/plain"}))
    for name, text, _ in accepted:
        req.app.state.sources.add(name, text)
    return {"status": "queued", "uploaded": [meta for *_, meta in accepted]}


@app.get("/api/sources")
async def sources(req: Request):
    return req.app.state.sources.status
