from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response, FileResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import httpx
import os
import json
import uvicorn
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
async def text_to_speech(request: TTSRequest):
    """文本转语音"""
    if not request.text or len(request.text.strip()) == 0:
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    
    if len(request.text) > 500:  # 限制文本长度
        raise HTTPException(status_code=400, detail="Text too long (max 500 characters)")
    
    try:
        # 调用UniAPI TTS服务
        api_key = os.getenv("UNIAPI_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="TTS API key not configured")
        
        url = "https://api.uniapi.io/v1/audio/speech"
        payload = {
            "model": "tts-1",
            "input": request.text.strip(),
            "voice": "alloy",
            "response_format": "mp3"
        }
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            # 返回音频数据
            from fastapi.responses import Response
            return Response(
                content=response.content,
                media_type="audio/mpeg",
                headers={"Content-Disposition": "inline; filename=speech.mp3"}
            )
            
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=500, detail=f"TTS API error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS service error: {str(e)}")


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
            # "language": (None, "zh")  # 暂时移除语言参数测试
        }
        
        headers = {
            "Authorization": f"Bearer {api_key}"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, files=files)
            print(f"[STT] UniAPI响应状态: {response.status_code}")
            print(f"[STT] UniAPI响应头: {dict(response.headers)}")
            
            if response.status_code != 200:
                print(f"[STT] UniAPI错误响应: {response.text}")
                raise HTTPException(status_code=500, detail=f"STT API error: {response.status_code}")
            
            result = response.json()
            print(f"[STT] UniAPI原始响应: {result}")
            
            transcribed_text = result.get("text", "")
            print(f"[STT] 提取的文本: '{transcribed_text}'")
            
            return {"text": transcribed_text.strip()}
            
    except httpx.HTTPStatusError as e:
        print(f"[STT] HTTP错误: {e}")
        print(f"[STT] 错误响应: {e.response.text}")
        raise HTTPException(status_code=500, detail=f"STT API error: {e}")
    except Exception as e:
        print(f"[STT] 异常: {e}")
        raise HTTPException(status_code=500, detail=f"STT service error: {str(e)}")


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
