import streamlit as st
import cv2
import pandas as pd
import numpy as np
from datetime import datetime
from processor import DataProcessor
import database
from ocr_module import process_ocr_and_heatmap, calculate_sleep_duration

def render_page():
    st.title("飛靶 OCR 辨識與日常生活紀錄")
    st.caption("💡 提示：上傳成績單後，系統將自動啟動 AI 影像辨識")
    st.markdown("---")

    # 📌 初始化 Session State 狀態控制鎖
    if "ocr_result_cache" not in st.session_state:
        st.session_state["ocr_result_cache"] = None
    if "last_uploaded_file_name" not in st.session_state:
        st.session_state["last_uploaded_file_name"] = None
    if "upload_success" not in st.session_state:
        st.session_state["upload_success"] = False

    # 📌 若已成功上傳並鎖定，顯示成功畫面與「上傳其他成績單」按鈕
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
            st.session_state["ocr_result_cache"] = None
            st.session_state["last_uploaded_file_name"] = None
            st.session_state["upload_success"] = False
            if "last_clean_df" in st.session_state:
                del st.session_state["last_clean_df"]
            st.rerun()
            
        return # 中斷後續渲染，鎖定畫面

    # =============================================================
    #  標準模式：允許填寫與上傳
    # =============================================================
    uploaded_file = st.file_uploader("上傳成績單 (JPG, PNG, PDF)", type=["jpg", "png", "pdf"])

    if uploaded_file and st.session_state["last_uploaded_file_name"] != uploaded_file.name:
        st.session_state["ocr_result_cache"] = None
        st.session_state["last_uploaded_file_name"] = uploaded_file.name

    col_img, col_form = st.columns([4, 6])
    
    # =============================================================
    #  1. 自動觸發 OCR 辨識區
    # =============================================================
    if uploaded_file and st.session_state["ocr_result_cache"] is None:
        file_bytes = uploaded_file.read()
        is_pdf = uploaded_file.type == "application/pdf"
        
        with st.spinner("系統正在讀取成績單，請稍候..."):
            try:
                ocr_res = process_ocr_and_heatmap(file_bytes, is_pdf)
                st.session_state["ocr_result_cache"] = ocr_res
                st.toast("✅ AI 辨識完成！已自動換算等級並填入表單。")
            except Exception as e:
                st.error(f"❌ AI 自動辨識失敗，已載入預設無資料表單。錯誤: {e}")
                st.session_state["ocr_result_cache"] = {
                    "total_shots": 0, "first_hit": 0, "second_hit": 0, "miss": 0,
                    "heatmap_matrix": None
                }
    
    ocr_defaults = st.session_state["ocr_result_cache"]

    # ============================================================
    # 2. 左側區塊：檔案預覽
    # ============================================================
    with col_img:
        st.subheader("📸 成績檔案預覽")
        if uploaded_file:
            if uploaded_file.type == "application/pdf":
                st.info("📂 PDF 檔案已上傳，已完成背景讀取。")
            else:
                st.image(uploaded_file, use_container_width=True)
        else:
            st.info("請在上傳區提供飛靶成績單圖片。")

    # =============================================================
    # 📝 3. 右側區塊：校正表單與日常生活因子填寫
    # =============================================================
    with col_form:
        st.subheader("數據校正與每日作息填寫")
        
        # ── 🌙 選手睡眠時間動態換算區（獨立表單外） ──
        st.markdown("#### 🌙 選手睡眠時間動態換算")
        c_sleep1, c_sleep2 = st.columns(2)
        bedtime = c_sleep1.time_input("請選擇入睡時間：", value=datetime.strptime("23:00", "%H:%M").time())
        wake_up_time = c_sleep2.time_input("請選擇起床時間：", value=datetime.strptime("07:00", "%H:%M").time())

        sleep_duration = calculate_sleep_duration(bedtime, wake_up_time)
        st.info(f"⏳ (系統自動換算) 當日睡眠時長: {sleep_duration} 小時")
        st.markdown("---")

        # ── 📊 射擊表現數據手動輸入與即時計算區（💡 移到表單外以支援即時聯動） ──
        st.markdown