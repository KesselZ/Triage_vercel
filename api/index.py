from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any

from utils.ai_client import get_next_question, generate_diagnosis

app = FastAPI()

# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    history: List[Dict[str, str]]

@app.post("/api/chat/next")
async def chat_next(request: ChatRequest):
    """问诊接口"""
    result = await get_next_question(request.history)
    return result

@app.post("/api/chat/diagnose")
async def chat_diagnose(request: ChatRequest):
    """诊断接口"""
    result = await generate_diagnosis(request.history)
    return result

# Vercel需要这个导出
handler = app
