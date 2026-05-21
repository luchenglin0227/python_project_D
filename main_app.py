# app.py (主程式入口)
import streamlit as st

#  從 src_ui 引入兩個分頁設計
from src_ui import upload_page, analysis_page

# 基本設定 
st.set_page_config(
    page_title="不定向飛靶分析網站",
    page_icon="🥏",
    layout="wide"
)

# 側邊欄導航 (Sidebar)
st.sidebar.title("🎯 系統選單")
page = st.sidebar.radio("請選擇功能分頁：", ["📄 飛靶辨識與上傳", "📊 歷程數據與分析"])


if page == "📄 飛靶辨識與上傳":
    upload_page.render_page()

elif page == "📊 歷程數據與分析":
    analysis_page.render_page()