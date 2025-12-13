import os
import base64
from typing import List, Dict, Any

from fastapi import FastAPI, HTTPException, Request, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, validator

from .utils.ai_client import get_next_question, generate_diagnosis
from .utils.voice_services import speech_to_text, text_to_speech, decode_base64_audio


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


# 首页现在由 vercel.json 直接处理，不需要这个路由了


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

class TTSRequest(BaseModel):
    text: str

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

@app.post("/api/chat/tts")
async def text_to_speech_endpoint(request: TTSRequest):
    """文本转语音"""
    try:
        result = await text_to_speech(request.text)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS service error: {str(e)}")

@app.post("/api/chat/stt")
async def speech_to_text_endpoint(request: Request):
    """语音转文字 - 支持JSON和FormData格式"""
    try:
        content_type = request.headers.get("content-type", "")
        
        if "application/json" in content_type:
            # JSON格式（base64编码）
            body = await request.json()
            audio_base64 = body.get("audio_data")
            mime_type = body.get("mime_type", "audio/webm")
            language = body.get("language", "zh")
            
            if not audio_base64:
                raise HTTPException(status_code=400, detail="audio_data field is required")
            
            audio_data = decode_base64_audio(audio_base64)
            filename = "audio.webm"
        else:
            # FormData格式（原始文件上传）
            form = await request.form()
            if "file" not in form:
                raise HTTPException(status_code=400, detail="file field is required")
            
            file = form["file"]
            audio_data = await file.read()
            filename = file.filename
            mime_type = file.content_type
            language = form.get("language", "zh")
        
        if len(audio_data) == 0:
            raise HTTPException(status_code=400, detail="Audio data is empty")
        
        if "application/json" not in content_type and not mime_type.startswith('audio/'):
            raise HTTPException(status_code=400, detail="File must be an audio file")
        
        result = await speech_to_text(audio_data, filename, mime_type, language)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"STT service error: {str(e)}")
