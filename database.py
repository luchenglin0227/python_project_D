import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# 雲端資料表的名稱（對應 Google Sheet 裡面的分頁工作表名稱）
WORKSHEET_NAME = "records"

def _get_gsheets_conn():
    """建立並回傳 Google Sheets 的雲端連線物件"""
    try:
        # 使用 Streamlit 官方推薦的連線方式
        conn = st.connection("gsheets", type=GSheetsConnection)
        return conn
    except Exception as e:
        st.error(f"⚠️ Google Sheets 連線初始化失敗，請檢查 secrets.toml 設定。錯誤訊息: {e}")
        return None

def init_db() -> None:
    """
    初始化雲端資料表。
    提示：請先手動在 Google Drive 建立一個 Google Sheet，
    並在第一行（Header）填入對應的英文欄位名稱。
    """
    st.info("☁️ 系統正使用 Google Sheets 雲端資料庫。請確保您的雲端表單第一行已建立正確的欄位名稱。")

def insert_record(clean_df: pd.DataFrame) -> bool:
    """
    將 DataProcessor 清洗完傳回的單筆 DataFrame 紀錄，直接附加（Append）到雲端 Google Sheet 中。
    - clean_df: 來自 processor.process_record() 回傳的 DataFrame
    """
    conn = _get_gsheets_conn()
    if conn is None:
        return False
        
    try:
        # 1. 先從雲端讀取目前現有的所有紀錄
        existing_df = conn.read(worksheet=WORKSHEET_NAME, ttl=0)
    except Exception:
        # 如果是全新空白的表單，建立一個空 DataFrame
        existing_df = pd.DataFrame()

    try:
        # 2. 確保新資料有補上建立時間戳記
        if "created_at" not in clean_df.columns:
            clean_df["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 3. 將新舊資料合併（串接在最後一列）
        if not existing_df.empty:
            # 確保欄位順序與雲端一致
            updated_df = pd.concat([existing_df, clean_df], ignore_index=True)
        else:
            updated_df = clean_df

        # 4. 將整張更新後的大表重新推回雲端覆蓋覆寫
        conn.update(worksheet=WORKSHEET_NAME, data=updated_df)
        return True
    except Exception as e:
        st.error(f"❌ 雲端資料寫入失敗: {e}")
        return False

# 💡 【關鍵修正】加上 cache_data 裝飾器，這樣別的頁面才能使用 .clear() 清除此函式的快取
@st.cache_data(ttl=0)
def load_records(user_id: str = None) -> pd.DataFrame:
    """
    從 Google Sheets 雲端即時載入所有紀錄，回傳為 Pandas DataFrame。
    """
    conn = _get_gsheets_conn()
    if conn is None:
        return pd.DataFrame()

    try:
        # 即時從雲端抓取最新數據
        df = conn.read(worksheet=WORKSHEET_NAME, ttl=0)
        
        if df.empty:
            return df

        # 根據 user_id 進行篩選（若有提供）
        if user_id:
            df = df[df["user_id"] == user_id]

        # 確保日期欄位格式正確
        if "record_date" in df.columns:
            df["record_date"] = pd.to_datetime(df["record_date"], errors="coerce")
            df = df.sort_values(by="record_date", ascending=False)

        return df
    except Exception as e:
        st.error(f"❌ 雲端資料載入失敗: {e}")
        return pd.DataFrame()
    
@st.cache_data(ttl="5m")
def get_all_records():
    """
    從 Google Sheets 讀取所有歷史紀錄並回傳為 DataFrame
    """
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(worksheet="records", ttl="5m") 
        return df
    except Exception as e:
        print(f"讀取雲端資料失敗: {e}")
        return None