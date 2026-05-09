import pandas as pd
import numpy as np
from datetime import datetime

# 1. 定義統一的欄位映射字典
# 目的：將 OCR 辨識出的中文欄位或手動輸入，統一轉為資料庫/程式使用的英文變數名
SHOOTING_FIELD_MAP = {
    "總發射數": "total_shots",
    "第一發命中": "first_hit_count",
    "第二發命中": "second_hit_count",
    "命中率": "hit_rate",
    "一發命中率": "first_hit_rate",
    "二發命中率": "second_hit_rate",
    "脫靶數": "miss_count",
    "脫靶率": "miss_rate"
}

class DataProcessor:
    def __init__(self):
        # 初始化時載入欄位字典，方便後續 rename 呼叫
        self.field_map = SHOOTING_FIELD_MAP

    def clean_numeric(self, value):
        """
        工具方法：清洗數值型字串
        作用：移除 '%'、空格，並處理髒資料（非數字字串），確保轉為 float 避免運算噴錯
        """
        if isinstance(value, str):
            value = value.replace('%', '').strip()
            try:
                return float(value)
            except ValueError:
                return 0.0  # 如果轉換失敗（例如抓到亂碼），預設回傳 0.0
        return float(value) if value is not None else 0.0

    def process_record(self, ocr_data, manual_data):
        """
        核心方法：整合其他的數據
        - ocr_data: 來自OCR 模組 (辨識表格內容)
        - manual_data: 來自Streamlit 介面 (如心情、睡眠、場地名稱)
        """
        # --- 步驟 1: 數據合併 ---
        # 使用 Python 字典解構語法 {**d1, **d2} 將兩份數據合併成一筆
        raw_data = {**ocr_data, **manual_data}
        
        # 轉換為 DataFrame 格式（1 列數據）並套用欄位字典改名
        df = pd.DataFrame([raw_data])
        df = df.rename(columns=self.field_map)

        # --- 步驟 2: 資料型別清洗 (Data Cleaning) ---
        # 確保核心射擊數值都是「整數 (int)」，方便後續計算加減
        cols_to_fix = ['total_shots', 'first_hit_count', 'second_hit_count', 'miss_count']
        for col in cols_to_fix:
            if col in df.columns:
                df[col] = df[col].apply(lambda x: int(self.clean_numeric(x)))

        # --- 步驟 3: 自動校正衍生指標 (Feature Engineering) ---
        # 即使 OCR 沒抓準百分比，我們也根據原始數字重新計算，確保數據 100% 正確
        if 'total_shots' in df.columns and df['total_shots'].iloc[0] > 0:
            total = df['total_shots'].iloc[0]
            # 計算總命中率 (第一發 + 第二發)
            df['hit_rate'] = (df['first_hit_count'] + df['second_hit_count']) / total
            # 計算第一發命中率
            df['first_hit_rate'] = df['first_hit_count'] / total
            # 計算脫靶率 (1 - 總命中率)
            df['miss_rate'] = 1 - df['hit_rate']

        # --- 步驟 4: 處理飛靶 3x3 熱區矩陣 (Heatmap) ---
        # 邏輯：將 3x3 的二維陣列「壓扁」成 9 個獨立欄位，方便存入 CSV 或資料庫
        # 對應關係：LH (左上), MH (中上), RH (右上)... RL (右下)
        if 'heatmap_matrix' in raw_data:
            matrix = np.array(raw_data['heatmap_matrix']).flatten()
            heatmap_cols = [
                'heat_lh', 'heat_mh', 'heat_rh',
                'heat_lc', 'heat_mc', 'heat_rc',
                'heat_ll', 'heat_ml', 'heat_rl'
            ]
            for i, col_name in enumerate(heatmap_cols):
                # 如果矩陣數據不足 9 格，補 0.0
                df[col_name] = matrix[i] if i < len(matrix) else 0.0

        # --- 步驟 5: 生活變數處理 ---
        # 將睡眠時長等可能影響表現的數據轉為浮點數
        if 'sleep_hours' in df.columns:
            df['sleep_hours'] = df['sleep_hours'].apply(self.clean_numeric)

        # --- 步驟 6: 系統紀錄 ---
        # 自動加入數據處理的時間戳記，追蹤這筆紀錄是什麼時候產生的
        df['created_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        return df

# --- 主程式區塊：供本地測試用 ---
if __name__ == "__main__":
    processor = DataProcessor()
    
    # 模擬數據：假設這是 OCR 抓到的結果
    sample_ocr = {
        "總發射數": "50", 
        "第一發命中": "37", 
        "第二發命中": "8", 
        "heatmap_matrix": [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6], [0.7, 0.8, 0.9]]
    }
    
    # 模擬數據：假設這是表單填寫的結果
    sample_manual = {
        "sleep_hours": "7.5", 
        "range_name": "頂福靶場"
    }
    
    # 執行清洗
    clean_df = processor.process_record(sample_ocr, sample_manual)
    
    # 印出結果預覽
    print("--- 數據清洗成功 ---")
    print(clean_df.head())