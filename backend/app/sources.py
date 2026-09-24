import asyncio
import logging

from langchain_core.vectorstores import InMemoryVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter

log = logging.getLogger("uvicorn.error")
splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=150)


class Sources:
    def __init__(self, embeddings):
        self.store = InMemoryVectorStore(embeddings)
        self.queue = asyncio.Queue()
        self.status = {}
        self.ids = {}
        self.latest = {}

    def add(self, name: str, text: str):
        self.status[name] = "queued"
        self.latest[name] = text
        self.queue.put_nowait((name, text))

    async def work(self):
        while True:
            name, text = await self.queue.get()
            try:
                self.status[name] = "processing"
                docs = splitter.create_documents([text], [{"source": name}])
                ids = await asyncio.wait_for(self.store.aadd_documents(docs), 120)
                if self.latest[name] is not text:
                    await self.store.adelete(ids)
                    continue
                old, self.ids[name] = self.ids.get(name), ids
                await self.store.adelete(old)
                self.status[name] = f"ready: {len(ids)} chunks"
                log.info("indexed %s (%d chunks)", name, len(ids))
            except Exception as e:
                log.exception("ingestion failed: %s", name)
                if self.latest[name] is text:
                    self.status[name] = f"failed: {e!r}"
            finally:
                self.queue.task_done()

    async def search(self, query: str, k: int = 6):
        await self.queue.join()
        return await self.store.asimilarity_search(query, k=k) if self.store.store else []
