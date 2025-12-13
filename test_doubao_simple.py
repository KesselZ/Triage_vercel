"""
豆包流式语音识别 - 实时录音测试
直接从麦克风录音并实时识别
"""
import asyncio
import sounddevice as sd
import numpy as np
import queue
from api.utils.doubao_streaming_asr import DoubaoStreamingASR

# 配置（从你的账户复制）
APP_ID = "9369539387"
ACCESS_TOKEN = "EVHujvbAnGM-OW0T3WHHO1YF8ZHRzINa"
# SECRET_KEY = "zVV1XJMZR5lXqWOAzV_dQl7inG99AXFs"  # 备用

# 注意：之前失败是因为缺少 X-Api-Resource-Id 和 X-Api-Connect-Id
# 现在已经添加了完整的4个 header

# 音频配置
SAMPLE_RATE = 16000  # 16kHz
CHANNELS = 1         # 单声道
DTYPE = 'int16'      # 16-bit
CHUNK_DURATION = 0.2 # 200ms per chunk (最优性能)

async def test_real_time_recognition():
    """
    实时录音识别测试
    """
    print("=" * 60)
    print("🎤 豆包流式语音识别 - 实时录音测试")
    print("=" * 60)
    
    # 音频队列
    audio_queue = queue.Queue()
    
    # 创建客户端（使用优化版双向流式）
    client = DoubaoStreamingASR(
        app_id=APP_ID,
        token=ACCESS_TOKEN,
        mode="async",  # 使用优化版
        sample_rate=SAMPLE_RATE,
        format="pcm",
        bits_per_sample=16,
        channel=CHANNELS
    )
    
    # 录音控制
    is_recording = False
    
    def audio_callback(indata, frames, time_info, status):
        """音频回调函数：实时接收麦克风数据"""
        if status:
            print(f"⚠️  音频状态: {status}")
        
        if is_recording:
            # 将音频数据放入队列
            audio_queue.put(indata.copy())
    
    try:
        # 1. 连接到豆包服务
        await client.connect()
        print("✅ 连接成功")
        
        # 2. 发送初始化请求
        await client.send_start_request()
        
        # 3. 开始录音
        print("\n" + "=" * 60)
        print("🎤 准备开始录音")
        print("=" * 60)
        print("\n提示：")
        print("  - 请说一句完整的话")
        print("  - 例如：\"我最近头痛，想咨询一下应该挂什么科\"")
        print("  - 录音时长：5秒")
        print("  - 识别结果会实时显示")
        
        input("\n按 Enter 键开始录音...")
        
        print("\n🔴 正在录音... (5秒)\n")
        
        # 创建接收任务
        final_text = ""
        
        async def receive_results():
            """接收识别结果"""
            nonlocal final_text
            while True:
                result = await client.receive_result()
                if result is None:
                    break
                
                # 实时打印结果
                if result['text']:
                    status = "【最终】" if result['is_final'] else "【临时】"
                    print(f"{status} {result['text']}")
                    
                    if result['is_final']:
                        final_text = result['text']
                
                if result['is_final']:
                    break
        
        # 启动接收任务
        receive_task = asyncio.create_task(receive_results())
        
        # 开始录音
        is_recording = True
        
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            callback=audio_callback,
            blocksize=int(SAMPLE_RATE * CHUNK_DURATION)
        ):
            # 录音并发送数据
            duration = 5  # 5秒
            chunks_to_send = int(duration / CHUNK_DURATION)
            
            for i in range(chunks_to_send):
                # 从队列获取音频数据
                try:
                    audio_data = audio_queue.get(timeout=1)
                    
                    # 转换为字节
                    audio_bytes = audio_data.tobytes()
                    
                    # 发送到豆包
                    await client.send_audio_chunk(audio_bytes, is_last=False)
                    
                except queue.Empty:
                    print("⚠️  音频队列为空")
                    break
                
                # 等待下一个音频块
                await asyncio.sleep(CHUNK_DURATION)
        
        is_recording = False
        
        # 发送结束标记
        print("\n⏸️  录音结束，等待最终结果...\n")
        await client.send_audio_chunk(b'', is_last=True)
        
        # 等待接收完成
        await receive_task
        
        # 4. 显示结果
        if final_text:
            print("\n" + "=" * 60)
            print(f"🎉 识别完成：{final_text}")
            print("=" * 60)
        else:
            print("\n⚠️  未识别到内容（请确保麦克风正常工作）")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # 5. 关闭连接
        await client.close()




if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🎤 豆包流式语音识别 - 实时测试")
    print("=" * 60)
    print("\n说明：")
    print("  - 此程序会直接从麦克风录音")
    print("  - 实时发送到豆包服务进行识别")
    print("  - 识别结果会实时显示")
    print("\n要求：")
    print("  - 确保麦克风正常工作")
    print("  - 确保网络连接正常")
    print("  - 已安装依赖：pip install websockets sounddevice numpy")
    
    input("\n按 Enter 键开始测试...")
    
    try:
        asyncio.run(test_real_time_recognition())
    except KeyboardInterrupt:
        print("\n\n👋 测试已取消")
    except Exception as e:
        print(f"\n\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

