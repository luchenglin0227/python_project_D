import streamlit as st
import cv2
import pandas as pd
import numpy as np
from datetime import datetime
from processor import DataProcessor
import database
from ocr_module import process_ocr_and_heatmap, calculate_sleep_duration

def render_page():
    st.title(" 不定向飛靶成績與日常生活紀錄")
    # 初始化 Session State 狀態控制鎖
    #if "ocr_result_cache" not in st.session_state:
    #   st.session_state["ocr_result_cache"] = None
    if "last_uploaded_file_name" not in st.session_state:
        st.session_state["last_uploaded_file_name"] = None
    if "upload_success" not in st.session_state:
        st.session_state["upload_success"] = False

    # 若已成功上傳並鎖定，顯示成功畫面與「上傳其他成績單」按鈕
    if st.session_state["upload_success"]:
        st.success("🎉 資料已成功結構化，並即時同步至雲端 Google Sheets！")
        
        # 顯示剛剛上傳成功的暫存結果
        if "last_clean_df" in st.session_state:
            display_df = pd.DataFrame({
                "欄位": st.session_state["last_clean_df"].columns.tolist(),
                "數值": [str(v) for v in st.session_state["last_clean_df"].iloc[0].tolist()]
            })
            st.dataframe(display_df, height=300)

        st.markdown("---")
        if st.button("🔄 上傳其他成績單", type="primary"):
            #st.session_state["ocr_result_cache"] = None
            st.session_state["last_uploaded_file_name"] = None
            st.session_state["upload_success"] = False
            if "last_clean_df" in st.session_state:
                del st.session_state["last_clean_df"]
            st.rerun()
            
        return 

    # =============================================================
    #  允許填寫與上傳
    # =============================================================
    uploaded_file = st.file_uploader("上傳成績單 (JPG, PNG, PDF)", type=["jpg", "png", "pdf"])

    if uploaded_file and st.session_state["last_uploaded_file_name"] != uploaded_file.name:
        #st.session_state["ocr_result_cache"] = None
        st.session_state["last_uploaded_file_name"] = uploaded_file.name

    # 建立左右布局
    col_img, col_form = st.columns([4, 6])
    
    # =============================================================
    #  1. 自動觸發 OCR 辨識區(效果不佳，關掉)
    # =============================================================
    #if uploaded_file and st.session_state["ocr_result_cache"] is None:
    #    file_bytes = uploaded_file.read()
    #    is_pdf = uploaded_file.type == "application/pdf"
        
    #    with st.spinner("系統正在讀取成績單，請稍候..."):
    #        try:
    #            ocr_res = process_ocr_and_heatmap(file_bytes, is_pdf)
    #           st.session_state["ocr_result_cache"] = ocr_res
    #            st.toast("✅ AI 辨識完成！已自動換算等級並填入表單。")
    #        except Exception as e:
    #            st.error(f"❌ AI 自動辨識失敗，已載入預設無資料表單。錯誤: {e}")
    #            st.session_state["ocr_result_cache"] = {
    #                "total_shots": 0, "first_hit": 0, "second_hit": 0, "miss": 0,
    #                "heatmap_matrix": None
    #            }
    
    #ocr_defaults = st.session_state["ocr_result_cache"]

    # ============================================================
    # 2. 左側區塊：檔案預覽
    # ============================================================
    with col_img:
        st.subheader("📸 成績檔案預覽")
        if uploaded_file:
            if uploaded_file.type == "application/pdf":
                st.info("📂 PDF 檔案已上傳，請進行核對。")
            else:
                st.image(uploaded_file, use_container_width=True)
        else:
            st.info("請在上傳區提供飛靶成績單圖片。")

    # =============================================================
    # 3. 右側區塊：控制面板
    # =============================================================
    with col_form:
        st.subheader("射擊數據與每日作息填寫")
        
        # ── 第一區塊：基本資訊 ──
        st.markdown("### 📋 1. 基本資訊")
        c1, c2 = st.columns(2)
        user_id = c1.text_input("選手編號：", value="User_01")
        record_date = c2.date_input("射擊日期：", datetime.now())
        
        c3, c4 = st.columns(2)
        match_start_time = c3.time_input("訓練/比賽開始時間：", datetime.now().time())
        shooting_range = c4.selectbox("射擊靶場：", ["A", "B", "C"])
        st.markdown("---")

        # ── 第二區塊：九方位空間分析 ──
        st.markdown("### 🎯 2. 九方位彈著點與命中率空間分析")
        st.caption("提示標籤顏色： :green[良好] (分數>=80) | :orange[尚可] (40~79) | :red[較差] (<40) | 無資料")
        
        status_options = ["無資料", "🔴較差", "🟡尚可", "🟢良好"]
        status_values = {"無資料": -1, "🔴較差": 0, "🟡尚可": 1, "🟢良好": 2}

        # 註解掉由 OCR 結果填入預設值的邏輯，直接全部給 -1
        #default_indices = []
        #for idx in range(9):
        #    if ocr_defaults is None or ocr_defaults.get("heatmap_matrix") is None:
        #        default_indices.append(0)
        #    else:
        #        try:
        #            score = float(ocr_defaults["heatmap_matrix"][idx])
        #            if score == -1:
        #                default_indices.append(0)
        #            elif score >= 80.0:
        #                default_indices.append(3)
        #            elif score >= 40.0:
        #                default_indices.append(2)
        #            else:
        #                default_indices.append(1)
        #        except (IndexError, ValueError, TypeError):
        #            default_indices.append(0)
        default_indices = [0] * 9  # 強制讓九宮格預設為 "無資料"

        h_col1, h_col2, h_col3 = st.columns(3)
        with h_col1:
            v0 = h_col1.selectbox("左上 (High Left)", status_options, index=default_indices[0])
            v3 = h_col1.selectbox("左中 (Mid Left)", status_options, index=default_indices[3])
            v6 = h_col1.selectbox("左下 (Low Left)", status_options, index=default_indices[6])
        with h_col2:
            v1 = h_col2.selectbox("中上 (High Center)", status_options, index=default_indices[1])
            v4 = h_col2.selectbox("正中 (Center)", status_options, index=default_indices[4])
            v7 = h_col2.selectbox("中下 (Low Center)", status_options, index=default_indices[7])
        with h_col3:
            v2 = h_col3.selectbox("右上 (High Right)", status_options, index=default_indices[2])
            v5 = h_col3.selectbox("右中 (Mid Right)", status_options, index=default_indices[5])
            v8 = h_col3.selectbox("右下 (Low Right)", status_options, index=default_indices[8])

        updated_matrix = [
            status_values[v0], status_values[v1], status_values[v2],
            status_values[v3], status_values[v4], status_values[v5],
            status_values[v6], status_values[v7], status_values[v8]
        ]
        st.markdown("---")

        # ── 第三區塊：射擊表現數據 ──
        st.markdown("### 📊 3. 射擊表現數據")
        c5, c7, c8 = st.columns(3)
        total_shots = c5.number_input("總發數：", min_value=0, value=0)
        second_hit = c7.number_input("二發命中數：", min_value=0, value=0)
        miss_count = c8.number_input("失誤數：", min_value=0, value=0)

        # 由上述三個部分即時在背景用減法推算一發命中數
        first_hit = total_shots - second_hit - miss_count
        if first_hit < 0:
            first_hit = 0  # 避免尚未填完前出現負數

        # 計算表現指標
        if total_shots > 0:
            total_hits = first_hit + second_hit
            calc_hit_rate = total_hits / total_shots
            calc_first_hit_rate = first_hit / total_shots
            calc_miss_rate = miss_count / total_shots
        else:
            calc_hit_rate, calc_first_hit_rate, calc_miss_rate = 0.0, 0.0, 0.0

        # 即時數據大看板
        rate_col1, rate_col2, rate_col3, rate_col4 = st.columns(4)
        rate_col1.metric("💡 推算一發命中數", f"{first_hit} 發")
        rate_col2.metric("🎯 總命中率", f"{calc_hit_rate:.1%}")
        rate_col3.metric("⚡ 一發命中率", f"{calc_first_hit_rate:.1%}")
        rate_col4.metric("❌ 失誤率", f"{calc_miss_rate:.1%}")
        st.markdown("---")

        # ── 第四區塊：睡眠時間 + 日常生活因子紀錄 ──
        st.markdown("### 🌙 4. 睡眠時間與日常生活因子紀錄")
        st.caption("🔒 睡眠時數動態聯動區：調整時間下方時數將即時更新")
        c_sleep1, c_sleep2 = st.columns(2)
        bedtime = c_sleep1.time_input("請選擇入睡時間：", value=datetime.strptime("23:00", "%H:%M").time())
        wake_up_time = c_sleep2.time_input("請選擇起床時間：", value=datetime.strptime("07:00", "%H:%M").time())

        sleep_duration = calculate_sleep_duration(bedtime, wake_up_time)
        st.info(f"⏳ (系統自動換算) 當日睡眠時長: {sleep_duration} 小時")
        st.markdown("")

        # 日常生活因子其餘欄位大表單
        with st.form("shooting_form_final"):
            c11, c12 = st.columns(2)
            arrival_time = c11.time_input("到場時間：",  value=datetime.strptime("08:30", "%H:%M").time())
            warm_up_time = c12.number_input("熱身時長 (min)", min_value=0, value=20)

            c13, c14, c15 = st.columns(3)
            breakfast_calories = c13.number_input("早餐總熱量 (kcal)：", min_value=0, value=450)
            breakfast_protein = c14.number_input("早餐蛋白質攝取量 (g)", min_value=0.0, value=25.0)
            caffeine_intake = c15.number_input("咖啡因攝取 (mg)", min_value=0.0, value=100.0)
            
            c16, c17 = st.columns(2)
            fatigue_level = c16.select_slider("疲勞程度", options=[1, 2, 3, 4, 5], value=1)
            tension_level = c17.select_slider("緊張程度", options=[1, 2, 3, 4, 5], value=1)

            st.markdown("---")
            confirm_lock = st.checkbox("🚨 我已確認以上 1 ~ 4 區的所有輸入數據皆正確無誤", value=False)
            submit_btn = st.form_submit_button("💾 結構化並上傳雲端資料庫")

        # =============================================================
        #  4. 後端資料儲存與串接
        # =============================================================
        if submit_btn:
            if not confirm_lock:
                st.error("🛑 上傳失敗：請先勾選下方的「我已確認以上 1 ~ 4 區的所有輸入數據皆正確無誤」核取方塊！")
            else:
                # 📌 修正點：將鍵值改為與 processor.py 完全對齊的中文字眼
                final_shooting_data = {
                    "總發數": total_shots,
                    "一發命中數": first_hit,
                    "二發命中數": second_hit,
                    "失誤數": miss_count,
                    "heatmap_matrix": updated_matrix
                }
                manual_life_data = {
                    "使用者編號": user_id, "射擊日期": record_date, "比賽時間": match_start_time, "靶場": shooting_range,
                    "入睡時間": bedtime, "起床時間": wake_up_time, "到場時間": arrival_time, "熱身時長": warm_up_time,
                    "早餐熱量": breakfast_calories, "蛋白質": breakfast_protein, "咖啡因攝取": caffeine_intake,
                    "疲勞程度": fatigue_level, "緊張程度": tension_level, "睡眠時長": sleep_duration
                }

                try:
                    processor = DataProcessor()
                    clean_df = processor.process_record(
                        final_shooting_data, manual_life_data,
                        raw_image_path=f"./storage/{user_id}_{record_date}.jpg"
                    )

                    with st.spinner("正在將資料即時同步至雲端 Google Sheets..."):
                        success = database.insert_record(clean_df)

                    if success:
                        st.session_state["upload_success"] = True
                        st.session_state["last_clean_df"] = clean_df
                        st.rerun()
                    else:
                        st.error("❌ 同步到雲端時失敗，請檢查金鑰設定。")
                except Exception as e:
                    st.error(f"❌ 資料清洗與數據換算處理發生錯誤: {e}")