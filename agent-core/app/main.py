from contextlib import asynccontextmanager

import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from fastapi.staticfiles import StaticFiles

from app.api.routers import router as api_router
from app.core.config import settings
from app.models.database import init_db
from app.services.rag_logger import set_main_loop


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Capture the main event loop so sync code running in thread pool threads
    # (e.g. knowledge_base.structured_query via run_in_executor) can schedule
    # fire-and-forget log coroutines via run_coroutine_threadsafe.
    set_main_loop(asyncio.get_running_loop())
    init_db()
    yield


app = FastAPI(
    title="美陈设计 AI Agent",
    description="美陈设计师的 AI 辅助出案系统",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

# 静态文件服务（预览生成的 HTML 和图片），指向外部 design-data 目录
app.mount("/data", StaticFiles(directory=str(Path(settings.image_cache_dir).parent)), name="data")


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/")
async def root():
    return {"message": "美陈设计 AI Agent 服务运行中", "version": "0.1.0"}
