from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
import requests
from datetime import datetime

app = FastAPI()

# 🔐 Notion API 정보
NOTION_TOKEN = "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"
ATTENDANCE_DB_ID = "1d1fbe500a9e808a9291f31ef415427d"
CLASS_DB_ID = "1d1fbe500a9e806caf47c677171307ec"

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

# ✅ 안내용 메인 루트 (Render용 + 유저 입장 안내용)
@app.get("/", response_class=HTMLResponse)
def root():
    return """
    <html>
        <head><title>출석 시스템</title></head>
        <body style="font-family:sans-serif;">
            <h2>✅ 자동 출석 시스템 서버가 정상 작동 중입니다</h2>
            <p><a href="/run-attendance">👉 출석 자동 실행하러 가기</a></p>
        </body>
    </html>
    """

# ✅ 실제 출석 자동화 기능
@app.api_route("/run-attendance", methods=["GET", "POST"])
def run_attendance(request: Request):
    result = run_auto_attendance()

    if request.method == "GET":
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
            html_content += "<h3>✅ 출석부 불러오기 성공!</h3>"
        return HTMLResponse(content=html_content)
    
    return JSONResponse(content={"status": "success", "message": "출석 자동화 완료!"})


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
        props = res.json().get("properties", {})
        student_name = "이름없음"
        for key, value in props.items():
            if value.get("type") == "title":
                title_list = value.get("title", [])
                if title_list:
                    texts = [t.get("text", {}).get("content", "") for t in title_list]
                    student_name = "".join(texts).strip()
                    break
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
