from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List
import uvicorn
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

from api.utils.ai_client import get_next_question, generate_diagnosis

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = FastAPI()

# 允许跨域，方便本地前端或其他域访问 API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 如果以后有静态资源（JS/CSS），可以挂到 /static 目录
app.mount("/static", StaticFiles(directory=BASE_DIR, html=False), name="static")


@app.get("/")
async def serve_index():
    """返回前端首页 index.html"""
    index_path = os.path.join(BASE_DIR, "public", "index.html")
    if not os.path.exists(index_path):
        raise HTTPException(status_code=404, detail="public/index.html not found")
    return FileResponse(index_path)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    history: List[ChatMessage]


@app.post("/api/chat/next")
async def chat_next(request: ChatRequest):
    """获取下一个问题"""
    history_dicts = [msg.model_dump() for msg in request.history]
    result = await get_next_question(history_dicts)
    return result


@app.post("/api/chat/diagnose")
async def chat_diagnose(request: ChatRequest):
    """生成诊断结果"""
    history_dicts = [msg.model_dump() for msg in request.history]
    result = await generate_diagnosis(history_dicts)
    return result


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
