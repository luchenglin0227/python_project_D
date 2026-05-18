import streamlit as st
import cv2
import numpy as np
import pandas as pd
import fitz
import easyocr
import re
from datetime import datetime, timedelta
from processor import DataProcessor
import database

# --- 1. 初始化與核心邏輯區 ---
@st.cache_resource
def load_ocr():
    """載入 OCR 引擎 (僅初次執行會下載模型)"""
    return easyocr.Reader(['ch_tra', 'en'])

# 1. 這裡要乾乾淨淨的換行，單純初始化 reader
reader = load_ocr()


# 2. 這是我們新加的快取功能，裝飾器一定要寫在 def 的「正上方」喔！
@st.cache_data(show_spinner=False)
def process_ocr_and_heatmap(file_bytes, is_pdf):
    """
    ✨【核心優化：記憶緩衝區】
    只要是同一張圖片，辨識過一次就會把結果牢牢記住！
    """
    if is_pdf:
        img_doc = fitz.open(stream=file_bytes, filetype="pdf")
        page = img_doc.load_page(0)
        pix = page.get_pixmap(dpi=300)
        img = cv2.imdecode(np.frombuffer(pix.tobytes("png"), np.uint8), cv2.IMREAD_COLOR)
    else:
        img = cv2.imdecode(np.frombuffer(file_bytes, np.uint8), cv2.IMREAD_COLOR)
        
    ocr_results = reader.readtext(img, detail=0)
    full_text = " ".join(ocr_results)
    heat_scores = analyze_heatmap_to_values(img)
    
    return img, full_text, heat_scores
#補



def convert_pdf_to_img(file_bytes):
    """PDF 轉圖片邏輯"""
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    page = doc.load_page(0)
    pix = page.get_pixmap(dpi=300)
    return cv2.imdecode(np.frombuffer(pix.tobytes("png"), np.uint8), cv2.IMREAD_COLOR)

def analyze_heatmap_to_values(img):
    """
    【光譜數值映射版】
    直接將每一格彩色像素的平均色調 (Hue)，精確映射為 0.0 - 100.0 的方位命中率。
    """
    h, w, _ = img.shape
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    # 建立遮罩：過濾出光譜上有顏色的彩色像素 (忽略白底、灰字、黑網格線)
    lower_bound = np.array([0, 40, 40])
    upper_bound = np.array([100, 255, 255])
    color_mask = cv2.inRange(hsv, lower_bound, upper_bound)
    
    # 【自動定位核心】計算每一行的彩色像素數量，尋找熱點集中的區域
    row_counts = np.sum(color_mask > 0, axis=1)
    search_start = int(h * 0.55)
    active_rows = np.where(row_counts[search_start:] > (w * 0.01))[0]
    
    if len(active_rows) > 0:
        y_start = search_start + active_rows[0] - 10  # 往上留點緩衝
        y_end = search_start + active_rows[-1] + 10   # 往下留點緩衝
    else:
        y_start, y_end = int(h * 0.63), int(h * 0.92)
        
    x_start, x_end = int(w * 0.06), int(w * 0.94)
    
    # 裁切出九宮格的 HSV 與 遮罩區域
    roi_hsv = hsv[y_start:y_end, x_start:x_end]
    roi_mask = color_mask[y_start:y_end, x_start:x_end]
    
    # 切成 3x3 矩陣
    h_rows = np.array_split(roi_hsv, 3, axis=0)
    
    values = []
    
    for r_idx in range(3):
        h_cols = np.array_split(h_rows[r_idx], 3, axis=1)
        # 確保遮罩切分與 HSV 矩陣完全同步
        m_cols = np.array_split(np.array_split(roi_mask, 3, axis=0)[r_idx], 3, axis=1)
        
        for c_idx in range(3):
            cell_hsv = h_cols[c_idx]
            cell_mask = m_cols[c_idx]
            
            # 抽出該格子內真正屬於熱點顏色的像素
            colored_pixels = cell_hsv[cell_mask > 0]
            
            if len(colored_pixels) == 0:
                # 沒彩色色塊 = 該區域沒有失誤紀錄 = 100.0% 完美命中
                values.append(100.0)
            else:
                # 抓取有顏色像素的「平均色調 (Hue)」
                avg_hue = np.mean(colored_pixels[:, 0])
                
                # 線性映射演算法：將 Hue 範圍 (0 ~ 85) 對應到 命中率 (0% ~ 100%)
                # 越接近 85 (深綠色) 命中率越高；越接近 0 (橘紅色) 命中率越低
                hit_rate = (avg_hue / 85.0) * 100
                
                # 安全邊界限制
                hit_rate = max(0.0, min(100.0, hit_rate))
                values.append(round(hit_rate, 1))
                
    return values

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

# 優化：
if uploaded_file:
    # 先讀取檔案的二進位內容
    file_bytes = uploaded_file.read()
    is_pdf = uploaded_file.type == "application/pdf"

    # 使用 st.spinner 只在「第一次辨識」時提示
    with st.spinner("正在執行 AI 辨識與光譜映射分析（初次讀取耗時較久，請稍候）..."):
        # 呼叫有快取記憶的函數
        img, full_text, heat_scores = process_ocr_and_heatmap(file_bytes, is_pdf)

    # ─── 底下原本的 col_img, col_form = st.columns([4, 6]) 那些都不要動，照舊即可 ───

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

        # 4. 空間分析矩陣 (Heatmap Matrix) - 回歸精準數值調整框
        with st.expander("🔥 空間分析矩陣 (方位命中率 %)", expanded=True):
            st.info("系統已根據光譜顏色自動換算命中率 (偏綠接近100%，偏橘紅接近0%)")
            grid_cols = st.columns(3)
            matrix_names = [
                "miss_left_high", "miss_middle_high", "miss_right_high",
                "miss_left_mid", "miss_middle_mid", "miss_right_mid",
                "miss_left_low", "miss_middle_low", "miss_right_low"
            ]
            
            matrix_values = {}
            for i, name in enumerate(matrix_names):
                # 將自動辨識的命中率小數帶入輸入框，供使用者手動微調
                matrix_values[name] = grid_cols[i % 3].number_input(
                    name, 
                    min_value=0.0, 
                    max_value=100.0, 
                    value=float(heat_scores[i]), 
                    step=0.1
                )

        if st.button("💾 確認存檔"):
            # 組裝 OCR 辨識的資料（送往同學的 DataProcessor）
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
                
                # ✨【核心改動：在這裡直接將資料推上 Google Sheets 雲端】
                with st.spinner("正在將資料即時同步至雲端 Google Sheets..."):
                    success = database.insert_record(clean_df)
                
                if success:
                    st.success("🎉 資料已成功結構化，並即時同步至雲端 Google Sheets 資料庫！")
                    # 轉成直式顯示，避免 pyarrow 型別衝突
                    display_df = pd.DataFrame({
                        "欄位": clean_df.columns.tolist(),
                        "數值": [str(v) for v in clean_df.iloc[0].tolist()]
                    })
                    st.dataframe(display_df, height=600)
                else:
                    st.error("❌ 資料已成功結構化，但同步到雲端時失敗，請檢查網路或密鑰設定。")

                # 保留原本的 CSV 下載按鈕作為第二備援方案
                csv = clean_df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 備份：下載本次清洗後 CSV", data=csv, file_name=f"{record_date}_log.csv")

            except ValueError as e:
                st.error(f"❌ 資料驗證失敗：{e}")


# ─────────────────────────────────────────────────────────────────
# ✨【新增功能：即時雲端歷史紀錄看板】
# ─────────────────────────────────────────────────────────────────

st.markdown("---")
st.header("📜 雲端歷史紀錄總覽 (Google Sheets 直連)")

# 建立一個刷新按鈕，讓使用者可以手動同步最新資料
if st.button("🔄 重新整理雲端資料"):
    # 只清除歷史紀錄的快取，不影響 OCR 模型
    database.get_all_records.clear()
    st.rerun()
try:
    with st.spinner("正在讀取雲端最新歷史紀錄..."):
        # 呼叫讀取功能（等一下我們會在 database.py 補上這個功能）
        history_df = database.get_all_records()
        
    if history_df is not None and not history_df.empty:
        # 計算一下總共有幾筆
        total_records = len(history_df)
        st.metric(label="📊 目前已累積總筆數", value=f"{total_records} 筆")
        
        # 漂亮的表格顯示，支援網頁上直接搜尋、排序、篩選
        st.dataframe(
            history_df, 
            use_container_width=True,
            height=400
        )
    else:
        st.warning("📭 雲端目前沒有任何紀錄，或者分頁標題不正確。")

except Exception as e:
    st.error(f"❌ 無法讀取歷史紀錄：{e}")