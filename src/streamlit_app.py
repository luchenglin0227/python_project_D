import streamlit as st
import sqlite3
from datetime import datetime

# =========================
# Database
# =========================

conn = sqlite3.connect("shooting_data.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    upload_time TEXT,
    sleep_hours REAL,
    sleep_quality INTEGER,
    calories INTEGER,
    carbs INTEGER,
    protein INTEGER,
    fat INTEGER,
    mood TEXT,
    warmup_minutes INTEGER,
    shooting_range TEXT,
    hit INTEGER,
    direction TEXT,
    height TEXT,
    report_name TEXT
)
""")
conn.commit()

# =========================
# Page Config
# =========================

st.set_page_config(
    page_title="飛靶競賽分析系統",
    layout="wide"
)

st.title("不定向飛靶競賽表現分析系統")

st.markdown("---")

# =========================
# Sidebar
# =========================

st.sidebar.header("功能選單")

page = st.sidebar.radio(
    "前往頁面",
    [
        "資料輸入",
        "Dashboard"
    ]
)

# =========================
# Data Input Page
# =========================

if page == "資料輸入":

    st.header("上傳與資料輸入")

    col1, col2 = st.columns(2)

    with col1:

        report_file = st.file_uploader(
            "上傳飛靶報表",
            type=["pdf", "jpg", "png"]
        )

        athlete_photo = st.file_uploader(
            "上傳當日照片",
            type=["jpg", "png", "jpeg"]
        )

        if athlete_photo:
            st.image(athlete_photo, width=300)

    with col2:

        sleep_hours = st.slider(
            "昨晚睡眠時間",
            0.0,
            12.0,
            7.0,
            0.5
        )
        
        sleep_quality = st.slider(
        "昨晚睡眠品質",
        1,
        10,
        7
    )

        arrival_time = st.time_input(
        "抵達靶場時間"
    )

        warmup_minutes = st.number_input(
        "熱身時間（分鐘）",
        min_value=0,
        max_value=180,
        value=20
    )
        
        st.subheader("早餐營養資訊")

calories = st.number_input(
    "早餐卡路里（kcal）",
    min_value=0,
    max_value=3000,
    value=500
)

carbs = st.number_input(
    "碳水化合物（g）",
    min_value=0,
    max_value=500,
    value=50
)

protein = st.number_input(
    "蛋白質（g）",
    min_value=0,
    max_value=300,
    value=25
)

fat = st.number_input(
    "脂肪（g）",
    min_value=0,
    max_value=300,
    value=20
)

        mood = st.select_slider(
            "主觀精神狀態",
            options=[
                "非常差",
                "差",
                "普通",
                "好",
                "非常好"
            ]
        )

     
        shooting_range = st.selectbox(
            "比賽靶場",
            [
                "林口靶場a",
                "林口靶場b",
                "林口靶場c",
            ]
        )

    st.markdown("---")

    st.subheader("AI 分析結果（模擬）")

    if st.button("開始分析"):

        st.success("報表解析完成")

        st.info("熱區分析：右上區域命中偏低")

        st.warning("偵測到壓力偏高，可能影響命中率")

        st.subheader("人工確認")

        confirmed = st.checkbox("確認分析結果")

        if confirmed:

            cursor.execute("""
INSERT INTO records (
    upload_time,
    sleep_hours,
    sleep_quality,
    calories,
    carbs,
    protein,
    fat,
    mood,
    warmup_minutes,
    shooting_range,
    hit,
    direction,
    height,
    report_name
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (
    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    sleep_hours,
    sleep_quality,
    calories,
    carbs,
    protein,
    fat,
    mood,
    warmup_minutes,
    shooting_range,
    1,              # 暫時用 1 當 hit（模擬）
    "center",       # 模擬 direction
    "mid",          # 模擬 height
    report_file.name if report_file else "None"
))
            conn.commit()

            st.success("資料已成功儲存至資料庫")

# =========================
# Dashboard
# =========================

elif page == "Dashboard":

    st.header("Dashboard")

    cursor.execute("SELECT * FROM records")

    rows = cursor.fetchall()

    if rows:

        st.write("歷史紀錄")

        st.dataframe(rows)

        import pandas as pd

df = pd.DataFrame(rows, columns=[
    "id", "upload_time",
    "sleep_hours", "sleep_quality",
    "calories", "carbs", "protein", "fat",
    "mood", "warmup_minutes",
    "shooting_range",
    "hit", "direction", "height",
    "report_name"
])

st.subheader("Performance KPI")

hit_rate = df["hit"].mean()
miss_rate = 1 - hit_rate

col1, col2 = st.columns(2)

with col1:
    st.metric("Hit Rate", f"{hit_rate:.2%}")

with col2:
    st.metric("Miss Rate", f"{miss_rate:.2%}")
    
    st.subheader("Performance Trend")

df["date"] = pd.to_datetime(df["upload_time"]).dt.date

trend = df.groupby("date")["hit"].mean()

st.line_chart(trend)

st.metric(
            "總資料筆數",
            len(rows)
        )

    else:

        st.info("目前尚無資料")
