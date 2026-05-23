# src_ui/analysis_page.py
import streamlit as st
import database

def render_page():
    st.title("📊 選手歷史歷程與數據分析看板")
    
    # 🔒 簡易密碼鎖
    admin_password = st.text_input("🔒 查看數據分析請輸入後台管理密碼：", type="password")
    
    if admin_password == "Shooting":
        st.success("🔓 密碼正確！已成功載入管理後台。")
        st.markdown("---")
        
        # 建立一個刷新按鈕
        if st.button("🔄 重新整理雲端資料"):
            database.get_all_records.clear()
            st.rerun()
            
        try:
            with st.spinner("正在讀取雲端最新歷史紀錄..."):
                history_df = database.get_all_records()
                
            if history_df is not None and not history_df.empty:
                st.metric(label="📊 目前已累積總筆數", value=f"{len(history_df)} 筆")
                
                # 💡 之後可以直接在這邊底下畫折線圖/搜尋功能
                st.dataframe(history_df, use_container_width=True, height=400)
import pandas as pd
            else:
                st.warning("📭 雲端目前沒有任何紀錄。")
        except Exception as e:
            st.error(f"❌ 無法讀取歷史紀錄：{e}")
            
    elif admin_password == "":
        st.warning("🔑 請輸入密碼以解鎖選手歷程數據。")
    else:
        st.error("❌ 密碼錯誤！您沒有存取歷史數據的權限。")
