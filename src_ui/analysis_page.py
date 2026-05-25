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
                    # =============================================================
                    # 📌 大盤視覺化看板 (Dashboard) 
                    # =============================================================
                    st.markdown("---")
                    st.header("📈 全隊整體表現 Dashboard")
                    
                    # 尋找組員資料表中對應的命中率欄位
                    hit_rate_col = None
                    for eng, zh in SHOOTING_FIELD_MAP.items():
                        if "命中率" in eng or "hit_rate" in zh:
                            hit_rate_col = zh
                            break
                    if not hit_rate_col:
                        for col in raw_df.columns:
                            if "命中率" in str(col) or "rate" in str(col).lower():
                                hit_rate_col = col
                                break

                    # 如果找到了命中率數據，就畫出你的精美 KPI & 趨勢圖
                    if hit_rate_col in raw_df.columns:
                        try:
                            # 確保數據是數字
                            valid_rates = pd.to_numeric(raw_df[hit_rate_col], errors='coerce').dropna()
                            avg_hit_rate = valid_rates.mean()
                            
                            # 如果命中率原本就是 0-100 的百分比，則調整計算
                            if avg_hit_rate > 1.0:
                                avg_hit_rate = avg_hit_rate / 100.0
                                
                            avg_miss_rate = 1.0 - avg_hit_rate

                            # 1. 你的 Performance KPI 儀表板
                            st.subheader("Performance KPI")
                            dkpi1, dkpi2 = st.columns(2)
                            dkpi1.metric("全隊平均 Hit Rate", f"{avg_hit_rate:.2%}")
                            dkpi2.metric("全隊平均 Miss Rate", f"{avg_miss_rate:.2%}")

                            # 2. 你的 Performance Trend 趨勢折線圖
                            st.subheader("Performance Trend (歷史表現趨勢)")
                            date_col = None
                            for eng, zh in SHOOTING_FIELD_MAP.items():
                                if "日期" in eng or "date" in zh:
                                    date_col = zh
                                    break
                            
                            if date_col in raw_df.columns:
                                trend_df = raw_df.copy()
                                trend_df["parsed_date"] = pd.to_datetime(trend_df[date_col]).dt.date
                                trend_df[hit_rate_col] = pd.to_numeric(trend_df[hit_rate_col], errors='coerce')
                                if trend_df[hit_rate_col].mean() > 1.0:
                                    trend_df[hit_rate_col] = trend_df[hit_rate_col] / 100.0
                                    
                                trend_data = trend_df.groupby("parsed_date")[hit_rate_col].mean()
                                st.line_chart(trend_data)
                        except Exception as chart_err:
                            st.info(f"💡 趨勢圖表正在等待更多標準格式數據累積中...")
                    else:
                        st.info("💡 雲端資料串接成功！當正式數據寫入後，此處將自動呈現你的 Performance KPI 與 Trend 折線圖。")
                    
                    st.markdown("---")                    
                    
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
                        # ==========================================
                        # 進階數據交叉分析 
                        # ==========================================
                        st.markdown("---")
                        st.subheader(" 進階交叉分析 (生活作息 vs 射擊表現)")
                        st.caption("分析全隊選手的賽前生理與心理狀態，如何影響最終的射擊命中率。")
                        
                        # 複製一份原始資料來畫圖
                        df_analysis = raw_df.copy()
    
                        ana_col1, ana_col2 = st.columns(2)
    
                        # 1. 睡眠時長 vs 命中率 (折線圖)
                        with ana_col1:
                            st.write("** 睡眠時長 vs 平均命中率 (%)**")
                            # 檢查欄位是否存在
                            if 'sleep_duration' in df_analysis.columns and 'hit_rate' in df_analysis.columns:
                                # 確保資料型態為數字，並將睡眠時間四捨五入分群
                                df_analysis['sleep_duration'] = pd.to_numeric(df_analysis['sleep_duration'], errors='coerce')
                                df_analysis['sleep_group'] = df_analysis['sleep_duration'].round()
                                
                                # 確保命中率換算為百分比
                                hit_data = pd.to_numeric(df_analysis['hit_rate'], errors='coerce')
                                if hit_data.mean() <= 1.0:
                                    hit_data = hit_data * 100
                                df_analysis['hit_rate_pct'] = hit_data
                                
                                # 畫出折線圖
                                sleep_trend = df_analysis.groupby('sleep_group')['hit_rate_pct'].mean()
                                st.line_chart(sleep_trend)
                            else:
                                st.info("💡 雲端資料庫累積更多睡眠數據後將自動顯示圖表。")
    
                        # 2. 緊張程度 vs 失誤率 (長條圖)
                        with ana_col2:
                            st.write("**賽前緊張程度 vs 平均失誤率 (%)**")
                            if 'tension_level' in df_analysis.columns and 'miss_rate' in df_analysis.columns:
                                df_analysis['tension_level'] = pd.to_numeric(df_analysis['tension_level'], errors='coerce')
                                
                                miss_data = pd.to_numeric(df_analysis['miss_rate'], errors='coerce')
                                if miss_data.mean() <= 1.0:
                                    miss_data = miss_data * 100
                                df_analysis['miss_rate_pct'] = miss_data
                                
                                tension_trend = df_analysis.groupby('tension_level')['miss_rate_pct'].mean()
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
