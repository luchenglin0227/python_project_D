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
    breakfast TEXT,
    mood TEXT,
    stress_level INTEGER,
    shooting_range TEXT,
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

st.title("🎯 不定向飛靶競賽表現分析系統")

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

    st.header("📄 上傳與資料輸入")

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

        breakfast = st.selectbox(
            "早餐狀況",
            [
                "未進食",
                "簡單早餐",
                "正常早餐",
                "高蛋白早餐"
            ]
        )

        mood = st.select_slider(
            "心理狀態",
            options=[
                "非常差",
                "差",
                "普通",
                "好",
                "非常好"
            ]
        )

        stress_level = st.slider(
            "壓力程度",
            1,
            10,
            5
        )

        shooting_range = st.selectbox(
            "今日靶場",
            [
                "台北靶場",
                "桃園靶場",
                "台中靶場",
                "高雄靶場"
            ]
        )

    st.markdown("---")

    st.subheader("🧠 AI 分析結果（模擬）")

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
                breakfast,
                mood,
                stress_level,
                shooting_range,
                report_name
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                sleep_hours,
                breakfast,
                mood,
                stress_level,
                shooting_range,
                report_file.name if report_file else "None"
            ))

            conn.commit()

            st.success("資料已成功儲存至資料庫")

# =========================
# Dashboard
# =========================

elif page == "Dashboard":

    st.header("📊 Dashboard")

    cursor.execute("SELECT * FROM records")

    rows = cursor.fetchall()

    if rows:

        st.write("歷史紀錄")

        st.dataframe(rows)

        st.metric(
            "總資料筆數",
            len(rows)
        )

    else:

        st.info("目前尚無資料")
