import os
from typing import List, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, validator

from .utils.ai_client import get_next_question, generate_diagnosis


# 支持的模型列表
SUPPORTED_MODELS = [
    "grok-4-1-fast-non-reasoning",
    "doubao-seed-1-6-thinking-250715", 
    "deepseek-v3.2-exp"
]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = FastAPI()

# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def serve_index():
    """返回前端首页 public/index.html"""
    index_path = os.path.join(BASE_DIR, "..", "public", "index.html")
    if not os.path.exists(index_path):
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(index_path)


class ChatRequest(BaseModel):
    # history 中的每一项至少包含 role/content，但前端还会带上 options、selectedOptions 等字段
    # 因此前端发来的是 Dict[str, Any]，不能用 Dict[str, str] 否则会导致 422 验证失败
    history: List[Dict[str, Any]]
    model: str = "grok-4-1-fast-non-reasoning"  # 默认模型
    
    @validator('model')
    def validate_model(cls, v):
        if v not in SUPPORTED_MODELS:
            raise ValueError(f"不支持的模型: {v}. 支持的模型: {', '.join(SUPPORTED_MODELS)}")
        return v

@app.post("/api/chat/next")
async def chat_next(request: ChatRequest):
    """问诊接口"""
    result = await get_next_question(request.history, request.model)
    return result

@app.post("/api/chat/diagnose")
async def chat_diagnose(request: ChatRequest):
    """诊断接口"""
    result = await generate_diagnosis(request.history, request.model)
    return result
