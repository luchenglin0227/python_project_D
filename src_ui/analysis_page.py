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
                st.markdown(f"### 目前已累積總筆數： :green[{total_count} 筆]")
                
                if total_count > 0:
                    # 建立反向對映表
                    reverse_map = {v: k for k, v in SHOOTING_FIELD_MAP.items()}
                    
                    # 將 DataFrame 的欄位全部轉成中文名
                    display_df = raw_df.rename(columns=reverse_map)

                    # 補齊 index 作為辨識不重複紀錄的依據
                    display_df['系統內部序號'] = display_df.index
                    
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
                
                # 分層查詢區
                    st.subheader("訓練記錄查詢")
                    
                    # 設立橫向三個欄位
                    filter_col1, filter_col2, filter_col3 = st.columns(3)
                    
                    # 第一層：選擇使用者
                    with filter_col1:
                        all_users = sorted(display_df[user_col_zh].dropna().unique().tolist())
                        selected_user = st.selectbox("選擇選手：", all_users)
                    
                    # 根據選定的使用者，過濾出該選手的資料
                    user_filtered_df = display_df[display_df[user_col_zh] == selected_user]
                    
                    # 第二層：選擇訓練日期
                    with filter_col2:
                        all_dates = sorted(user_filtered_df[date_col_zh].dropna().unique().tolist(), reverse=True)
                        selected_date = st.selectbox("選擇訓練日期：", all_dates)
                        
                    # 根據選定的使用者 + 射擊日期，進一步過濾
                    date_filtered_df = user_filtered_df[user_filtered_df[date_col_zh] == selected_date]
                    
                    # 第三層：選擇精確紀錄時間（避免同一天有多筆紀錄）】
                    with filter_col3:
                        time_options = []
                        # 建立時間選單顯示字串，並把「系統內部序號」藏在裡面以便精確對應
                        for _, row in date_filtered_df.iterrows():
                            c_val = row.get(created_col_zh, "未知時間")
                            idx_val = row['系統內部序號']
                            time_options.append(f"紀錄時間：{c_val} (序號: {idx_val})")
                            
                        selected_time_str = st.selectbox("選擇紀錄時間：", time_options)
                    
                    # 找出最終被選中的那一筆資料
                    selected_idx = int(selected_time_str.split("(序號: ")[1].replace(")", ""))
                    selected_row = display_df[display_df['系統內部序號'] == selected_idx].iloc[0]
                
                    #展開詳細資料
                    st.markdown("---")
                    st.subheader(f"🔍 詳細數據展開：選手 {selected_user} 在 {selected_date} 的訓練紀錄")
                    
                    #用雙欄呈現
                    with st.container(border=True):
                        col1, col2 = st.columns(2)
                        
                        # 轉換為清單，過濾掉不需要顯示的內部序號
                        items = [(k, v) for k, v in selected_row.items() if k != '系統內部序號']
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