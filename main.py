from fastapi import FastAPI, APIRouter, Request
from fastapi.responses import RedirectResponse
import requests
from urllib.parse import urlencode
from dotenv import load_dotenv
import os


# .env 로딩
load_dotenv()

# 환경 변수 로딩
CLIENT_ID = os.getenv("NOTION_CLIENT_ID")
CLIENT_SECRET = os.getenv("NOTION_CLIENT_SECRET")
REDIRECT_URI = os.getenv("NOTION_REDIRECT_URI")

# FastAPI 앱 생성
app = FastAPI()

# OAuth 인증 라우터 정의
auth_router = APIRouter()

@auth_router.get("/auth")
def auth_start():
    print(f"REDIRECT_URI: {REDIRECT_URI}")
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "owner": "user",
        "redirect_uri": REDIRECT_URI,  # 여기에서 .env에서 가져온 값 사용
    }
    print("✅ redirect_uri:", REDIRECT_URI)
    auth_url = f"https://api.notion.com/v1/oauth/authorize?{urlencode(params)}"
    return RedirectResponse(auth_url)

@auth_router.get("/auth/callback")
def auth_callback(request: Request):
    code = request.query_params.get("code")
    print(f"👉 인증 코드: {code}")
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

# 메인 애플리케이션에 라우터 포함
app.include_router(auth_router)