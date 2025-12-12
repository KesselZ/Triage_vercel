import os
import httpx
from typing import List, Dict, Any

from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
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


@app.post("/api/stt")
async def speech_to_text(file: UploadFile = File(...)):
    """语音转文字"""
    try:
        print(f"[STT] 收到文件: {file.filename}, 类型: {file.content_type}, 大小: {file.size if hasattr(file, 'size') else 'unknown'}")
        
        # 检查文件类型
        if not file.content_type.startswith('audio/'):
            raise HTTPException(status_code=400, detail="File must be an audio file")
        
        # 读取音频数据
        audio_data = await file.read()
        
        if len(audio_data) == 0:
            raise HTTPException(status_code=400, detail="Audio file is empty")
            
        print(f"[STT] 音频数据读取完成，大小: {len(audio_data)} bytes")
        
        # 调用UniAPI STT服务
        api_key = os.getenv("UNIAPI_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="STT API key not configured")
        
        print(f"[STT] 开始调用UniAPI API...")
        url = "https://api.uniapi.io/v1/audio/transcriptions"
        
        # 使用multipart/form-data格式上传文件
        files = {
            "file": (file.filename, audio_data, file.content_type),
            "model": (None, "whisper-1")
        }
        
        headers = {
            "Authorization": f"Bearer {api_key}"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, files=files)
            print(f"[STT] UniAPI响应状态: {response.status_code}")
            
            if response.status_code != 200:
                print(f"[STT] UniAPI错误响应: {response.text}")
                raise HTTPException(status_code=500, detail=f"STT API error: {response.status_code}")
            
            result = response.json()
            transcribed_text = result.get("text", "")
            
            print(f"[STT] 识别结果: {transcribed_text}")
            
            return {"text": transcribed_text}
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"[STT] 处理异常: {str(e)}")
        raise HTTPException(status_code=500, detail=f"STT service error: {str(e)}")


class TTSRequest(BaseModel):
    text: str


@app.post("/api/tts")
async def text_to_speech(request: TTSRequest):
    """文字转语音"""
    try:
        print(f"[TTS] 收到文本: {request.text}")
        
        # 调用UniAPI TTS服务
        api_key = os.getenv("UNIAPI_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="TTS API key not configured")
        
        url = "https://api.uniapi.io/v1/audio/speech"
        
        data = {
            "model": "tts-1",
            "input": request.text,
            "voice": "alloy",
            "response_format": "mp3"
        }
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=data)
            print(f"[TTS] UniAPI响应状态: {response.status_code}")
            
            if response.status_code != 200:
                print(f"[TTS] UniAPI错误响应: {response.text}")
                raise HTTPException(status_code=500, detail=f"TTS API error: {response.status_code}")
            
            # 返回音频文件
            return Response(
                content=response.content,
                media_type="audio/mpeg",
                headers={"Content-Disposition": "inline; filename=speech.mp3"}
            )
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"[TTS] 处理异常: {str(e)}")
        raise HTTPException(status_code=500, detail=f"TTS service error: {str(e)}")
