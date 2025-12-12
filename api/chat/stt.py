import json
import asyncio
import sys
import os
import base64
import httpx

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

def handler(request, response):
    """
    Vercel serverless function for speech-to-text
    """
    # 设置CORS头
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    response.headers['Content-Type'] = 'application/json'
    
    # 处理OPTIONS请求（CORS预检）
    if request.method == 'OPTIONS':
        response.status_code = 200
        return ''
    
    if request.method != 'POST':
        response.status_code = 405
        return json.dumps({'error': 'Method not allowed'})
    
    try:
        # 解析请求体
        body = json.loads(request.body)
        
        # 获取base64编码的音频数据
        audio_base64 = body.get('audio_data')
        mime_type = body.get('mime_type', 'audio/webm')
        language = body.get('language', 'zh')  # 默认中文
        
        if not audio_base64:
            response.status_code = 400
            return json.dumps({'error': 'No audio data provided'})
        
        # 解码base64音频数据
        audio_data = base64.b64decode(audio_base64)
        
        # 获取API密钥
        api_key = os.getenv('UNIAPI_KEY') or os.getenv('UNIAPI_API_KEY')
        if not api_key:
            response.status_code = 500
            return json.dumps({'error': 'API key not configured'})
        
        # 调用UniAPI Whisper-1进行语音识别
        async def transcribe():
            url = "https://api.uniapi.io/v1/audio/transcriptions"
            files = {
                "file": ("audio.webm", audio_data, mime_type),
                "model": (None, "whisper-1"),
                "language": (None, language)
            }
            headers = {
                "Authorization": f"Bearer {api_key}"
            }
            async with httpx.AsyncClient(timeout=30.0) as client:
                api_response = await client.post(url, headers=headers, files=files)
                api_response.raise_for_status()
                return api_response.json()
        
        result = asyncio.run(transcribe())
        transcribed_text = result.get("text", "")
        
        response.status_code = 200
        return json.dumps({"text": transcribed_text.strip()})
        
    except Exception as e:
        print(f"STT Error: {str(e)}")
        response.status_code = 500
        return json.dumps({"error": str(e)})
