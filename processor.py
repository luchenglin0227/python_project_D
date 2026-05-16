import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from datetime import time, date

# 定義統一的欄位映射字典
# 目的：將 OCR 辨識出的中文欄位或手動輸入，統一轉為資料庫/程式使用的英文變數名
SHOOTING_FIELD_MAP = {
    # 1. 基本資訊與關聯欄位
    "使用者編號": "user_id",
    "射擊日期": "record_date",
    "比賽時間": "match_start_time",
    "靶場": "shooting_range",

    # 2. 射擊表現欄位 (OCR 辨識部分)
    "總發數": "total_shots",
    "一發命中數": "first_hit_count",
    "二發命中數": "second_hit_count",
    "失誤數": "miss_count",

    # 3. 賽前生活因子欄位
    "入睡時間": "bedtime",
    "起床時間": "wake_up_time",
    "到場時間": "arrival_time", 
    "熱身時長": "warm_up_time",
    "早餐熱量": "breakfast_calories",
    "蛋白質": "breakfast_protein",
    "咖啡因攝取": "caffeine_intake",
    "疲勞程度": "fatigue_level",
    "緊張程度": "tension_level",
    "射擊靶場": "Shooting_range",
}

class DataProcessor:
    def __init__(self):
        # 初始化時載入欄位字典
        self.field_map = SHOOTING_FIELD_MAP

    def clean_numeric(self, value):
        """
        工具方法：清洗數值型字串
        作用：移除 '%'、空格，並處理髒資料（非數字字串），確保轉為 float
        """
        if isinstance(value, str):
            value = value.replace('%', '').strip()
            try:
                return float(value)
            except ValueError:
                return 0.0
        return float(value) if value is not None else 0.0

    def calculate_sleep(self, bedtime, wake_up_time, shoot_date):
        """
        工具方法：根據入睡時間和起床時間計算睡眠時長
        - 回傳小時數（float），例如 7.5 代表 7 小時 30 分鐘
        - 自動處理跨日問題（例如 23:00 入睡，07:00 起床）
        """
        wake_dt = datetime.combine(shoot_date, wake_up_time)
        bed_dt  = datetime.combine(shoot_date, bedtime)

        # 跨日處理：如果入睡時間 >= 起床時間，代表是前一天入睡
        if bed_dt >= wake_dt:
            bed_dt -= timedelta(days=1)

        duration = wake_dt - bed_dt
        return round(duration.seconds / 3600, 2)

    def process_record(self, ocr_data, manual_data, raw_image_path="", ocr_confidence=1.0):
        """
        核心方法：整合所有的數據
        - ocr_data: 來自 OCR 模組（辨識表格內容）
        - manual_data: 來自 Streamlit 介面
        - raw_image_path: 原始圖片路徑
        - ocr_confidence: OCR 信心分數
        """
        # 數據合併
        raw_data = {**ocr_data, **manual_data}

        # 計算睡眠時長（對應新規範欄位名稱：sleep_duration）
        if "入睡時間" in raw_data and "起床時間" in raw_data and "射擊日期" in raw_data:
            raw_data["sleep_duration"] = self.calculate_sleep(
                raw_data["入睡時間"],
                raw_data["起床時間"],
                raw_data["射擊日期"]
            )
        else:
            raw_data["sleep_duration"] = 0.0

        # 把合併後的字典轉成 DataFrame
        df = pd.DataFrame([raw_data])
        
        # 把中文欄位名稱對應成英文
        df = df.rename(columns=self.field_map)

        # 資料型別清洗：確保射擊數值都是「整數 (int)」
        cols_to_fix = ['total_shots', 'first_hit_count', 'second_hit_count', 'miss_count']
        for col in cols_to_fix:
            if col in df.columns:
                df[col] = df[col].apply(lambda x: int(self.clean_numeric(x)))

        # 初始化衍生指標欄位（確保欄位一定存在，避免模型出錯）
        df['total_hits'] = 0
        for rate_col in ['hit_rate', 'first_hit_rate', 'second_hit_rate', 'miss_rate']:
            df[rate_col] = 0.0

        # 計算衍生指標與資料一致性檢查
        if 'total_shots' in df.columns and df['total_shots'].iloc[0] > 0:
            total = df['total_shots'].iloc[0]
            expected = (df['first_hit_count'].iloc[0] +
                        df['second_hit_count'].iloc[0] +
                        df['miss_count'].iloc[0])
            
            if expected != total:
                raise ValueError(f"數字不一致：總發數={total}，一發+二發+失誤={expected}，請回頭修正")

            # 根據新規範重新計算表現指標
            df['total_hits'] = df['first_hit_count'] + df['second_hit_count']
            df['hit_rate'] = df['total_hits'] / df['total_shots']
            df['first_hit_rate'] = df['first_hit_count'] / df['total_shots']
            df['second_hit_rate'] = df['second_hit_count'] / df['total_shots']
            df['miss_rate'] = df['miss_count'] / df['total_shots']

        # 數值範圍驗證：疲勞程度和緊張程度應在 1-5 之間
        for col in ['fatigue_level', 'tension_level']:
            if col in df.columns:
                df[col] = df[col].clip(1, 5)

        # 時間欄位格式統一
        time_cols = ['bedtime', 'wake_up_time', 'arrival_time', 'match_start_time']
        for col in time_cols:
            if col in df.columns:
                if isinstance(df[col].iloc[0], str):
                    df[col] = pd.to_datetime(
                        df[col], format='%H:%M:%S', errors='coerce'
                    ).dt.time

        # 4. 空間分析矩陣處理 (根據新命名規範：方位_高度)
        if 'heatmap_matrix' in raw_data:
            matrix = np.array(raw_data['heatmap_matrix']).flatten()
            heatmap_cols = [
                'miss_left_high',   'miss_middle_high',   'miss_right_high',
                'miss_left_mid',    'miss_middle_mid',    'miss_right_mid',
                'miss_left_low',    'miss_middle_low',    'miss_right_low'
            ]
            for i, col_name in enumerate(heatmap_cols):
                df[col_name] = int(matrix[i]) if i < len(matrix) else 0
        else:
            # 若無傳入矩陣，預設補 0
            heatmap_cols = [
                'miss_left_high', 'miss_middle_high', 'miss_right_high',
                'miss_left_mid', 'miss_middle_mid', 'miss_right_mid',
                'miss_left_low', 'miss_middle_low', 'miss_right_low'
            ]
            for col_name in heatmap_cols:
                df[col_name] = 0

        # 生活變數處理
        if 'sleep_duration' in df.columns:
            df['sleep_duration'] = df['sleep_duration'].apply(self.clean_numeric)

        # 5. 系統管理欄位
        df['raw_image_path'] = raw_image_path
        df['ocr_confidence'] = float(ocr_confidence)
        df['created_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return df


# 主程式區塊：供本地測試用
if __name__ == "__main__":
    processor = DataProcessor()

    # 基礎手動輸入資料範例
    base_manual = {
        "使用者編號": "U101",
        "射擊日期": date(2026, 5, 14),
        "比賽時間": time(10, 30),
        "靶場": "大安靶場",
        "入睡時間": time(23, 0), 
        "起床時間": time(7, 0), 
        "到場時間": time(9, 0), 
        "疲勞程度": 2, 
        "緊張程度": 3,
        "熱身時長": 15.0,
        "早餐熱量": 450.0,
        "蛋白質": 25.0,
        "咖啡因攝取": 80.0
    }

    # 模擬 3x3 矩陣脫靶數據
    sample_heatmap = [[1, 0, 2], [0, 1, 0], [3, 0, 1]]

    # 範例 A：正常資料清洗測試
    print("\n=== [測試 A：全新規範變數轉換驗證] ===")
    ocr_a = {
        "總發數": "50", 
        "一發命中數": "37", 
        "二發命中數": "8", 
        "失誤數": "5",
        "heatmap_matrix": sample_heatmap
    }
    
    df_a = processor.process_record(
        ocr_a, 
        base_manual, 
        raw_image_path="/images/shot_001.png", 
        ocr_confidence=0.98
    )
    
    print(f"使用者 ID: {df_a.iloc[0]['user_id']} | 紀錄日期: {df_a.iloc[0]['record_date']}")
    print(f"系統換算睡眠時長 (sleep_duration): {df_a.iloc[0]['sleep_duration']} 小時")
    print(f"總命中數 (total_hits): {df_a.iloc[0]['total_hits']} | 總命中率 (hit_rate): {df_a.iloc[0]['hit_rate']:.2f}")
    print(f"空間分析 (正中間脫靶 miss_middle_mid): {df_a.iloc[0]['miss_middle_mid']}")
    print(f"圖片路徑 (raw_image_path): {df_a.iloc[0]['raw_image_path']} (信心值: {df_a.iloc[0]['ocr_confidence']})")