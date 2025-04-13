from fastapi import FastAPI, APIRouter, Request
from fastapi.responses import RedirectResponse
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
    try:
        response = requests.post(token_url, headers=headers, json=data, auth=auth)
        response.raise_for_status()  # 응답 상태 코드가 2xx가 아니면 예외를 던짐
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {e}"}
    

    if response.status_code == 200:
        token_data = response.json()

        # 저장 함수 호출
        user_id = token_data["owner"]["user"]["id"]  # 사용자 고유 ID
        save_token_to_file(user_id, token_data)

        # 사용자 ID 포함하여 루트 페이지로 리디렉션
        return RedirectResponse(f"/?user_id={user_id}")
    else:
        return {"❌ Access Token 발급 실패": response.json()}

# 메인 애플리케이션에 라우터 포함
app.include_router(auth_router)