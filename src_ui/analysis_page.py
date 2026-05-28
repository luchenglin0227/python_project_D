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
            database.load_records.clear()  
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
                    
                    # 數據轉換準備區（將 0,1,2 轉回中文供表格與文字顯示）
                    heatmap_eng_cols = [
                        'miss_left_high', 'miss_middle_high', 'miss_right_high',
                        'miss_left_mid',  'miss_middle_mid',  'miss_right_mid',
                        'miss_left_low',  'miss_middle_low',  'miss_right_low'
                    ]
                    
                    # 建立數字轉中文的反向映射
                    num_to_zh_map = {2: "良好", 1: "尚可", 0: "較差", "2": "良好", "1": "尚可", "0": "較差"}
                    
                    # 複製一份專門用來文字與篩選展示的 DataFrame (不影響原始數字 raw_df)
                    transformed_df = raw_df.copy()
                    for col in heatmap_eng_cols:
                        if col in transformed_df.columns:
                            transformed_df[col] = transformed_df[col].map(num_to_zh_map).fillna(transformed_df[col])

                    # 將 DataFrame 的欄位全部轉成中文名
                    display_df = transformed_df.rename(columns=reverse_map)

                    # 補齊 index 作為辨識不重複紀錄的依據
                    display_df['系統內部序號'] = display_df.index
                    
                    # 取得核心欄位的中文名稱
                    user_col_zh = reverse_map.get(SHOOTING_FIELD_MAP.get("使用者編號", "user_id"), "使用者編號")
                    date_col_zh = reverse_map.get(SHOOTING_FIELD_MAP.get("射擊日期", "record_date"), "射擊日期")
                    created_col_zh = "系統紀錄時間"
                
                    # 處理射擊日期格式
                    if date_col_zh in display_df.columns:
                        display_df[date_col_zh] = pd.to_datetime(display_df[date_col_zh], errors='coerce').dt.strftime('%Y-%m-%d')
                    
                    # 處理系統紀錄時間的格式
                    if created_col_zh in display_df.columns:
                        display_df[created_col_zh] = pd.to_datetime(display_df[created_col_zh], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')
                    
                    # 定義資料庫 user_id 欄位名稱 (給後面分析跟刪除使用)
                    if 'user_id' in raw_df.columns:
                        actual_user_col = 'user_id'
                    elif '使用者編號' in raw_df.columns:
                        actual_user_col = '使用者編號'
                    else:
                        actual_user_col = user_col_zh
                    
                    # 先行篩選區：先選擇選手
                    st.header("🎯 選擇分析對象")
                    all_users = sorted(display_df[user_col_zh].dropna().unique().tolist())
                    selected_user = st.selectbox("請先選取選手：", all_users)
                    user_filtered_display_df = display_df[display_df[user_col_zh] == selected_user]

                    # 使用 Tabs 將資料庫管理與圖表分析切開
                    tab_db, tab_ana = st.tabs(["🗄️ 歷史資料庫與管理", "📈 選手數據分析看板"])
                    
                    # ==========================================
                    #  分頁 1：歷史資料庫管理與刪除
                    # ==========================================
                    with tab_db:
                        st.subheader(f"📂 {selected_user} 的個人完整歷史資料庫")
                        st.dataframe(user_filtered_display_df.drop(columns=['系統內部序號'], errors='ignore'), use_container_width=True)
                        
                        st.markdown("---")
                        st.subheader("🔍 查看單筆詳細數據")

                    # 設立兩個篩選欄位
                    filter_col2, filter_col3 = st.columns(2)
                    with filter_col2:
                        all_dates = sorted(user_filtered_display_df[date_col_zh].dropna().unique().tolist(), reverse=True)
                        selected_date = st.selectbox("選擇要檢視的訓練日期：", all_dates) if all_dates else None
                    
                    if selected_date:
                            date_filtered_df = user_filtered_display_df[user_filtered_display_df[date_col_zh] == selected_date]
                            with filter_col3:
                                time_options = []
                                for _, row in date_filtered_df.iterrows():
                                    c_val = row.get(created_col_zh, "未知時間")
                                    idx_val = row['系統內部序號']
                                    time_options.append(f"紀錄時間：{c_val} (序號: {idx_val})")
                                selected_time_str = st.selectbox("選擇紀錄時間：", time_options)
                            
                            selected_idx = int(selected_time_str.split("(序號: ")[1].replace(")", ""))
                            selected_row = display_df[display_df['系統內部序號'] == selected_idx].iloc[0]
                            
                            with st.container(border=True):
                                col_d1, col_d2 = st.columns(2)
                                items = [(k, v) for k, v in selected_row.items() if k != '系統內部序號']
                                mid = (len(items) + 1) // 2
                                with col_d1:
                                    for key, val in items[:mid]:
                                        if str(key).lower() in ['index', 'id']: continue
                                        st.write(f"**📌 {key}** : `{val}`")
                                with col_d2:
                                    for key, val in items[mid:]:
                                        if str(key).lower() in ['index', 'id']: continue
                                        st.write(f"**📌 {key}** : `{val}`")
                           
                            # 新增刪除功能與警告按鈕
                            st.markdown("<br>", unsafe_allow_html=True)
                            if st.button("🗑️ 刪除此筆紀錄"):
                                st.session_state.delete_confirm_idx = selected_idx
                                
                            if st.session_state.get("delete_confirm_idx") == selected_idx:
                                st.warning("⚠️ 警告：此動作無法復原，確定要刪除這筆資料嗎？")
                                c_yes, c_no = st.columns(2)
                                if c_yes.button("✅ 確定刪除", type="primary"):
                                    # 精確抓取要刪除的 user_id 與 timestamp
                                    target_row = raw_df.iloc[selected_idx]
                                    t_user = target_row[actual_user_col]
                                    t_created = target_row['created_at']
                                    
                                    with st.spinner("正在從雲端移除資料，請稍候..."):
                                        success = database.delete_record(t_user, t_created)
                                        if success:
                                            st.success("🗑️ 刪除成功！")
                                            st.session_state.delete_confirm_idx = None
                                            database.load_records.clear() # 清除快取以抓取最新狀態
                                            st.rerun()
                                        else:
                                            st.error("❌ 刪除失敗，請檢查網路連線或金鑰。")
                                            
                                if c_no.button("❌ 點此取消"):
                                    st.session_state.delete_confirm_idx = None
                                    st.rerun()
                    # =============================================================
                    # 分頁 2：視覺化數據分析看板
                    # =============================================================
                    with tab_ana:
                        st.subheader(f"📈 選手 {selected_user} 表現分析看板")
                        
                        user_raw_df = raw_df[raw_df[actual_user_col] == selected_user].copy()
                        user_raw_df = user_raw_df.rename(columns=SHOOTING_FIELD_MAP)
                        
                        hit_rate_col = None
                        for col in ['hit_rate', '總命中率']:
                            if col in user_raw_df.columns:
                                hit_rate_col = col
                                break
                        if not hit_rate_col:
                            for col in user_raw_df.columns:
                                if "命中率" in str(col) or "rate" in str(col).lower():
                                    hit_rate_col = col
                                    break
                                
                        if hit_rate_col in user_raw_df.columns and not user_raw_df.empty:
                            try:
                                valid_rates = pd.to_numeric(user_raw_df[hit_rate_col], errors='coerce').dropna()
                                avg_hit_rate = valid_rates.mean()
                                
                                if avg_hit_rate > 1.0:
                                    avg_hit_rate = avg_hit_rate / 100.0
                                avg_miss_rate = 1.0 - avg_hit_rate

                                dkpi1, dkpi2 = st.columns(2)
                                dkpi1.metric("個人平均 Hit Rate (總命中率)", f"{avg_hit_rate:.2%}")
                                dkpi2.metric("個人平均 Miss Rate (失誤率)", f"{avg_miss_rate:.2%}")

                                st.markdown("##### 📌 個人歷史表現趨勢 (Performance Trend)")
                                date_col = None
                                for eng, zh in SHOOTING_FIELD_MAP.items():
                                    if "日期" in eng or "date" in zh:
                                        date_col = zh
                                        break
                                
                                if date_col in user_raw_df.columns:
                                    user_raw_df["parsed_date"] = pd.to_datetime(user_raw_df[date_col]).dt.date
                                    user_raw_df[hit_rate_col] = pd.to_numeric(user_raw_df[hit_rate_col], errors='coerce')
                                    if user_raw_df[hit_rate_col].mean() > 1.0:
                                        user_raw_df[hit_rate_col] = user_raw_df[hit_rate_col] / 100.0
                                        
                                    trend_data = user_raw_df.groupby("parsed_date")[hit_rate_col].mean()
                                    st.line_chart(trend_data)
                            except Exception:
                                st.info("💡 趨勢圖表正在等待更多標準格式數據累積中...")
                        else:
                            st.info("💡 該選手目前尚無足夠的命中率數據生成歷史趨勢圖。")
                        
                        st.markdown("---")
                        st.subheader("進階交叉分析 (生活作息 vs 射擊表現)")
                            
                        ana_col1, ana_col2 = st.columns(2)
                        with ana_col1:
                            st.write("**🌙 睡眠時長 vs 平均命中率 (%)**")
                            if 'sleep_duration' in user_raw_df.columns and 'hit_rate' in user_raw_df.columns:
                                user_raw_df['sleep_duration'] = pd.to_numeric(user_raw_df['sleep_duration'], errors='coerce')
                                user_raw_df['sleep_group'] = user_raw_df['sleep_duration'].round()
                                        
                                hit_data = pd.to_numeric(user_raw_df['hit_rate'], errors='coerce')
                                if hit_data.mean() <= 1.0:
                                    hit_data = hit_data * 100
                                user_raw_df['hit_rate_pct'] = hit_data
                                        
                                sleep_trend = user_raw_df.groupby('sleep_group')['hit_rate_pct'].mean()
                                st.line_chart(sleep_trend)
                            else:
                                st.info("💡 累積更多睡眠數據後將自動顯示圖表。")
        
                        with ana_col2:
                            st.write("**⚡ 賽前緊張程度 vs 平均失誤率 (%)**")
                            if 'tension_level' in user_raw_df.columns and 'miss_rate' in user_raw_df.columns:
                                user_raw_df['tension_level'] = pd.to_numeric(user_raw_df['tension_level'], errors='coerce')
                                
                                miss_data = pd.to_numeric(user_raw_df['miss_rate'], errors='coerce')
                                if miss_data.mean() <= 1.0:
                                    miss_data = miss_data * 100
                                user_raw_df['miss_rate_pct'] = miss_data
                                
                                tension_trend = user_raw_df.groupby('tension_level')['miss_rate_pct'].mean()
                                st.bar_chart(tension_trend)
                            else:
                                st.info("💡 累積更多緊張程度數據後將自動顯示圖表。")
                else:
                    st.warning("📭 雲端目前沒有任何紀錄。")
                
        except Exception as e:
            st.error(f"❌ 無法讀取歷史紀錄：{e}")
            
    elif admin_password == "":
        st.warning("🔑 請輸入密碼以解鎖選手歷程數據。")
    else:
        st.error("❌ 密碼錯誤！您沒有存取歷史數據的權限。")