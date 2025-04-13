import os
import requests
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from datetime import datetime
from dotenv import load_dotenv



# 🔐 Notion API 정보
NOTION_TOKEN = "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"
ATTENDANCE_DB_ID = "1d1fbe500a9e808a9291f31ef415427d"
CLASS_DB_ID = "1d1fbe500a9e806caf47c677171307ec"

# .env 파일 로딩
load_dotenv()
access_token = os.getenv("ACCESS_TOKEN")

headers = {
    "Authorization": f"Bearer {access_token}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

# 라우터 정의
router = APIRouter()

@router.get("/", response_class=HTMLResponse)
def auto_run_root():
    result = run_auto_attendance()

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


def get_today_weekday_korean():
    days = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
    return days[datetime.today().weekday()]

def get_today_classes():
    url = f"https://api.notion.com/v1/databases/{CLASS_DB_ID}/query"
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

def create_attendance_page(student_id, class_id, student_name, class_name):
    today_str = datetime.today().strftime("%Y.%m.%d")
    title = f"{today_str} / {student_name}"
    data = {
        "parent": { "database_id": ATTENDANCE_DB_ID },
        "properties": {
            "제목": { "title": [{"text": { "content": title }}] },
            "날짜": { "date": { "start": datetime.today().date().isoformat() }},
            "학생": { "relation": [{ "id": student_id }] },
            "수업": { "relation": [{ "id": class_id }] }
        }
    }
    response = requests.post("https://api.notion.com/v1/pages", headers=headers, json=data)
    
    if response.status_code != 200:
        print("❌ 생성 실패!")
        print("Status Code:", response.status_code)
        print("Response:", response.text)

    return response.status_code, response.json()

def get_student_name_map(student_ids):
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


def run_auto_attendance():
    classes = get_today_classes()
    if not classes:
        print("⚠️ 오늘 요일에 해당하는 수업이 없습니다.")
        return []
    
    all_student_ids = list({sid for c in classes for sid in c["student_ids"]})
    student_name_map = get_student_name_map(all_student_ids)

    results = []
    for c in classes:
        student_names = []
        for student_id in c["student_ids"]:
            student_name = student_name_map.get(student_id, "이름없음")
            status, result = create_attendance_page(student_id, c["id"], student_name, c["name"])
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

