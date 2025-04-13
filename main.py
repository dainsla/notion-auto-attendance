import os
import requests
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from urllib.parse import urlencode
from dotenv import load_dotenv

# .env 로딩 (로컬 개발 시)
load_dotenv()

router = APIRouter()

CLIENT_ID = os.getenv("NOTION_CLIENT_ID")
CLIENT_SECRET = os.getenv("NOTION_CLIENT_SECRET")
REDIRECT_URI = "https://notion-auto-attendance.onrender.com/auth/callback"

@router.get("/auth")
def auth_start():
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "owner": "user",
        "redirect_uri": REDIRECT_URI,
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
        "redirect_uri": REDIRECT_URI,
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