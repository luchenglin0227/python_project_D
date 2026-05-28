import streamlit as st
import pandas as pd
import numpy as np
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
                    
                    # =========================================================
                    # 選手確認區塊：必須點擊按鈕，才會顯示下方的兩個分頁
                    # =========================================================
                    st.header("🎯 選擇分析對象")
                    all_users = sorted(display_df[user_col_zh].dropna().unique().tolist())
                    selected_user = st.selectbox("請先選取選手：", all_users)
                    
                    # 選手確認按鈕
                    if st.button("✅ 確認載入此選手資料", type="primary"):
                        st.session_state["confirmed_user"] = selected_user

                    # 只有在「已經確認過」的狀態下，才會把兩個 Tabs 放出來
                    if "confirmed_user" in st.session_state and st.session_state["confirmed_user"] in all_users:
                        active_user = st.session_state["confirmed_user"]
                        
                        # 貼心提示：如果使用者在下拉選單換了人，但還沒按確認鈕
                        if active_user != selected_user:
                            st.info(f"💡 目前下方顯示的是 **{active_user}** 的資料。若要查看 **{selected_user}** 的資料，請點擊上方「確認載入」按鈕。")
                            
                        user_filtered_display_df = display_df[display_df[user_col_zh] == active_user]

                        # 使用 Tabs 將資料庫管理與圖表分析切開
                        tab_db, tab_ana = st.tabs(["🗄️ 歷史資料庫與管理", "📈 選手數據分析看板"])
                        
                        # ==========================================
                        #  分頁 1：歷史資料庫管理與刪除
                        # ==========================================
                        with tab_db:
                            st.subheader(f"📂 {active_user} 的個人完整歷史資料庫")
                            st.dataframe(user_filtered_display_df.drop(columns=['系統內部序號'], errors='ignore'), use_container_width=True)
                            
                            st.markdown("---")
                            st.subheader("🔍 查看與管理單筆詳細數據")

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
                                
                                # 刪除功能與警告按鈕
                                st.markdown("<br>", unsafe_allow_html=True)
                                if st.button("🗑️ 刪除此筆紀錄"):
                                    st.session_state.delete_confirm_idx = selected_idx
                                    
                                if st.session_state.get("delete_confirm_idx") == selected_idx:
                                    st.warning("⚠️ 警告：此動作無法復原，確定要刪除這筆資料嗎？")
                                    c_yes, c_no = st.columns(2)
                                    if c_yes.button("✅ 確定刪除", type="primary"):
                                        
                                        # 將 iloc 換成 loc，使用絕對標籤定位，精準刪除
                                        target_row = raw_df.loc[selected_idx] 
                                        t_user = str(target_row[actual_user_col])
                                        t_created = str(target_row['created_at'])
                                        
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
                            st.subheader(f"📈 選手 {active_user} 表現分析看板")
                            
                            user_raw_df = raw_df[raw_df[actual_user_col] == active_user].copy()
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

                            # =========================================================
                            # 📌 亮點修改：九宮格空間表現熱區 (結合當次失誤率加權)
                            # =========================================================
                            st.markdown("---")
                            st.subheader("🎯 九宮格失誤熱區 (失誤權重佔比 %)")
                            st.caption("數值代表各方位佔整體失誤的百分比，九宮格總和為 100%。\n\n*(💡 此佔比已根據「每次練習的實際失誤率」進行加權計算，失誤越嚴重的場次，其該方位的失誤權重越高)*")
                            
                            grid_mapping = [
                                ['miss_left_high', 'miss_middle_high', 'miss_right_high'],
                                ['miss_left_mid',  'miss_middle_mid',  'miss_right_mid'],
                                ['miss_left_low',  'miss_middle_low',  'miss_right_low']
                            ]
                            
                            zone_intensities = np.zeros((3, 3))
                            total_miss_intensity = 0
                            has_valid_data = False
                            
                            # 確保有失誤率欄位可供加權計算
                            if 'miss_rate' in user_raw_df.columns:
                                user_raw_df['miss_rate_calc'] = pd.to_numeric(user_raw_df['miss_rate'], errors='coerce').fillna(0)
                                # 如果 miss_rate 大於 1.0，代表它是用 0-100 的格式儲存，需換算回 0-1 的小數以便當權重
                                if user_raw_df['miss_rate_calc'].max() > 1.0:
                                    user_raw_df['miss_rate_calc'] = user_raw_df['miss_rate_calc'] / 100.0
                            else:
                                user_raw_df['miss_rate_calc'] = 0.0
                            
                            for i in range(3):
                                for j in range(3):
                                    col = grid_mapping[i][j]
                                    if col in user_raw_df.columns:
                                        vals = pd.to_numeric(user_raw_df[col], errors='coerce')
                                        valid_mask = vals >= 0 # 排除 -1 (無資料)
                                        
                                        if valid_mask.any():
                                            has_valid_data = True
                                            
                                            # 1. 非線性權重：較差(0)->3點, 尚可(1)->1點, 良好(2)->0點
                                            # 使用 np.where 來做條件轉換：如果值是 0 給 3，是 1 給 1，其他(2) 給 0
                                            base_weights = np.where(vals[valid_mask] == 0, 3, np.where(vals[valid_mask] == 1, 1, 0))

                                            # 2. 乘上「實際失誤發數 (miss_count)」代替失誤率，讓大樣本場次更有代表性
                                            session_miss_counts = pd.to_numeric(user_raw_df.loc[valid_mask, 'miss_count'], errors='coerce').fillna(0)

                                            #3. 如果該場 0 失誤，但教練仍評了「較差/尚可」，給予保底權重 0.5 避免瑕疵紀錄被歸零
                                            session_miss_counts = np.maximum(session_miss_counts, 0.5)

                                            # 加權公式：非線性點數 * (實際失誤數或保底值)
                                            weighted_intensity = (base_weights * session_miss_counts).sum()
                                            
                                            zone_intensities[i, j] = weighted_intensity
                                            total_miss_intensity += weighted_intensity
                                            
                            if not has_valid_data or total_miss_intensity == 0:
                                st.info("💡 該選手目前尚無足夠的九宮格空間數據，或所有場次皆無失誤。")
                            else:
                                # 計算佔比
                                grid_scores = (zone_intensities / total_miss_intensity) * 100.0
                                
                                df_grid = pd.DataFrame(
                                    grid_scores,
                                    index=['上 (High)', '中 (Mid)', '下 (Low)'],
                                    columns=['左 (Left)', '正中 (Center)', '右 (Right)']
                                )
                                
                                # 上色規則 
                                def color_rules_pct(val):
                                    if pd.isna(val):
                                        return ""
                                    elif val >= 20.0:
                                        return "background-color: #ffcccc; color: #990000;" # 佔比>=20% (淺紅)
                                    elif val >= 10.0:
                                        return "background-color: #ffffcc; color: #888800;" # 佔比10~20% (淺黃)
                                    elif val > 0.0:
                                        return "background-color: #ccffcc; color: #006600;" # 佔比<10% (淺綠)
                                    else:
                                        return "background-color: #f8f9fa; color: #6c757d;" # 佔比 0% (灰)

                                styled_grid = df_grid.style.format("{:.1f}%", na_rep="無資料").map(color_rules_pct)
                                
                                st.dataframe(styled_grid, use_container_width=True)

                            # =========================================================
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
                        # 如果還沒按確認按鈕，就提示使用者
                        st.info("👉 請點選上方「✅ 確認載入此選手資料」以解鎖歷史資料庫與分析看板。")
                else:
                    st.warning("📭 雲端目前沒有任何紀錄。")
                
        except Exception as e:
            st.error(f"❌ 無法讀取歷史紀錄：{e}")
            
    elif admin_password == "":
        st.warning("🔑 請輸入密碼以解鎖選手歷程數據。")
    else:
        st.error("❌ 密碼錯誤！您沒有存取歷史數據的權限。")