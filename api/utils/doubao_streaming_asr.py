"""
豆包流式语音识别客户端
使用 WebSocket 协议实现实时语音识别
"""
import asyncio
import websockets
import json
import gzip
import struct
import os
from typing import AsyncGenerator, Callable, Optional


class DoubaoStreamingASR:
    """豆包流式语音识别客户端"""
    
    # 三种模式的接口地址
    BIGMODEL_URL = "wss://openspeech.bytedance.com/api/v3/sauc/bigmodel"
    BIGMODEL_ASYNC_URL = "wss://openspeech.bytedance.com/api/v3/sauc/bigmodel_async"
    BIGMODEL_NOSTREAM_URL = "wss://openspeech.bytedance.com/api/v3/sauc/bigmodel_nostream"
    
    def __init__(
        self, 
        app_id: str, 
        token: str,
        mode: str = "async",  # "async", "bigmodel", "nostream"
        sample_rate: int = 16000,
        format: str = "pcm",
        bits_per_sample: int = 16,
        channel: int = 1
    ):
        """
        初始化流式识别客户端
        
        Args:
            app_id: 火山引擎控制台获取的 APP ID
            token: 火山引擎控制台获取的 Token
            mode: 识别模式 ("async"=优化版双向流式, "bigmodel"=双向流式, "nostream"=流式输入)
            sample_rate: 采样率，支持 8000/16000/24000/32000/44100/48000
            format: 音频格式，支持 pcm/ogg_opus/opus/mp3/flac/aac/amr/speex
            bits_per_sample: 采样位数，仅 PCM 格式需要
            channel: 声道数，1=单声道
        """
        self.app_id = app_id
        self.token = token
        self.sample_rate = sample_rate
        self.format = format
        self.bits_per_sample = bits_per_sample
        self.channel = channel
        
        # 选择接口地址
        if mode == "async":
            self.url = self.BIGMODEL_ASYNC_URL
        elif mode == "bigmodel":
            self.url = self.BIGMODEL_URL
        else:
            self.url = self.BIGMODEL_NOSTREAM_URL
            
        self.ws = None
        self.sequence = 0
    
    def _create_header(
        self, 
        message_type: int, 
        message_flags: int = 0,
        serialization: int = 1,  # 1=JSON
        compression: int = 1     # 1=Gzip
    ) -> bytes:
        """
        创建消息头（4字节）
        
        消息头格式：
        - version (4 bits): 0001
        - header_size (4 bits): 0001
        - message_type (4 bits): 消息类型
        - message_flags (4 bits): 消息标志
        - serialization (4 bits): 序列化方法
        - compression (4 bits): 压缩方法
        - reserved (8 bits): 保留字段
        """
        byte1 = (0b0001 << 4) | 0b0001  # version + header_size
        byte2 = (message_type << 4) | message_flags
        byte3 = (serialization << 4) | compression
        byte4 = 0x00  # reserved
        
        return struct.pack('BBBB', byte1, byte2, byte3, byte4)
    
    def _pack_full_request(self, request_data: dict) -> bytes:
        """
        打包完整请求消息
        
        消息类型：0001 (Full client request)
        """
        # 序列化为 JSON
        json_data = json.dumps(request_data, ensure_ascii=False).encode('utf-8')
        
        # Gzip 压缩
        compressed_data = gzip.compress(json_data)
        
        # 创建消息头
        header = self._create_header(
            message_type=0b0001,  # Full client request
            message_flags=0b0000,
            serialization=0b0001,  # JSON
            compression=0b0001    # Gzip
        )
        
        # 打包：header + payload_size + payload
        payload_size = struct.pack('>I', len(compressed_data))  # 大端
        
        return header + payload_size + compressed_data
    
    def _pack_audio_request(self, audio_data: bytes, is_last: bool = False) -> bytes:
        """
        打包音频数据消息
        
        消息类型：0010 (Audio only client request)
        """
        # Gzip 压缩音频
        compressed_audio = gzip.compress(audio_data)
        
        # 创建消息头
        message_flags = 0b0010 if is_last else 0b0000  # 最后一包标志
        header = self._create_header(
            message_type=0b0010,  # Audio only client request
            message_flags=message_flags,
            serialization=0b0000,  # None (raw bytes)
            compression=0b0001     # Gzip
        )
        
        # 打包：header + payload_size + payload
        payload_size = struct.pack('>I', len(compressed_audio))
        
        return header + payload_size + compressed_audio
    
    def _unpack_response(self, data: bytes) -> dict:
        """
        解包服务器响应
        
        响应格式：header(4B) + sequence(4B) + payload_size(4B) + payload
        """
        if len(data) < 12:
            raise ValueError("响应数据太短")
        
        # 解析头部
        header = data[0:4]
        byte2 = header[1]
        message_type = (byte2 >> 4) & 0x0F
        message_flags = byte2 & 0x0F
        
        byte3 = header[2]
        serialization = (byte3 >> 4) & 0x0F
        compression = byte3 & 0x0F
        
        # 解析 sequence
        sequence = struct.unpack('>I', data[4:8])[0]
        
        # 解析 payload size
        payload_size = struct.unpack('>I', data[8:12])[0]
        
        # 解析 payload
        payload = data[12:12+payload_size]
        
        # 如果 payload 为空，返回空结果
        if payload_size == 0 or len(payload) == 0:
            return {
                "sequence": sequence,
                "is_last": (message_flags & 0b0011) == 0b0011,
                "data": {}
            }
        
        # 解压缩
        if compression == 0b0001:  # Gzip
            try:
                payload = gzip.decompress(payload)
            except Exception as e:
                print(f"⚠️  Gzip 解压失败: {e}")
                return {
                    "sequence": sequence,
                    "is_last": (message_flags & 0b0011) == 0b0011,
                    "data": {"error": "decompress_failed"}
                }
        
        # 反序列化
        if serialization == 0b0001:  # JSON
            try:
                decoded = payload.decode('utf-8')
                result = json.loads(decoded)
            except Exception as e:
                print(f"⚠️  JSON 解析失败: {e}")
                print(f"   Payload 前100字节: {payload[:100]}")
                return {
                    "sequence": sequence,
                    "is_last": (message_flags & 0b0011) == 0b0011,
                    "data": {"error": "json_parse_failed"}
                }
        else:
            result = {"raw": payload}
        
        # 检查是否是最后一包
        is_last = (message_flags & 0b0011) == 0b0011
        
        return {
            "sequence": sequence,
            "is_last": is_last,
            "data": result
        }
    
    async def connect(self):
        """建立 WebSocket 连接"""
        import uuid
        
        # 生成唯一的连接 ID
        connect_id = str(uuid.uuid4())
        
        # 准备 headers（根据豆包官方文档）
        # 文档要求在 HTTP 请求头中添加以下4个信息
        headers = [
            ("X-Api-App-Key", self.app_id),
            ("X-Api-Access-Key", self.token),
            ("X-Api-Resource-Id", "volc.seedasr.sauc.duration"),  # 豆包2.0小时版 ✅
            ("X-Api-Connect-Id", connect_id),  # 连接追踪ID
        ]
        
        # 简化输出
        print(f"📡 正在连接豆包服务 (豆包2.0 双向流式优化版)...")
        
        # websockets 14.0+ 使用 additional_headers
        self.ws = await websockets.connect(
            self.url,
            additional_headers=headers
        )
        
        print(f"✅ 已连接到豆包流式识别服务")
    
    async def send_start_request(self):
        """发送初始化请求"""
        request_data = {
            "app": {
                "appid": self.app_id,
                "token": "access_token",  # 固定值，实际 token 在 header 中
                "cluster": "volc_bigasr_sauc"
            },
            "user": {
                "uid": "user_001"
            },
            "audio": {
                "format": self.format,
                "sample_rate": self.sample_rate,
                "channel": self.channel,
            },
            "request": {
                "reqid": f"req_{self.sequence}",
                "nbest": 1,
                "show_language": False,
                "show_utterances": True,
                "result_type": "full"
            }
        }
        
        # 如果是 PCM 格式，需要指定采样位数
        if self.format == "pcm":
            request_data["audio"]["bits"] = self.bits_per_sample
        
        message = self._pack_full_request(request_data)
        await self.ws.send(message)
        
        # 等待服务器响应
        response_data = await self.ws.recv()
        response = self._unpack_response(response_data)
        
        # 检查初始化是否成功
        if response['data']:
            print(f"✅ 初始化成功，准备接收音频")
        
        return response
    
    async def send_audio_chunk(self, audio_data: bytes, is_last: bool = False):
        """
        发送音频数据块
        
        Args:
            audio_data: 音频数据（建议 100-200ms）
            is_last: 是否是最后一包
        """
        message = self._pack_audio_request(audio_data, is_last)
        await self.ws.send(message)
        self.sequence += 1
    
    async def receive_result(self) -> Optional[dict]:
        """
        接收识别结果
        
        Returns:
            识别结果字典，包含 text, is_final 等字段
        """
        try:
            response_data = await self.ws.recv()
            response = self._unpack_response(response_data)
            
            result_data = response['data']
            
            # 提取识别文本
            text = ""
            is_final = response['is_last']
            
            if 'result' in result_data:
                utterances = result_data['result'].get('utterances', [])
                if utterances:
                    text = utterances[0].get('text', '')
            
            return {
                "text": text,
                "is_final": is_final,
                "sequence": response['sequence'],
                "raw": result_data
            }
            
        except websockets.exceptions.ConnectionClosed:
            print("⚠️ WebSocket 连接已关闭")
            return None
    
    async def close(self):
        """关闭连接"""
        if self.ws:
            await self.ws.close()


async def streaming_recognize(
    audio_generator: AsyncGenerator[bytes, None],
    app_id: str,
    token: str,
    on_result: Callable[[str, bool], None],
    mode: str = "async"
) -> str:
    """
    流式语音识别（便捷函数）
    
    Args:
        audio_generator: 异步音频数据生成器
        app_id: APP ID
        token: Token
        on_result: 结果回调函数 (text, is_final)
        mode: 识别模式
    
    Returns:
        最终识别文本
    """
    client = DoubaoStreamingASR(app_id, token, mode=mode)
    
    try:
        # 连接
        await client.connect()
        
        # 发送初始化请求
        await client.send_start_request()
        
        # 创建接收任务
        async def receive_loop():
            final_text = ""
            while True:
                result = await client.receive_result()
                if result is None:
                    break
                
                if result['text']:
                    on_result(result['text'], result['is_final'])
                    if result['is_final']:
                        final_text = result['text']
                
                if result['is_final']:
                    break
            
            return final_text
        
        receive_task = asyncio.create_task(receive_loop())
        
        # 发送音频数据
        async for audio_chunk in audio_generator:
            await client.send_audio_chunk(audio_chunk, is_last=False)
        
        # 发送最后一包（空数据）
        await client.send_audio_chunk(b'', is_last=True)
        
        # 等待接收完成
        final_text = await receive_task
        
        return final_text
        
    finally:
        await client.close()


# 使用示例
if __name__ == "__main__":
    async def main():
        # 从环境变量获取配置
        app_id = os.getenv("DOUBAO_APP_ID")
        token = os.getenv("DOUBAO_TOKEN")
        
        # 模拟音频数据生成器
        async def audio_generator():
            # 这里应该是实际的音频数据
            # 每次 yield 100-200ms 的音频
            for i in range(10):
                yield b'\x00' * 3200  # 16kHz, 16bit, 100ms
                await asyncio.sleep(0.1)
        
        # 结果回调
        def on_result(text: str, is_final: bool):
            status = "【最终】" if is_final else "【临时】"
            print(f"{status} {text}")
        
        # 执行识别
        final_text = await streaming_recognize(
            audio_generator(),
            app_id,
            token,
            on_result,
            mode="async"
        )
        
        print(f"\n最终识别结果: {final_text}")
    
    asyncio.run(main())

