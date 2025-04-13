import os
from fastapi import FastAPI
from dotenv import load_dotenv
from auto import router as auto_router


# .env 로딩 (로컬 개발 시)
load_dotenv()

# FastAPI 앱 생성
app = FastAPI()

app.include_router(auto_router)
