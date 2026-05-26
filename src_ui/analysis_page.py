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
            database.load_records.clear()  # 現在 database 有掛快取了，這行可以正常執行
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
                    
                    # =============================================================
                    # 📌 1. 數據轉換準備區（將 0,1,2 轉回中文供表格與文字顯示）
                    # =============================================================
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
                    
                    # =============================================================
                    # 📌 2. 先行篩選區（必須先選擇選手）
                    # =============================================================
                    st.header("🎯 訓練記錄查詢與選手篩選")
                    
                    # 設立橫向三個篩選欄位
                    filter_col1, filter_col2, filter_col3 = st.columns(3)
                    
                    # 第一層：選擇使用者
                    with filter_col1:
                        all_users = sorted(display_df[user_col_zh].dropna().unique().tolist())
                        selected_user = st.selectbox("請先選取選手：", all_users)
                    
                    # 根據選定的使用者，過濾出該選手的中文顯示資料
                    user_filtered_df = display_df[display_df[user_col_zh] == selected_user]
                    
                    # 第二層：選擇訓練日期
                    with filter_col2:
                        all_dates = sorted(user_filtered_df[date_col_zh].dropna().unique().tolist(), reverse=True)
                        selected_date = st.selectbox("選擇訓練日期：", all_dates)
                        
                    # 根據選定的使用者 + 射擊日期，進一步過濾
                    date_filtered_df = user_filtered_df[user_filtered_df[date_col_zh] == selected_date]
                    
                    # 第三層：選擇精確紀錄時間（避免同一天有多筆紀錄）
                    with filter_col3:
                        time_options = []
                        for _, row in date_filtered_df.iterrows():
                            c_val = row.get(created_col_zh, "未知時間")
                            idx_val = row['系統內部序號']
                            time_options.append(f"紀錄時間：{c_val} (序號: {idx_val})")
                            
                        selected_time_str = st.selectbox("選擇紀錄時間：", time_options)
                    
                    # 找出最終被選中的那一筆單次紀錄資料
                    selected_idx = int(selected_time_str.split("(序號: ")[1].replace(")", ""))
                    selected_row = display_df[display_df['系統內部序號'] == selected_idx].iloc[0]
                
                    # =============================================================
                    # 📌 3. 詳細數據展開（顯示中文 良好/尚可/較差）
                    # =============================================================
                    st.markdown("---")
                    st.subheader(f"🔍 當次詳細數據：選手 {selected_user} 在 {selected_date} 的訓練紀錄")
                    
                    with st.container(border=True):
                        col1, col2 = st.columns(2)
                        
                        # 排除不需要顯示的內部序號
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
                                
                    # =============================================================
                    # 📌 4. 後置個人視覺化看板與圖表分析 (Dashboard)
                    # =============================================================
                    st.markdown("---")
                    st.header(f"📈 選手個人表現分析看板 ({selected_user})")
                    st.caption(f"此看板已自動鎖定並篩選選手：**{selected_user}** 的所有歷史數據。")
                    
                    # 💡 【安全相容修正】自動偵測 raw_df 到底是用中文還是英文當欄位名
                    actual_user_col = None
                    if 'user_id' in raw_df.columns:
                        actual_user_col = 'user_id'
                    elif '使用者編號' in raw_df.columns:
                        actual_user_col = '使用者編號'
                    else:
                        actual_user_col = user_col_zh
                    
                    # 核心過濾：用動態偵測到的正確欄位切出指定選手資料
                    user_raw_df = raw_df[raw_df[actual_user_col] == selected_user].copy()
                    
                    # 💡 將這份個人資料的欄位名稱對齊成英文，確保後續順利運算
                    user_raw_df = user_raw_df.rename(columns=SHOOTING_FIELD_MAP)
                    
                    # 尋找對應的命中率欄位
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
                            
                    # 如果找到了命中率數據，就畫出個人專屬 KPI 與 趨勢圖
                    if hit_rate_col in user_raw_df.columns and not user_raw_df.empty:
                        try:
                            # 確保數據是數字
                            valid_rates = pd.to_numeric(user_raw_df[hit_rate_col], errors='coerce').dropna()
                            avg_hit_rate = valid_rates.mean()
                            
                            # 如果命中率原本就是 0-100 的百分比，則調整計算
                            if avg_hit_rate > 1.0:
                                avg_hit_rate = avg_hit_rate / 100.0
                                
                            avg_miss_rate = 1.0 - avg_hit_rate

                            # A. 個人 Performance KPI 儀表板
                            st.subheader("個人歷史平均 Performance KPI")
                            dkpi1, dkpi2 = st.columns(2)
                            dkpi1.metric("個人平均 Hit Rate", f"{avg_hit_rate:.2%}")
                            dkpi2.metric("個人平均 Miss Rate", f"{avg_miss_rate:.2%}")

                            # B. 個人 Performance Trend 趨勢折線圖
                            st.subheader("個人歷史表現趨勢 (Performance Trend)")
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
                        except Exception as chart_err:
                            st.info(f"💡 趨勢圖表正在等待更多標準格式數據累積中...")
                    else:
                        st.info(f"💡 該選手目前尚無足夠的命中率數據生成歷史趨勢圖。")
                    
                    # =============================================================
                    # 📌 5. 個人生活作息交叉分析
                    # =============================================================
                    st.markdown("---")
                    st.subheader("進階交叉分析 (生活作息 vs 射擊表現)")
                    st.caption(f"分析選手 **{selected_user}** 的個人生理與心理狀態，如何影響最終的射擊命中率。")
                        
                    ana_col1, ana_col2 = st.columns(2)
    
                    # 1. 睡眠時長 vs 命中率 (折線圖)
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
                            st.info("💡 雲端資料庫累積更多睡眠數據後將自動顯示圖表。")
    
                    # 2. 緊張程度 vs 失誤率 (長條圖)
                    # 💡 【關鍵修正】補齊原本在此處中斷的語法，並關閉對應的縮排
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
                            st.info("💡 雲端資料庫累積更多緊張程度數據後將自動顯示圖表。")
                else:
                    st.warning("📭 雲端目前沒有任何紀錄。")
                
        except Exception as e:
            st.error(f"❌ 無法讀取歷史紀錄：{e}")
            
    elif admin_password == "":
        st.warning("🔑 請輸入密碼以解鎖選手歷程數據。")
    else:
        st.error("❌ 密碼錯誤！您沒有存取歷史數據的權限。")