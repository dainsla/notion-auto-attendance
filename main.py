import os
import requests
from fastapi import APIRouter, Request, FastAPI
from fastapi.responses import RedirectResponse
from urllib.parse import urlencode
from dotenv import load_dotenv
from auto import router as auto_router


# .env 로딩 (로컬 개발 시)
load_dotenv()

# FastAPI 앱 생성
app = FastAPI()

# 라우터 정의
router = APIRouter()

# auto.py의 라우터를 main.py에 포함
app.include_router(auto_router)

# 환경 변수 로딩
CLIENT_ID = os.getenv("NOTION_CLIENT_ID")
CLIENT_SECRET = os.getenv("NOTION_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")  # .env 파일에서 가져오기

@router.get("/auth")
def auth_start():
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "owner": "user",
        "redirect_uri": REDIRECT_URI,  # 여기에서 .env에서 가져온 값 사용
    }
    auth_url = f"https://api.notion.com/v1/oauth/authorize?{urlencode(params)}"
    return RedirectResponse(auth_url)

@router.get("/auth/callback")
def auth_callback(request: Request):
    code = request.query_params.get("code")
    if not code:
        return {"error": "Authorization code not found"}

    # Access token 요청
    token_url = "https://api.notion.com/v1/oauth/token"
    headers = {"Content-Type": "application/json"}
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,  # .env에서 가져온 REDIRECT_URI 사용
    }

    auth = (CLIENT_ID, CLIENT_SECRET)
    response = requests.post(token_url, headers=headers, json=data, auth=auth)

    if response.status_code == 200:
        token_data = response.json()
        return {
            "✅ Access Token 발급 완료": token_data
        }
    else:
        return {
            "❌ Access Token 발급 실패": response.json()
        }
