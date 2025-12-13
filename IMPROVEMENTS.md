# 问诊系统改进说明

## 问题描述

1. **按钮禁用问题**: Agent正在分析期间(LLM生成回复+流式TTS播放),所有按钮被禁用,用户无法操作
2. **缺少中断机制**: 用户无法中断Agent当前的思考和语音播放,必须等待完成才能继续

## 解决方案

### 1. 添加全局中断标志和TTS中断机制

#### 新增状态变量
```javascript
const isAgentThinking = ref(false);      // Agent是否正在思考(LLM+TTS)
const currentAudioContext = ref(null);   // 当前TTS的AudioContext
const shouldInterrupt = ref(false);       // 中断标志
```

#### 增强的stopTTS函数
- 停止传统Audio播放
- 关闭流式TTS的AudioContext
- 清理所有音频资源

#### 新增interruptAgent函数
```javascript
const interruptAgent = () => {
    // 设置中断标志
    shouldInterrupt.value = true;
    
    // 停止TTS播放
    stopTTS();
    
    // 清理Agent思考状态
    isAgentThinking.value = false;
    isLoading.value = false;
    
    // 移除最后一条未完成的AI消息
}
```

### 2. 修改前端按钮逻辑,生成期间保持可用

#### 移除所有按钮的`:disabled="isLoading"`属性
- 症状选项按钮
- 确认提交按钮
- 相机按钮
- 语音/键盘切换按钮
- 录音按钮
- 添加按钮
- 发送按钮

现在所有按钮在Agent思考期间都保持可用状态。

### 3. 实现用户输入时中断当前agent流程

#### sendMessage函数
```javascript
// 如果Agent正在思考，先中断
if (isAgentThinking.value || isLoading.value) {
    interruptAgent();
    await new Promise(resolve => setTimeout(resolve, 100)); // 等待中断完成
}

// 重置中断标志
shouldInterrupt.value = false;
isLoading.value = true;
isAgentThinking.value = true;
```

#### submitSelectedOptions函数
- 同样的中断逻辑
- 在提交选项前先中断当前Agent

#### startRecording函数
- 录音开始前先中断当前Agent
- 确保用户可以随时打断AI说话

### 4. 清理被中断的消息和状态

#### 在关键点检查中断标志

**LLM响应后检查**:
```javascript
if (shouldInterrupt.value) {
    console.log('🛑 [中断] LLM响应后检测到中断，放弃处理');
    isLoading.value = false;
    isAgentThinking.value = false;
    return;
}
```

**TTS播放期间检查**:
```javascript
while (true) {
    // 每次循环检查中断标志
    if (shouldInterrupt.value) {
        console.log('🛑 [中断] TTS播放期间检测到中断，停止接收');
        reader.cancel(); // 取消读取流
        audioCtx.close(); // 关闭音频上下文
        currentAudioContext.value = null;
        isAgentThinking.value = false;
        return;
    }
    
    const { done, value } = await reader.read();
    // ...
}
```

#### displayAIMessageWithTTS函数改进
- 保存AudioContext引用以便中断
- 在流式接收音频时持续检查中断标志
- 被中断时立即取消流读取和关闭音频上下文
- 确保isAgentThinking状态正确清理

## 技术亮点

### 1. 非阻塞式中断
- 用户操作立即响应,不需要等待
- 中断标志在多个关键点检查
- 异步流程可以优雅地中止

### 2. 资源清理
- AudioContext正确关闭
- 流式读取器取消
- 状态变量重置

### 3. 用户体验优化
- 按钮始终可用,不会"卡住"
- 可以随时打断AI说话
- 新输入立即处理,无需等待

## 测试场景

### 场景1: 打字中断语音
1. AI正在播放语音回复
2. 用户开始打字并发送消息
3. ✅ 语音立即停止
4. ✅ 新消息立即处理

### 场景2: 语音中断语音
1. AI正在播放语音回复
2. 用户按下录音按钮
3. ✅ 语音立即停止
4. ✅ 录音立即开始

### 场景3: 选项提交中断
1. AI正在思考或播放语音
2. 用户点击症状选项并提交
3. ✅ 当前流程立即中断
4. ✅ 选项立即提交并处理

### 场景4: 按钮始终可用
1. AI正在生成回复(loading状态)
2. ✅ 所有按钮保持可点击状态
3. ✅ 用户可以随时操作

## 代码改动总结

- **新增**: 3个状态变量 (isAgentThinking, currentAudioContext, shouldInterrupt)
- **新增**: 1个中断函数 (interruptAgent)
- **修改**: stopTTS函数 (增加AudioContext清理)
- **修改**: 6个用户交互函数 (sendMessage, submitSelectedOptions, startRecording等)
- **修改**: displayAIMessageWithTTS函数 (增加中断检查)
- **移除**: 8处按钮的disabled属性

## 注意事项

1. 中断后需要等待100ms让清理完成
2. shouldInterrupt标志在新请求开始时重置
3. isAgentThinking在TTS完成或中断时清理
4. 所有异步流程都需要检查中断标志

