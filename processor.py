import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from datetime import time, date

# 定義統一的欄位映射字典
SHOOTING_FIELD_MAP = {
   #基本資訊與關聯欄位
    "使用者編號": "user_id",
    "射擊日期": "record_date",
    "比賽時間": "match_start_time",
    "靶場": "shooting_range",

    #射擊表現欄位 (OCR 辨識部分)
    "總發數": "total_shots",
    "一發命中數": "first_hit_count",
    "二發命中數": "second_hit_count",
    "失誤數": "miss_count",

    #生活因子欄位
    "入睡時間": "bedtime",
    "起床時間": "wake_up_time",
    "到場時間": "arrival_time", 
    "熱身時長": "warm_up_time",
    "早餐熱量": "breakfast_calories",
    "蛋白質": "breakfast_protein",
    "咖啡因攝取": "caffeine_intake",
    "疲勞程度": "fatigue_level",
    "緊張程度": "tension_level",
    "睡眠時長": "sleep_duration",

    #計算指標 (由下方自動衍生，不需前端傳入)
    "總命中數 (一發+二發)": "total_hits",
    "總命中率": "hit_rate",
    "一發命中率": "first_hit_rate",
    "二發命中率": "second_hit_rate",
    "失誤率": "miss_rate",

    #空間分析矩陣欄位
    "左側高位命中率": "miss_left_high",
    "中間高位命中率": "miss_middle_high",
    "右側高位命中率": "miss_right_high",
    "左側中位命中率": "miss_left_mid",
    "正中間命中率": "miss_middle_mid",
    "右側中位命中率": "miss_right_mid",
    "左側低位命中率": "miss_left_low",
    "中間低位命中率": "miss_middle_low",
    "右側低位命中率": "miss_right_low",

    #系統管理欄位 
    "原始圖片存檔路徑": "raw_image_path",
    "系統紀錄時間": "created_at",
}

class DataProcessor:
    def __init__(self):
        # 初始化時載入欄位字典
        self.field_map = SHOOTING_FIELD_MAP

    def clean_numeric(self, value):
        """清洗數字欄位，移除非數字字元"""
        if isinstance(value, str):
            value = value.replace('%', '').strip()
            try:
                return float(value)
            except ValueError:
                return 0.0
        return float(value) if value is not None else 0.0

    def process_record(self, ocr_data, manual_data, raw_image_path=""):
        """
        核心方法：整合所有的數據
        """
        # 1. 數據合併
        raw_data = {**ocr_data, **manual_data}

        # 2. 把合併後的字典轉成 DataFrame
        df = pd.DataFrame([raw_data])
        
        # 3. 把中文欄位名稱對應成英文
        df = df.rename(columns=self.field_map)

        # 4. 資料型別清洗
        cols_to_fix = ['total_shots', 'first_hit_count', 'second_hit_count', 'miss_count']
        for col in cols_to_fix:
            if col in df.columns:
                df[col] = df[col].apply(lambda x: int(self.clean_numeric(x)))

        # 5. 初始化衍生指標欄位
        df['total_hits'] = 0
        for rate_col in ['hit_rate', 'first_hit_rate', 'second_hit_rate', 'miss_rate']:
            df[rate_col] = 0.0

        # 6. 計算衍生指標與資料一致性檢查
        if 'total_shots' in df.columns and df['total_shots'].iloc[0] > 0:
            total = df['total_shots'].iloc[0]
            expected = (df['first_hit_count'].iloc[0] +
                        df['second_hit_count'].iloc[0] +
                        df['miss_count'].iloc[0])
            
            # (此處的防呆只是最後一道防線，前端已經先擋下了)
            if expected != total:
                raise ValueError(f"數字不一致：總發數={total}，一發+二發+失誤={expected}")

            df['total_hits'] = df['first_hit_count'] + df['second_hit_count']
            df['hit_rate'] = df['total_hits'] / df['total_shots']
            df['first_hit_rate'] = df['first_hit_count'] / df['total_shots']
            df['second_hit_rate'] = df['second_hit_count'] / df['total_shots']
            df['miss_rate'] = df['miss_count'] / df['total_shots']

        # 7. 數值範圍驗證
        for col in ['fatigue_level', 'tension_level']:
            if col in df.columns:
                df[col] = df[col].clip(1, 5)

        # 8. 處理九宮格空間數據
        if 'heatmap_matrix' in raw_data and raw_data['heatmap_matrix']:
            matrix = np.array(raw_data['heatmap_matrix']).flatten()
            heatmap_cols = [
                'miss_left_high',   'miss_middle_high',   'miss_right_high',
                'miss_left_mid',    'miss_middle_mid',    'miss_right_mid',
                'miss_left_low',    'miss_middle_low',    'miss_right_low'
            ]
            for i, col_name in enumerate(heatmap_cols):
                df[col_name] = int(matrix[i]) if i < len(matrix) else -1
        else:
            heatmap_cols = [
                'miss_left_high', 'miss_middle_high', 'miss_right_high',
                'miss_left_mid', 'miss_middle_mid', 'miss_right_mid',
                'miss_left_low', 'miss_middle_low', 'miss_right_low'
            ]
            for col_name in heatmap_cols:
                df[col_name] = -1

        # 9. 睡眠變數型別處理 (現在不會再有重複的欄位來干擾這行了)
        if 'sleep_duration' in df.columns:
            df['sleep_duration'] = df['sleep_duration'].apply(self.clean_numeric)

        # 10. 系統管理欄位
        df['raw_image_path'] = raw_image_path
        df['created_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 11. 清除暫存矩陣
        if 'heatmap_matrix' in df.columns:
            df = df.drop(columns=['heatmap_matrix'])

        # 12. 把所有 time/date 物件轉成字串，確保能寫入資料庫
        for col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].apply(lambda x: str(x) if hasattr(x, 'strftime') else x)

        return df