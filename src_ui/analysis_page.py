# src_ui/analysis_page.py
import streamlit as st
import pandas as pd
import database
from processor import SHOOTING_FIELD_MAP

def render_page():
    st.title("📊 選手歷史歷程與數據分析看板")
    
    # 製作簡易密碼鎖
    admin_password = st.text_input("🔒 查看數據分析請輸入後台管理密碼：", type="password")
    
    if admin_password == "Shooting":
        st.success("🔓 密碼正確！已成功載入管理後台。")
        st.markdown("---")
        
        # 建立一個刷新按鈕
        if st.button("🔄 重新整理雲端資料"):
            database.load_records.clear()  # 清除 database.py 中的快取
            st.rerun()
            
        try:
            with st.spinner("正在讀取雲端最新歷史紀錄..."):
                # 從 database.py 撈取原始 DataFrame
                raw_df = database.load_records()
                
            if raw_df is not None:
                total_count = len(raw_df) if not raw_df.empty else 0
                st.markdown(f"### 📊 目前已累積總筆數： :green[{total_count} 筆]")
                
                # 建立反向對映表（從英文變數名稱轉回中文）
                reverse_map = {v: k for k, v in SHOOTING_FIELD_MAP.items()}
                
                # 將 DataFrame 的欄位全部轉成中文名
                display_df = raw_df.rename(columns=reverse_map)
                
                # 取得核心欄位的中文名稱
                user_col_zh = reverse_map.get(SHOOTING_FIELD_MAP.get("使用者編號", "user_id"), "使用者編號")
                date_col_zh = reverse_map.get(SHOOTING_FIELD_MAP.get("射擊日期", "record_date"), "射擊日期")
                created_col_zh = "系統紀錄時間"
                
                # 射擊日期
                if date_col_zh in display_df.columns:
                    display_df[date_col_zh] = pd.to_datetime(display_df[date_col_zh]).dt.strftime('%Y-%m-%d')
                
                # 處理系統紀錄時間的格式
                if created_col_zh in display_df.columns:
                    display_df[created_col_zh] = pd.to_datetime(display_df[created_col_zh]).dt.strftime('%Y-%m-%d %H:%M:%S')
                
                #精簡主畫面，呈現選手、射擊日期與紀錄日期
                st.subheader("📋 歷程總覽清單")
                
                # 建立主下拉選單的選項字串
                record_options = []
                for idx, row in display_df.iterrows():
                    u_val = row.get(user_col_zh, f"未知選手({idx})")
                    d_val = row.get(date_col_zh, "未知日期")
                    c_val = row.get(created_col_zh, "未知時間")
                    # 項目加粗呈現
                    record_options.append(f"**選手**: {u_val} | **射擊日期**: {d_val} | **紀錄時間**: {c_val} (編號: {idx})")
                
                selected_option = st.selectbox("💡 請在下方下拉選單中選取特定紀錄，即可查看完整詳細數據數據：", record_options)
                
                # 找出被選中的那一筆的 index
                selected_idx = int(selected_option.split("(編號: ")[1].replace(")", ""))
                selected_row = display_df.loc[selected_idx]
                
                # 展開詳細資料
                st.markdown("---")
                display_title = selected_option.split(" (編號:")[0]
                st.subheader(f"詳細數據展開：")
                
                with st.container(border=True):
                    col1, col2 = st.columns(2)
                    
                    items = list(selected_row.items())
                    mid = (len(items) + 1) // 2
                    
                    with col1:
                        for key, val in items[:mid]:
                            if str(key).lower() in ['index', 'id']: continue
                            st.write(f"**📌 {key}** : `{val}`")
                            
                    with col2:
                        for key, val in items[mid:]:
                            if str(key).lower() in ['index', 'id']: continue
                            st.write(f"**📌 {key}** : `{val}`")
                            
            else:
                st.warning("📭 雲端目前沒有任何紀錄。")
                
        except Exception as e:
            st.error(f"❌ 無法讀取歷史紀錄：{e}")
            
    elif admin_password == "":
        st.warning("🔑 請輸入密碼以解鎖選手歷程數據。")
    else:
        st.error("❌ 密碼錯誤！您沒有存取歷史數據的權限。")