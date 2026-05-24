import streamlit as st
import cv2
import pandas as pd
from datetime import datetime
from processor import DataProcessor
import database
from ocr_module import process_ocr_and_heatmap, calculate_sleep_duration


def render_page():
    st.title("📸 飛靶 OCR 辨識與雲端同步")

    uploaded_file = st.file_uploader("上傳成績單 (JPG, PNG, PDF)", type=["jpg", "png", "pdf"])

    if uploaded_file:
        file_bytes = uploaded_file.read()
        is_pdf = uploaded_file.type == "application/pdf"

        with st.spinner("正在執行 AI 辨識與光譜映射分析（初次讀取耗時較久，請稍候）..."):
            img, full_text, heat_scores, ocr_conf = process_ocr_and_heatmap(file_bytes, is_pdf)

        col_img, col_form = st.columns([4, 6])

        with col_img:
            st.image(cv2.cvtColor(img, cv2.COLOR_BGR2RGB), use_container_width=True)

        with col_form:
            st.subheader("🛠️ 資料錄入面板")

            # 1. 基本資訊
            with st.expander("🆔 基本資訊", expanded=True):
                c1, c2 = st.columns(2)
                user_id = c1.text_input("user_id", value="USER_001")
                record_date = c2.date_input("record_date", value=datetime(2026, 5, 2))
                match_start_time = st.time_input("match_start_time", value=datetime.strptime("09:00", "%H:%M").time())
                shooting_range = st.selectbox("Shooting_range", ["A", "B", "C"])

            # 2. 生活因子
            with st.expander("🧘 生活因子與生理狀態", expanded=True):
                c3, c4 = st.columns(2)
                bedtime = c3.time_input("bedtime (入睡時間)", value=datetime.strptime("23:00", "%H:%M").time())
                wake_up_time = c4.time_input("wake_up_time (起床時間)", value=datetime.strptime("07:00", "%H:%M").time())

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

            # 3. 射擊表現
            with st.expander("📊 射擊表現數據 (OCR 自動帶入)"):
                c10, c11, c12 = st.columns(3)
                total_shots = c10.number_input("total_shots", value=125)
                total_hits = c11.number_input("total_hits", value=101)
                hit_rate = c12.number_input("hit_rate (0-1)", value=0.808, format="%.3f")

                c13, c14, c15 = st.columns(3)
                first_hit_count = c13.number_input("first_hit_count", value=96)
                second_hit_count = c14.number_input("second_hit_count", value=5)
                miss_count = c15.number_input("miss_count", value=24)

            # 4. 空間分析矩陣
            with st.expander("🔥 空間分析矩陣 (方位命中率 %)", expanded=True):
                st.info("系統已根據光譜顏色自動換算命中率 (偏綠接近100%，偏橘紅接近0%)")
                grid_cols = st.columns(3)
                matrix_names = [
                    "miss_left_high", "miss_middle_high", "miss_right_high",
                    "miss_left_mid",  "miss_middle_mid",  "miss_right_mid",
                    "miss_left_low",  "miss_middle_low",  "miss_right_low"
                ]

                matrix_values = {}
                for i, name in enumerate(matrix_names):
                    matrix_values[name] = grid_cols[i % 3].number_input(
                        name, min_value=0.0, max_value=100.0,
                        value=float(heat_scores[i]), step=0.1
                    )

            if st.button("💾 確認存檔"):
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

                try:
                    processor = DataProcessor()
                    # 加入 ocr_confidence=ocr_conf 參數，讓真實分數進入 DataFrame
                    clean_df = processor.process_record(
                        ocr_data, manual_data,
                        raw_image_path=f"./storage/{user_id}_{record_date}.jpg",
                        ocr_confidence=ocr_conf  # 加上ocr_conf 
                    )

                    with st.spinner("正在將資料即時同步至雲端 Google Sheets..."):
                        success = database.insert_record(clean_df)

                    if success:
                        st.success("資料已成功結構化，並即時同步至雲端 Google Sheets 資料庫！")
                        display_df = pd.DataFrame({
                            "欄位": clean_df.columns.tolist(),
                            "數值": [str(v) for v in clean_df.iloc[0].tolist()]
                        })
                        st.dataframe(display_df, height=600)
                    else:
                        st.error("❌ 資料已成功結構化，但同步到雲端時失敗，請檢查網路或密鑰設定。")

                    csv = clean_df.to_csv(index=False).encode('utf-8-sig')
                    st.download_button("📥 備份：下載本次清洗後 CSV", data=csv, file_name=f"{record_date}_log.csv")

                except ValueError as e:
                    st.error(f"❌ 資料驗證失敗：{e}")