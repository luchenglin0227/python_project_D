import pandas as pd
import numpy as np
from datetime import datetime

# 1. 定義統一的欄位映射字典 (根據企劃書規範)
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
        self.field_map = SHOOTING_FIELD_MAP

    def clean_numeric(self, value):
        """將包含 % 或非數字字元的字串轉為浮點數"""
        if isinstance(value, str):
            value = value.replace('%', '').strip()
            try:
                return float(value)
            except ValueError:
                return 0.0
        return float(value) if value is not None else 0.0

    def process_record(self, ocr_data, manual_data):
        """
        核心功能：合併 OCR 結果與手動輸入資料，並進行清洗
        ocr_data: 來自 黃祉誠 的 OCR 模組 dict
        manual_data: 來自 張幼儀 的 Streamlit 表單 dict
        """
        # 合併原始字典
        raw_data = {**ocr_data, **manual_data}
        
        # 轉換為 DataFrame 並重新命名欄位
        df = pd.DataFrame([raw_data])
        df = df.rename(columns=self.field_map)

        # 2. 進行資料型別清洗 (Data Cleaning)
        # 處理射擊數據
        cols_to_fix = ['total_shots', 'first_hit_count', 'second_hit_count', 'miss_count']
        for col in cols_to_fix:
            if col in df.columns:
                df[col] = df[col].apply(lambda x: int(self.clean_numeric(x)))

        # 3. 計算/校正衍生指標 (Feature Engineering)
        if 'total_shots' in df.columns and df['total_shots'].iloc[0] > 0:
            total = df['total_shots'].iloc[0]
            # 確保命中率為小數點格式 (例如 0.86)
            df['hit_rate'] = (df['first_hit_count'] + df['second_hit_count']) / total
            df['first_hit_rate'] = df['first_hit_count'] / total
            df['miss_rate'] = 1 - df['hit_rate']

        # 4. 處理 3x3 熱區矩陣 (numpy array 扁平化儲存)
        # 假設 ocr_data 中有一個 'heatmap_matrix' 是一個 3x3 的 list 或 array
        if 'heatmap_matrix' in raw_data:
            matrix = np.array(raw_data['heatmap_matrix']).flatten()
            heatmap_cols = [
                'heat_lh', 'heat_mh', 'heat_rh',
                'heat_lc', 'heat_mc', 'heat_rc',
                'heat_ll', 'heat_ml', 'heat_rl'
            ]
            for i, col_name in enumerate(heatmap_cols):
                df[col_name] = matrix[i] if i < len(matrix) else 0.0

        # 5. 處理時間欄位 (例如將睡眠時長轉為 float)
        if 'sleep_hours' in df.columns:
            df['sleep_hours'] = df['sleep_hours'].apply(self.clean_numeric)

        # 加入系統標記
        df['created_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        return df

# 使用範例 (之後在 app.py 中呼叫)
if __name__ == "__main__":
    processor = DataProcessor()
    # 模擬資料
    sample_ocr = {"總發射數": "50", "第一發命中": "37", "第二發命中": "8", "heatmap_matrix": [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6], [0.7, 0.8, 0.9]]}
    sample_manual = {"sleep_hours": "7.5", "range_name": "頂福靶場"}
    
    clean_df = processor.process_record(sample_ocr, sample_manual)
    print("清洗後的資料列：")
    print(clean_df.head())