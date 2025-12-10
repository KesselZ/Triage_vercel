# THU智能分诊辅助系统

基于AI的智能医疗分诊系统，支持症状收集和初步诊断建议。

## 🚀 快速部署到Vercel

### 1. 准备工作
- 注册 [Vercel账号](https://vercel.com)
- 注册 [GitHub账号](https://github.com)

### 2. 上传到GitHub
```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/你的用户名/智能分诊系统.git
git push -u origin main
```

### 3. 部署到Vercel
1. 登录 [Vercel控制台](https://vercel.com/dashboard)
2. 点击 "New Project"
3. 导入GitHub仓库
4. Vercel会自动检测Python项目
5. 配置环境变量：
   - `UNIAPI_API_KEY`: 你的API密钥
   - `UNIAPI_BASE_URL`: `https://hk.uniapi.io/v1`
6. 点击 "Deploy"

### 4. 部署完成
- 前端：自动部署到 `https://你的项目名.vercel.app`
- API：自动部署到 `https://你的项目名.vercel.app/api`

## 📁 项目结构

```
├── api/
│   ├── chat/
│   │   ├── next.py        # 问诊接口
│   │   └── diagnose.py    # 诊断接口
│   └── utils/
│       └── ai_client.py   # AI逻辑
├── public/
│   └── index.html         # 前端页面
├── vercel.json            # Vercel配置
├── requirements.txt       # Python依赖
└── .env.example          # 环境变量模板
```

## 🔧 本地开发

### 环境准备
```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑.env文件，填入你的API密钥
```

### 运行方式1：传统FastAPI
```bash
python server.py
```

### 运行方式2：Vercel本地测试
```bash
# 安装Vercel CLI
npm i -g vercel

# 本地运行
vercel dev
```

## 📊 API接口

### 问诊接口
- **路径**: `/api/chat/next`
- **方法**: POST
- **请求体**: `{"history": [{"role": "user", "content": "症状描述"}]}`

### 诊断接口
- **路径**: `/api/chat/diagnose`
- **方法**: POST
- **请求体**: `{"history": [完整对话历史]}`

## 🎯 功能特性

- ✅ 智能症状收集
- ✅ 选项式交互
- ✅ 可视化推理过程
- ✅ 移动端适配
- ✅ 温暖AI语气
- ✅ 双模型配置

## 💡 技术栈

- **前端**: Vue 3 + Tailwind CSS
- **后端**: Python + Vercel Serverless
- **AI**: OpenAI GPT + UniAPI
- **部署**: Vercel

## 📱 移动端优化

- iPhone 15 Pro Max 完美适配
- iOS安全区域支持
- 响应式设计
- 触摸友好界面

## 🔐 环境变量配置

在Vercel控制台设置以下环境变量：

```
UNIAPI_API_KEY=your_actual_api_key
UNIAPI_BASE_URL=https://hk.uniapi.io/v1
```

## 📄 许可证

MIT License
