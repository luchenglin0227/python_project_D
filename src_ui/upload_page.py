import streamlit as st
import cv2
import pandas as pd
from datetime import datetime
from processor import DataProcessor
import database
from ocr_module import process_ocr_and_heatmap, calculate_sleep_duration


def render_page():
    st.title("飛靶 OCR 辨識與日常生活紀錄")
    st.caption("💡提醒：您可以同時進行 AI 影像辨識與填寫生活因子")
    st.markdown("---")

    uploaded_file = st.file_uploader("上傳成績單 (JPG, PNG, PDF)", type=["jpg", "png", "pdf"])

    if uploaded_file:
        file_bytes = uploaded_file.read()
        is_pdf = uploaded_file.type == "application/pdf"

        if "ocr_result_cache" not in st.session_state:
            st.session_state["ocr_result_cache"] = None

        col_img, col_form = st.columns([4, 6])

        # =============================================================
        # 左側區塊：檔案預覽與 AI 辨識獨立觸發區
        # =============================================================
        with col_img:
            st.subheader("成績檔案預覽")
            
            if st.session_state["ocr_result_cache"] is None:
                if is_pdf:
                    from ocr_module import convert_pdf_to_img
                    preview_img = convert_pdf_to_img(file_bytes)
                    st.image(preview_img, caption="PDF 檔案首頁預覽", use_container_width=True)
                else:
                    st.image(file_bytes, caption="已上傳的成績單圖片", use_container_width=True)
                    st.markdown("---")
                
            else:
                cached_img = st.session_state["ocr_result_cache"]["img"]
                st.image(cv2.cvtColor(cached_img, cv2.COLOR_BGR2RGB), caption="AI 光譜軌跡分析圖", use_container_width=True)

            st.markdown("---")
            # 將 AI 辨識做成獨立按鈕，點擊後觸發
            if st.button("開始執行 OCR 辨識", use_container_width=True):
                with st.spinner("正在執行辨識與光譜映射分析，請同時填寫右側日常因子..."):
                    try:
                        # 【關鍵修正】在執行前，強制清除 process_ocr_and_heatmap 的快取
                        # 這樣可以確保每次按下按鈕，OpenCV 都會重新切九宮格、重新計算顏色權重
                        process_ocr_and_heatmap.clear()
                        
                        img, full_text, heat_scores = process_ocr_and_heatmap(file_bytes, is_pdf)
                        
                        # 將 AI 吐出的所有數據寫入會話狀態快取
                        st.session_state["ocr_result_cache"] = {
                            "img": img,
                            "full_text": full_text,
                            "heat_scores": heat_scores
                        }
                        st.success("🎉 AI 影像辨識與光譜矩陣換算成功！")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ 辨識過程中發生錯誤：{e}")

        # =============================================================
        # 右側區塊：資料錄入面板
        # =============================================================
        with col_form:
            st.subheader("資料錄入面板")

            # 1. 基本資訊
            with st.expander("🆔 基本資訊", expanded=True):
                c1, c2 = st.columns(2)
                user_id = c1.text_input("使用者編號", value="USER_001")
                record_date = c2.date_input("射擊日期", value=datetime(2026, 5, 2))
                match_start_time = st.time_input("比賽時間", value=datetime.strptime("09:00", "%H:%M").time())
                shooting_range = st.selectbox("靶場", ["A", "B", "C"])

            # 2. 生活因子
            with st.expander("🧘 生活因子與生理狀態", expanded=True):
                c3, c4 = st.columns(2)
                bedtime = c3.time_input("入睡時間", value=datetime.strptime("23:00", "%H:%M").time())
                wake_up_time = c4.time_input("起床時間", value=datetime.strptime("07:00", "%H:%M").time())

                sleep_duration = calculate_sleep_duration(bedtime, wake_up_time)
                st.info(f"(系統自動換算)睡眠時長: {sleep_duration} 小時")
               
                c5, c6, c7 = st.columns(3)
                arrival_time = c5.time_input("到場時間", value=datetime.strptime("08:30", "%H:%M").time())
                warm_up_time = c6.number_input("熱身時長 (min)", value=20.0)
                caffeine_intake = c7.number_input("咖啡因攝取 (mg)", value=100.0)

                c8, c9 = st.columns(2)
                breakfast_calories = c8.number_input("早餐熱量 (kcal)", value=450.0)
                breakfast_protein = c9.number_input("早餐蛋白質攝取量 (g)", value=25.0)

                fatigue_level = st.select_slider("疲勞程度", options=[1, 2, 3, 4, 5], value=2)
                tension_level = st.select_slider("緊張程度", options=[1, 2, 3, 4, 5], value=1)

            # -------------------------------------------------------------
            # 核心數據串接
            # -------------------------------------------------------------
            has_cache = st.session_state["ocr_result_cache"] is not None
            current_heat_scores = st.session_state["ocr_result_cache"]["heat_scores"] if has_cache else [100.0]*9

            # 3. 射擊表現
            with st.expander("📊 射擊表現數據 (OCR 自動帶入)"):
                c10, c11, c12 = st.columns(3)
                total_shots = c10.number_input("總發數", value=125)
                total_hits = c11.number_input("總命中數", value=100)
                hit_rate = c12.number_input("總命中率(0-1)", value=0.80, format="%.3f")

                c13, c14, c15 = st.columns(3)
                first_hit_count = c13.number_input("一發命中數 ", value=100)
                second_hit_count = c14.number_input("二發命中數", value=10)
                miss_count = c15.number_input("失誤數", value=15)

           # 4. 空間分析矩陣
            with st.expander("🔥 空間分析矩陣 (方位命中率 %)", expanded=True):
                if has_cache:
                    st.success("✅ 已成功帶入 AI 換算數據！")
                else:
                    st.info("💡 提示：點擊左側辨識按鈕後，此處九宮格將會自動代入分析結果。")
                    
                grid_cols = st.columns(3)
                
                matrix_configs = [
                    ("左側高位命中率", "miss_left_high"), 
                    ("中間高位命中率", "miss_middle_high"), 
                    ("右側高位命中率", "miss_right_high"),
                    ("左側中位命中率", "miss_left_mid"),  
                    ("正中間命中率", "miss_middle_mid"),  
                    ("右側中位命中率", "miss_right_mid"),
                    ("左側低位命中率", "miss_left_low"),  
                    ("中間低位命中率", "miss_middle_low"),  
                    ("右側低位命中率", "miss_right_low")
                ]

                matrix_values = {}
                for i, (label_zh, name_en) in enumerate(matrix_configs):
                    matrix_values[name_en] = grid_cols[i % 3].number_input(
                        label_zh, min_value=0.0, max_value=100.0,
                        value=float(current_heat_scores[i]), step=0.1
                    )

            # =============================================================
            # 儲存確認與同步雲端
            # =============================================================
            if st.button("💾 確認存檔", use_container_width=True):
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
                    clean_df = processor.process_record(
                        ocr_data, manual_data,
                        raw_image_path=f"./storage/{user_id}_{record_date}.jpg"
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
                        
                        st.session_state["ocr_result_cache"] = None
                    else:
                        st.error("❌ 資料已成功結構化，但同步到雲端時失敗，請檢查網路或密鑰設定。")

                    csv = clean_df.to_csv(index=False).encode('utf-8-sig')
                    st.download_button("📥 備份：下載本次清洗後 CSV", data=csv, file_name=f"{record_date}_log.csv")

                except ValueError as e:
                    st.error(f"❌ 資料驗證失敗：{e}")