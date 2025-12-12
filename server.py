from fastapi import FastAPI, HTTPException, File, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response, FileResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import asyncio
import os
import json
import uvicorn
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

from api.utils.ai_client import get_next_question, generate_diagnosis
from api.utils.voice_services import speech_to_text, text_to_speech, decode_base64_audio, encode_audio_to_base64

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


class TTSRequest(BaseModel):
    text: str


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


@app.post("/api/tts")
async def text_to_speech_endpoint(request: TTSRequest):
    """文本转语音 - 使用共享服务"""
    try:
        # 调用共享的TTS服务
        result = await text_to_speech(request.text)
        return result
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS service error: {str(e)}")


@app.post("/api/stt")
async def speech_to_text_endpoint(request: Request):
    """语音转文字 - 使用共享服务，支持FormData和JSON格式"""
    try:
        # 检查Content-Type
        content_type = request.headers.get("content-type", "")
        
        if "application/json" in content_type:
            # 处理JSON格式（base64编码）
            body = await request.json()
            audio_base64 = body.get("audio_data")
            mime_type = body.get("mime_type", "audio/webm")
            language = body.get("language", "zh")  # 默认中文
            
            if not audio_base64:
                raise HTTPException(status_code=400, detail="audio_data field is required")
            
            # 解码base64音频数据
            audio_data = decode_base64_audio(audio_base64)
            filename = "audio.webm"
            
            print(f"[STT] 收到JSON格式音频，大小: {len(audio_data)} bytes, 语言: {language}")
            
        else:
            # 处理FormData格式（原始文件上传）
            form = await request.form()
            if "file" not in form:
                raise HTTPException(status_code=400, detail="file field is required")
            
            file = form["file"]
            audio_data = await file.read()
            filename = file.filename
            mime_type = file.content_type
            language = form.get("language", "zh")  # 默认中文
            
            print(f"[STT] 收到FormData文件: {filename}, 类型: {mime_type}, 大小: {len(audio_data)} bytes, 语言: {language}")
        
        # 检查音频数据
        if len(audio_data) == 0:
            raise HTTPException(status_code=400, detail="Audio data is empty")
            
        # 检查文件类型（仅对FormData）
        if "application/json" not in content_type and not mime_type.startswith('audio/'):
            raise HTTPException(status_code=400, detail="File must be an audio file")
            
        print(f"[STT] 音频数据读取完成，大小: {len(audio_data)} bytes")
        
        # 调用共享的STT服务
        result = await speech_to_text(audio_data, filename, mime_type, language)
        
        print(f"[STT] 识别结果: '{result['text']}'")
        return result
            
    except Exception as e:
        print(f"[STT] 错误: {e}")
        raise HTTPException(status_code=500, detail=f"STT service error: {str(e)}")


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
