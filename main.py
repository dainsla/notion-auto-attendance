from fastapi import FastAPI, APIRouter, Request
from fastapi.responses import RedirectResponse
from auto import router as auto_router
import requests
from urllib.parse import urlencode
from dotenv import load_dotenv
import os
import json


# .env 로딩
load_dotenv()

# 환경 변수 로딩
CLIENT_ID = os.getenv("NOTION_CLIENT_ID")
CLIENT_SECRET = os.getenv("NOTION_CLIENT_SECRET")
REDIRECT_URI = os.getenv("NOTION_REDIRECT_URI")

# 환경 변수 검사
if not CLIENT_ID or not CLIENT_SECRET or not REDIRECT_URI:
    raise ValueError("Missing required environment variables")

# FastAPI 앱 생성
app = FastAPI()
# OAuth 인증 라우터 정의
auth_router = APIRouter()


def save_token_to_file(user_id, token_data):
    os.makedirs("user_tokens", exist_ok=True)
    file_path = f"user_tokens/{user_id}.json"
    with open(file_path, "w") as f:
        json.dump(token_data, f, indent=2)

@auth_router.get("/auth")
def auth_start():
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "owner": "user",
        "redirect_uri": REDIRECT_URI,  # 여기에서 .env에서 가져온 값 사용
    }
    url = f"https://api.notion.com/v1/oauth/authorize?{urlencode(params)}"
    return RedirectResponse(url)

@auth_router.get("/auth/callback")
def auth_callback(request: Request):
    code = request.query_params.get("code")
    if not code:
        return {"error": "No code"}

    # Access token 요청
    token_url = "https://api.notion.com/v1/oauth/token"
    headers = {"Content-Type": "application/json"}
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,  # .env에서 가져온 REDIRECT_URI 사용
    }

    try:
        res = requests.post(token_url, headers=headers, json=data, auth=(CLIENT_ID, CLIENT_SECRET))
        res.raise_for_status()
        token_data = res.json()
        user_id = token_data["owner"]["user"]["id"]
        save_token_to_file(user_id, token_data)
        return RedirectResponse(f"/?user_id={user_id}")
    except Exception as e:
        return {"error": str(e)}
    
    
app.include_router(auth_router)   # 👉 인증 관련 라우터 (/auth, /auth/callback)
app.include_router(auto_router)   # 👉 자동 출석 관련 라우터 (/)