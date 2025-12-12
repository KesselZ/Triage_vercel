import json
import asyncio
import sys
import os
import base64

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from api.utils.voice_services import speech_to_text, decode_base64_audio

def handler(request, response):
    """
    Vercel serverless function for speech-to-text
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
        
        # 获取base64编码的音频数据
        audio_base64 = body.get('audio_data')
        mime_type = body.get('mime_type', 'audio/webm')
        
        if not audio_base64:
            response.status_code = 400
            return json.dumps({'error': 'No audio data provided'})
        
        # 解码base64音频数据
        audio_data = decode_base64_audio(audio_base64)
        
        # 调用共享的STT服务
        result = asyncio.run(speech_to_text(audio_data, "audio.webm", mime_type))
        
        response.status_code = 200
        return json.dumps(result)
        
    except Exception as e:
        print(f"STT Error: {str(e)}")
        response.status_code = 500
        return json.dumps({"error": str(e)})
