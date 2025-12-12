import json
import asyncio
import sys
import os
import base64
import httpx

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

def handler(request, response):
    """
    Vercel serverless function for text-to-speech
    """
    # 设置CORS头
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
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
        text = body.get('text', '')
        
        if not text.strip():
            response.status_code = 400
            return json.dumps({'error': 'No text provided'})
        
        if len(text) > 500:
            response.status_code = 400
            return json.dumps({'error': 'Text too long (max 500 characters)'})
        
        # 获取API密钥
        api_key = os.getenv('UNIAPI_KEY') or os.getenv('UNIAPI_API_KEY')
        if not api_key:
            response.status_code = 500
            return json.dumps({'error': 'API key not configured'})
        
        # 调用UniAPI TTS
        url = "https://api.uniapi.io/v1/audio/speech"
        
        data = {
            "model": "tts-1",
            "input": text.strip(),
            "voice": "alloy"
        }
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        async def generate_speech():
            async with httpx.AsyncClient(timeout=30.0) as client:
                api_response = await client.post(url, headers=headers, json=data)
                api_response.raise_for_status()
                return api_response.content
        
        # 运行异步TTS生成
        audio_content = asyncio.run(generate_speech())
        
        # 将音频内容编码为base64返回
        audio_base64 = base64.b64encode(audio_content).decode('utf-8')
        
        response.status_code = 200
        return json.dumps({
            "audio_data": audio_base64,
            "format": "mp3"
        })
        
    except Exception as e:
        print(f"TTS Error: {str(e)}")
        response.status_code = 500
        return json.dumps({"error": str(e)})
