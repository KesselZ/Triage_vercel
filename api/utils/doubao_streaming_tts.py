#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
豆包流式TTS服务 - HTTP单向流式
"""

import httpx
import json
import base64
from typing import AsyncGenerator, Optional


class DoubaoStreamingTTS:
    """豆包流式TTS客户端"""
    
    def __init__(
        self,
        app_id: str,
        access_key: str,
        resource_id: str = "seed-tts-1.0",
        speaker: str = "zh_female_tianxinxiaomei_emo_v2_mars_bigtts",
        sample_rate: int = 24000,
        audio_format: str = "pcm",  # 改为pcm支持真正的流式播放
        timeout: float = 30.0
    ):
        """
        初始化豆包TTS客户端
        
        Args:
            app_id: 应用ID
            access_key: 访问密钥
            resource_id: 资源ID (seed-tts-1.0)
            speaker: 说话人
            sample_rate: 采样率
            audio_format: 音频格式 (pcm/mp3)，pcm支持真正的流式播放
            timeout: 超时时间
        """
        self.app_id = app_id
        self.access_key = access_key
        self.resource_id = resource_id
        self.speaker = speaker
        self.sample_rate = sample_rate
        self.audio_format = audio_format
        self.timeout = timeout
        self.url = "https://openspeech.bytedance.com/api/v3/tts/unidirectional"
    
    async def synthesize_stream(
        self,
        text: str,
        speed_ratio: float = 1.0,
        volume_ratio: float = 1.0,
        pitch_ratio: float = 1.0
    ) -> AsyncGenerator[bytes, None]:
        """
        流式合成语音
        
        Args:
            text: 要合成的文本
            speed_ratio: 语速比例 (0.5-2.0)
            volume_ratio: 音量比例 (0.5-2.0)
            pitch_ratio: 音调比例 (0.5-2.0)
            
        Yields:
            音频数据块 (bytes)
        """
        # 设置请求头
        headers = {
            "X-Api-App-Id": self.app_id,
            "X-Api-Access-Key": self.access_key,
            "X-Api-Resource-Id": self.resource_id,
            "Content-Type": "application/json"
        }
        
        # 设置请求体
        payload = {
            "user": {
                "uid": "fastapi_user"
            },
            "req_params": {
                "text": text,
                "speaker": self.speaker,
                "audio_params": {
                    "format": self.audio_format,
                    "sample_rate": self.sample_rate,
                    "speed_ratio": speed_ratio,
                    "volume_ratio": volume_ratio,
                    "pitch_ratio": pitch_ratio
                }
            }
        }
        
        # 发送流式请求
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream(
                "POST",
                self.url,
                headers=headers,
                json=payload
            ) as response:
                
                # 检查状态码
                if response.status_code != 200:
                    error_text = await response.aread()
                    raise Exception(f"TTS请求失败 (状态码 {response.status_code}): {error_text.decode('utf-8')}")
                
                # 逐行读取响应（JSONL格式）
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    
                    try:
                        data = json.loads(line)
                        code = data.get("code", -1)
                        
                        # 成功且包含音频数据
                        if code == 0 and "data" in data and data["data"]:
                            # Base64解码音频数据
                            audio_chunk = base64.b64decode(data["data"])
                            yield audio_chunk
                            continue
                        
                        # 结束标记
                        if code == 20000000:
                            break
                        
                        # 错误
                        if code > 0:
                            error_msg = data.get("message", "未知错误")
                            raise Exception(f"TTS服务错误 (code {code}): {error_msg}")
                            
                    except json.JSONDecodeError as e:
                        # 忽略JSON解析错误，继续处理下一行
                        continue
    
    async def synthesize_full(
        self,
        text: str,
        speed_ratio: float = 1.0,
        volume_ratio: float = 1.0,
        pitch_ratio: float = 1.0
    ) -> bytes:
        """
        完整合成语音（等待所有数据）
        
        Args:
            text: 要合成的文本
            speed_ratio: 语速比例
            volume_ratio: 音量比例
            pitch_ratio: 音调比例
            
        Returns:
            完整的音频数据 (bytes)
        """
        audio_data = bytearray()
        
        async for chunk in self.synthesize_stream(text, speed_ratio, volume_ratio, pitch_ratio):
            audio_data.extend(chunk)
        
        return bytes(audio_data)

