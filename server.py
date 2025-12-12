from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import uvicorn
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 导入 Vercel 使用的 FastAPI 应用
from api.index import app as vercel_app

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 创建本地开发应用，直接复用 Vercel 的应用
app = vercel_app

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


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
