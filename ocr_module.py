import streamlit as st
import cv2
import numpy as np
import pandas as pd
import fitz
import easyocr
import re
from datetime import datetime, timedelta
from processor import DataProcessor

# --- 1. 初始化與核心邏輯區 ---

@st.cache_resource
def load_ocr():
    return easyocr.Reader(['ch_tra', 'en'])

reader = load_ocr()

def convert_pdf_to_img(file_bytes):
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    page = doc.load_page(0)
    pix = page.get_pixmap(dpi=300)
    return cv2.imdecode(np.frombuffer(pix.tobytes("png"), np.uint8), cv2.IMREAD_COLOR)

def analyze_heatmap_matrix(img):
    """空間分析矩陣：計算 3x3 區域的像素強度"""
    h, w, _ = img.shape
    y_start, y_end = int(h * 0.62), int(h * 0.93)
    x_start, x_end = int(w * 0.05), int(w * 0.95)
    heatmap_roi = img[y_start:y_end, x_start:x_end]
    
    hsv = cv2.cvtColor(heatmap_roi, cv2.COLOR_BGR2HSV)
    rows = np.array_split(hsv, 3, axis=0)
    scores = []
    
    for r in rows:
        cols = np.array_split(r, 3, axis=1)
        for cell in cols:
            s_channel = cell[:, :, 1]
            avg_s = np.mean(s_channel)
            scores.append(round(avg_s / 255.0 * 100, 1))
    return scores

def calculate_sleep_duration(bed, wake):
    """計算睡眠時長 (sleep_duration)"""
    today = datetime.today()
    t_bed = datetime.combine(today, bed)
    t_wake = datetime.combine(today, wake)
    if t_wake <= t_bed: # 代表跨夜
        t_wake += timedelta(days=1)
    diff = t_wake - t_bed
    return round(diff.seconds / 3600, 1)

# --- 2. Streamlit 網頁介面區 ---

st.set_page_config(page_title="Trap Shooting Analytics", layout="wide")
st.title("🏹 飛靶表現與生活因子關聯系統")

uploaded_file = st.file_uploader("上傳成績單 (JPG, PNG, PDF)", type=["jpg", "png", "pdf"])

if uploaded_file:
    # 讀取影像與基礎處理
    if uploaded_file.type == "application/pdf":
        img = convert_pdf_to_img(uploaded_file.read())
    else:
        img = cv2.imdecode(np.frombuffer(uploaded_file.read(), np.uint8), cv2.IMREAD_COLOR)

    with st.spinner("系統正在執行 OCR 與矩陣分析..."):
        ocr_results = reader.readtext(img, detail=0)
        full_text = " ".join(ocr_results)
        heat_scores = analyze_heatmap_matrix(img)

    col_img, col_form = st.columns([4, 6])

    with col_img:
        st.image(cv2.cvtColor(img, cv2.COLOR_BGR2RGB), use_container_width=True)

    with col_form:
        st.subheader("🛠️ 資料錄入面板")
        
        # 1. 基本資訊 (Relational Data)
        with st.expander("🆔 基本資訊", expanded=True):
            c1, c2 = st.columns(2)
            user_id = c1.text_input("user_id", value="USER_001")
            record_date = c2.date_input("record_date", value=datetime(2026, 5, 2))
            match_start_time = st.time_input("match_start_time", value=datetime.strptime("09:00", "%H:%M").time())
            shooting_range = st.selectbox("Shooting_range", ["A", "B", "C"])

        # 3. 賽前生活因子 (Pre-competition Factors)
        with st.expander("🧘 生活因子與生理狀態", expanded=True):
            c3, c4 = st.columns(2)
            bedtime = c3.time_input("bedtime (入睡時間)", value=datetime.strptime("23:00", "%H:%M").time())
            wake_up_time = c4.time_input("wake_up_time (起床時間)", value=datetime.strptime("07:00", "%H:%M").time())
            
            # 自動計算 sleep_duration
            sleep_duration = calculate_sleep_duration(bedtime, wake_up_time)
            st.info(f"系統自動換算 sleep_duration: {sleep_duration} 小時")
            
            c5, c6, c7 = st.columns(3)
            arrival_time = c5.time_input("arrival_time", value=datetime.strptime("08:30", "%H:%M").time())
            warm_up_time = c6.number_input("warm_up_time (min)", value=20.0)
            caffeine_intake = c7.number_input("caffeine_intake (mg)", value=100.0)
            
            c8, c9 = st.columns(2)
            breakfast_calories = c8.number_input("breakfast_calories (kcal)", value=450.0)
            breakfast_protein = c9.number_input("breakfast_protein (g)", value=25.0)
            
            fatigue_level = st.select_slider("fatigue_level (疲勞度)", options=[1, 2, 3, 4, 5], value=2)
            tension_level = st.select_slider("tension_level (緊張度)", options=[1, 2, 3, 4, 5], value=1)

        # 2. 射擊表現 (Shooting Performance) - 模擬 OCR 填充
        with st.expander("📊 射擊表現數據 (OCR 自動帶入)"):
            c10, c11, c12 = st.columns(3)
            total_shots = c10.number_input("total_shots", value=125)
            total_hits = c11.number_input("total_hits", value=101)
            hit_rate = c12.number_input("hit_rate (0-1)", value=0.808, format="%.3f")
            
            c13, c14, c15 = st.columns(3)
            first_hit_count = c13.number_input("first_hit_count", value=96)
            second_hit_count = c14.number_input("second_hit_count", value=5)
            miss_count = c15.number_input("miss_count", value=24)

        # 4. 空間分析矩陣 (Heatmap Matrix)
        with st.expander("🔥 空間分析矩陣 (方位_高度)"):
            grid_cols = st.columns(3)
            # 依照定義命名
            matrix_names = [
                "miss_left_high", "miss_middle_high", "miss_right_high",
                "miss_left_mid", "miss_middle_mid", "miss_right_mid",
                "miss_left_low", "miss_middle_low", "miss_right_low"
            ]
            matrix_values = {}
            for i, name in enumerate(matrix_names):
                matrix_values[name] = grid_cols[i % 3].number_input(name, value=heat_scores[i])

        if st.button("💾 確認存檔"):
            # 組裝 OCR 辨識的資料（射擊表現數值 + 熱區矩陣）
            ocr_data = {
                "總發數": total_shots,
                "一發命中數": first_hit_count,
                "二發命中數": second_hit_count,
                "失誤數": miss_count,
                "heatmap_matrix": [
                    [matrix_values["miss_left_high"], matrix_values["miss_middle_high"], matrix_values["miss_right_high"]],
                    [matrix_values["miss_left_mid"],  matrix_values["miss_middle_mid"],  matrix_values["miss_right_mid"]],
                    [matrix_values["miss_left_low"],  matrix_values["miss_middle_low"],  matrix_values["miss_right_low"]],
                ]
            }

            # 組裝使用者手動輸入的資料
            manual_data = {
                "使用者編號": user_id,
                "射擊日期": record_date,
                "比賽時間": match_start_time,
                "靶場": shooting_range,
                "入睡時間": bedtime,
                "起床時間": wake_up_time,
                "到場時間": arrival_time,
                "熱身時長": warm_up_time,
                "早餐熱量": breakfast_calories,
                "蛋白質": breakfast_protein,
                "咖啡因攝取": caffeine_intake,
                "疲勞程度": fatigue_level,
                "緊張程度": tension_level,
            }

            # 交給 DataProcessor 執行清洗與驗證
            try:
                processor = DataProcessor()
                clean_df = processor.process_record(
                    ocr_data,
                    manual_data,
                    raw_image_path=f"./storage/{user_id}_{record_date}.jpg"
                )
                st.success("資料已成功結構化！")
                st.dataframe(clean_df.T, height=600)

                csv = clean_df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("匯出 CSV 檔案", data=csv, file_name=f"{record_date}_log.csv")

            except ValueError as e:
                # 一致性檢查失敗（例如一發+二發+失誤 ≠ 總發數）
                st.error(f"❌ 資料驗證失敗：{e}")