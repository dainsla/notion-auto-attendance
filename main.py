from fastapi import FastAPI, APIRouter, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from auto import router as auto_router
import requests
from urllib.parse import urlencode
from dotenv import load_dotenv
import os
import json

# .env 로드
load_dotenv()

# 환경 변수 로드
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

# 토큰 저장 함수
def save_token_to_file(user_id, token_data):
    os.makedirs("user_tokens", exist_ok=True)
    file_path = f"user_tokens/{user_id}.json"
    with open(file_path, "w") as f:
        json.dump(token_data, f, indent=2)

# 사용자 설정 저장 함수
def save_user_config(user_id, attendance_db_id, class_db_id):
    os.makedirs("user_configs", exist_ok=True)
    config = {
        "attendance_db_id": attendance_db_id,
        "class_db_id": class_db_id
    }
    with open(f"user_configs/{user_id}.json", "w") as f:
        json.dump(config, f, indent=2)

# 인증 시작
@auth_router.get("/auth")
def auth_start():
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "owner": "user",
        "redirect_uri": REDIRECT_URI,
    }
    url = f"https://api.notion.com/v1/oauth/authorize?{urlencode(params)}"
    return RedirectResponse(url)

# 인증 후 콜백
@auth_router.get("/auth/callback")
def auth_callback(request: Request):
    code = request.query_params.get("code")
    if not code:
        return {"error": "No code"}

    token_url = "https://api.notion.com/v1/oauth/token"
    headers = {"Content-Type": "application/json"}
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }

    try:
        res = requests.post(token_url, headers=headers, json=data, auth=(CLIENT_ID, CLIENT_SECRET))
        res.raise_for_status()
        token_data = res.json()
        user_id = token_data["owner"]["user"]["id"]
        save_token_to_file(user_id, token_data)

        # ✅ 인증 완료 안내 메시지로 링크 출력
        html_content = f"""
        <html>
        <body>
            <h2>✅ 인증 완료!</h2>
            <p>⬇️ 아래 링크를 복사해서 Notion 템플릿 버튼에 붙이세요:</p>
            <pre style=\"background:#f4f4f4;padding:10px;\">https://notion-auto-attendance.onrender.com/?user_id={user_id}</pre>
            <p>또는 출석용 DB 설정을 하려면 👉 
            <a href=\"/setup?user_id={user_id}\">/setup 페이지로 이동</a></p>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)
    except Exception as e:
        return {"error": str(e)}

# 사용자 설정 입력 폼
@auth_router.get("/setup", response_class=HTMLResponse)
def setup_page(request: Request):
    user_id = request.query_params.get("user_id")
    if not user_id:
        return HTMLResponse("❗ user_id 누락", status_code=400)

    html = f"""
    <html>
    <body>
        <h2>📋 출석 자동화를 위한 DB 설정</h2>
        <form method=\"post\" action=\"/setup\">
            <input type=\"hidden\" name=\"user_id\" value=\"{user_id}\" />
            <label>🗂 출석부 DB ID:<br/><input type=\"text\" name=\"attendance_db_id\" required></label><br/><br/>
            <label>📘 수업 DB ID:<br/><input type=\"text\" name=\"class_db_id\" required></label><br/><br/>
            <button type=\"submit\">📂 저장하기</button>
        </form>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

# 사용자 설정 저장 처리
@auth_router.post("/setup")
def save_user_config_endpoint(
    user_id: str = Form(...),
    attendance_db_id: str = Form(...),
    class_db_id: str = Form(...)
):
    save_user_config(user_id, attendance_db_id, class_db_id)
    return HTMLResponse(f"""
    <h2>✅ 설정 저장 완료</h2>
    <p>이제 다음 링크를 Notion 템플릿 버튼에 붙이면 자동화가 작동합니다:</p>
    <pre>https://notion-auto-attendance.onrender.com/?user_id={user_id}</pre>
    """)

# 라우터 등록
app.include_router(auth_router)
app.include_router(auto_router)
