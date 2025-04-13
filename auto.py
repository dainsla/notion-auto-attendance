import os
import requests
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from urllib.parse import urlencode
from datetime import datetime
from dotenv import load_dotenv
import json
from pymongo import MongoClient

# .env 파일 로드
load_dotenv()

# 🔐 Notion API 정보
REDIRECT_URI = os.getenv("NOTION_REDIRECT_URI")
CLIENT_ID = os.getenv("NOTION_CLIENT_ID")
CLIENT_SECRET = os.getenv("NOTION_CLIENT_SECRET")
MONGODB_URI = os.getenv("MONGODB_URI")

# MongoDB 연결
mongo_client = MongoClient(MONGODB_URI)
db = mongo_client["notion_attendance"]
config_collection = db["user_configs"]

# 라우터 정의
router = APIRouter()

# 토큰 불러오기 (파일 기반)
def get_access_token(user_id):
    token_file = f"user_tokens/{user_id}.json"
    if not os.path.exists(token_file):
        raise FileNotFoundError(f"🔑 Token file for user '{user_id}' not found.")
    with open(token_file, "r") as f:
        token_data = json.load(f)
        return token_data["access_token"]

# 헤더 불러오기
def get_headers(user_id):
    access_token = get_access_token(user_id)
    return {
        "Authorization": f"Bearer {access_token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

# 사용자 설정 가져오기
def get_user_config(user_id):
    user_id = str(user_id).strip()
    print(f"🔍 [get_user_config] 요청된 user_id: {user_id}")
    
    config = config_collection.find_one({"user_id": user_id})
    print(f"🔍 [get_user_config] 조회된 설정: {config}")
    
    if not config:
        raise ValueError("❗ 설정 정보가 없습니다. 먼저 /setup 을 완료하세요.")
    
    return config["class_db_id"], config["attendance_db_id"]

# 루트 라우터 - 출석 자동화 실행
@router.get("/", response_class=HTMLResponse)
def auto_run_root(request: Request):
    user_id = request.query_params.get("user_id")
    if not user_id:
        return HTMLResponse("❗ 사용자 정보 없음 (user_id 누락)", status_code=400)

    try:
        result = run_auto_attendance(user_id)
    except Exception as e:
        return HTMLResponse(f"❗ 오류 발생: {str(e)}", status_code=500)

    today = datetime.today()
    day_str = today.strftime("%Y-%m-%d")
    weekday_str = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"][today.weekday()]
    html_content = f"<h2>{day_str} ({weekday_str})</h2>"

    if not result:
        html_content += "<p>❗오늘은 수업이 없습니다.</p>"
    else:
        for cls in result:
            student_names = ", ".join(cls['student_names'])
            html_content += f"<p>📚 {cls['name']} : 👩‍🎓 {student_names}</p>"
        html_content += "<h3>✅ 출석부 생성 완료!</h3>"

    return HTMLResponse(content=html_content)

# 오늘 요일 확인
def get_today_weekday_korean():
    days = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
    return days[datetime.today().weekday()]

# 수업 가져오기
def get_today_classes(headers, class_db_id):
    url = f"https://api.notion.com/v1/databases/{class_db_id}/query"
    res = requests.post(url, headers=headers)
    results = res.json().get("results", [])
    today_classes = []
    today = get_today_weekday_korean()
    for item in results:
        props = item.get("properties", {})
        class_name = props.get("수업명", {}).get("title", [{}])[0].get("text", {}).get("content", "수업")
        class_days = props.get("요일", {}).get("multi_select", [])
        day_list = [day.get("name") for day in class_days]
        if today in day_list:
            class_id = item["id"]
            students = props.get("수강생", {}).get("relation", [])
            student_ids = [s["id"] for s in students]
            today_classes.append({"id": class_id, "name": class_name, "student_ids": student_ids})
    return today_classes

# 출석 페이지 생성
def create_attendance_page(student_id, class_id, student_name, class_name, attendance_db_id, headers):
    today_str = datetime.today().strftime("%Y.%m.%d")
    title = f"{today_str} / {student_name}"
    data = {
        "parent": {"database_id": attendance_db_id},
        "properties": {
            "제목": {"title": [{"text": {"content": title}}]},
            "날짜": {"date": {"start": datetime.today().date().isoformat()}},
            "학생": {"relation": [{"id": student_id}]},
            "수업": {"relation": [{"id": class_id}]}
        }
    }
    response = requests.post("https://api.notion.com/v1/pages", headers=headers, json=data)

    if response.status_code != 200:
        print("❌ 생성 실패!", response.status_code, response.text)
    return response.status_code, response.json()

# 학생 이름 불러오기
def get_student_name_map(student_ids, headers):
    student_name_map = {}
    for student_id in student_ids:
        url = f"https://api.notion.com/v1/pages/{student_id}"
        res = requests.get(url, headers=headers)
        data = res.json()
        props = data.get("properties", {})
        name_property = props.get("학생이름", {})
        title_list = name_property.get("title", [])
        student_name = "이름없음"
        if title_list:
            texts = [t.get("text", {}).get("content", "") for t in title_list]
            student_name = "".join(texts).strip()
        student_name_map[student_id] = student_name
    return student_name_map

# 출석 자동화 실행
def run_auto_attendance(user_id):
    headers = get_headers(user_id)
    class_db_id, attendance_db_id = get_user_config(user_id)
    classes = get_today_classes(headers, class_db_id)

    if not classes:
        print("⚠️ 오늘 요일에 해당하는 수업이 없습니다.")
        return []

    all_student_ids = list({sid for c in classes for sid in c["student_ids"]})
    student_name_map = get_student_name_map(all_student_ids, headers)

    results = []
    for c in classes:
        student_names = []
        for student_id in c["student_ids"]:
            student_name = student_name_map.get(student_id, "이름없음")
            status, result = create_attendance_page(student_id, c["id"], student_name, c["name"], attendance_db_id, headers)
            if status == 200:
                print(f"✅ {c['name']} - {student_name} 출석 생성 완료")
                student_names.append(student_name)
            else:
                print(f"❌ {c['name']} - {student_name} 생성 실패: {status}")
        results.append({
            "name": c["name"],
            "student_names": student_names
        })
    return results