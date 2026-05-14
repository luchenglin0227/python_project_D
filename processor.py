import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from datetime import time, date

# 定義統一的欄位映射字典
# 目的：將 OCR 辨識出的中文欄位或手動輸入，統一轉為資料庫/程式使用的英文變數名
SHOOTING_FIELD_MAP = {
    # OCR 辨識的欄位
    "總發數": "total_shots",
    "一發命中數": "first_hit_count",
    "二發命中數": "second_hit_count",
    "總命中率": "hit_rate",
    "一發命中率": "first_hit_rate",
    "二發命中率": "second_hit_rate",
    "失誤數": "miss_count",
    "失誤率": "miss_rate",

    # Streamlit 介面欄位
    "入睡時間": "bedtime",
    "起床時間": "wake_up_time",
    "到場時間": "arrival_time",
    "熱身時長": "warm_up_time",
    "早餐熱量": "breakfast_calories",
    "蛋白質": "breakfast_protein",
    "咖啡因攝取": "caffeine_intake",
    "疲勞程度": "fatigue_level",
    "緊張程度": "tension_level",
    "射擊靶場": "range_name",
}

# 建立初始化
# 將外部常數 SHOOTING_FIELD_MAP（字典 dict），賦值給變數 self.field_map
class DataProcessor:
    def __init__(self):
        # 初始化時載入欄位字典
        self.field_map = SHOOTING_FIELD_MAP

    # 把混亂的數值資料轉為浮點數值
    def clean_numeric(self, value):
        """
        工具方法：清洗數值型字串
        作用：移除 '%'、空格，並處理髒資料（非數字字串），確保轉為 float
        """
        if isinstance(value, str):  # 處理字串類型的值
            value = value.replace('%', '').strip()
            # 將 % 替換成空白字串並移除字串前後的空白字元
            try:
                return float(value)  # 回傳已清理好的數值
            except ValueError:
                return 0.0  # 如果轉換失敗，回傳 0.0
        # 處理其他型別的值 (int, float, NoneType)
        return float(value) if value is not None else 0.0  # float(None) 回傳 0.0

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
        return round(duration.seconds / 3600, 2)  # 回傳小時數，例如 7.5

    def process_record(self, ocr_data, manual_data):
        """
        核心方法：整合其他的數據
        - ocr_data: 來自 OCR 模組（辨識表格內容）
        - manual_data: 來自 Streamlit 介面（如心情、睡眠、場地名稱）
        """
        # 數據合併
        # 使用 Python 字典解構語法 {**d1, **d2} 將兩份數據合併成一筆
        raw_data = {**ocr_data, **manual_data}

        # 計算睡眠時長（由入睡時間和起床時間換算，不依賴使用者直接輸入）
        raw_data["sleep_hours"] = self.calculate_sleep(
            raw_data["入睡時間"],
            raw_data["起床時間"],
            raw_data["射擊日期"]
        )

        # 把合併後的字典轉成 DataFrame
        df = pd.DataFrame([raw_data])
        # 把中文欄位名稱對應成英文
        df = df.rename(columns=self.field_map)  # 轉換 OCR 的中文

        # 資料型別清洗
        # 確保射擊數值都是「整數 (int)」
        cols_to_fix = ['total_shots', 'first_hit_count', 'second_hit_count', 'miss_count']
        for col in cols_to_fix:  # 逐一遍歷每個欄位名稱
            if col in df.columns:  # 先用 clean_numeric 處理所有髒資料，再轉整數
                df[col] = df[col].apply(lambda x: int(self.clean_numeric(x)))

        # 自動校正衍生指標 (Feature Engineering)
        # 即使 OCR 沒抓準百分比，我們也根據原始數字重新計算，確保數據 100% 正確
        if 'total_shots' in df.columns and df['total_shots'].iloc[0] > 0:
            total = df['total_shots'].iloc[0]  # .iloc[0] 取 DataFrame 第一筆資料的值

            # 射擊數字一致性檢查：一發命中 + 二發命中 + 失誤 應等於總發數
            expected = (df['first_hit_count'].iloc[0] +
                        df['second_hit_count'].iloc[0] +
                        df['miss_count'].iloc[0])
            if expected != total:
                print(f"警告：數字不一致，總發數={total}，加總={expected}")

            # 計算總命中率（第一發 + 第二發）
            df['hit_rate'] = (df['first_hit_count'] + df['second_hit_count']) / total
            # 計算第一發命中率
            df['first_hit_rate'] = df['first_hit_count'] / total
            # 計算第二發命中率
            df['second_hit_rate'] = df['second_hit_count'] / total
            # 計算脫靶率（1 - 總命中率）
            df['miss_rate'] = 1 - df['hit_rate']

        # 數值範圍驗證
        # 疲勞程度和緊張程度應在 1-5 之間，超出範圍自動修正
        for col in ['fatigue_level', 'tension_level']:
            if col in df.columns:
                df[col] = df[col].clip(1, 5)

        # 時間欄位格式統一
        # 確保時間欄位格式一致，避免 OCR 或使用者輸入格式不同造成問題
        time_cols = ['bedtime', 'wake_up_time', 'arrival_time']
        for col in time_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(
                    df[col].astype(str), format='%H:%M:%S', errors='coerce'
                ).dt.time

        # 處理飛靶 3x3 熱區矩陣 (Heatmap)
        # 邏輯：將 3x3 的二維陣列壓成 9 個獨立欄位，方便存入 CSV 或資料庫
        # 對應關係：LH（左上）, MH（中上）, RH（右上）... RL（右下）
        if 'heatmap_matrix' in raw_data:  # 確認原始資料中有 heatmap_matrix
            matrix = np.array(raw_data['heatmap_matrix']).flatten()  # 把二維陣列壓扁成一維
            heatmap_cols = [
                'heat_lh', 'heat_mh', 'heat_rh',
                'heat_lc', 'heat_mc', 'heat_rc',
                'heat_ll', 'heat_ml', 'heat_rl'
            ]
            for i, col_name in enumerate(heatmap_cols):
                # 如果矩陣數據不足 9 格，補 0.0
                df[col_name] = matrix[i] if i < len(matrix) else 0.0

        # 生活變數處理
        # 將睡眠時長等可能影響表現的數據轉為浮點數
        if 'sleep_hours' in df.columns:
            df['sleep_hours'] = df['sleep_hours'].apply(self.clean_numeric)

        # 系統紀錄
        # 自動加入數據處理的時間戳記，追蹤這筆紀錄是什麼時候產生的
        df['created_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return df


# 主程式區塊：供本地測試用
# 只有直接執行這個檔案時才會跑
if __name__ == "__main__":
    processor = DataProcessor()  # 建立一個 DataProcessor 物件，__init__ 會自動執行，載入 field_map

    # 模擬數據：假設這是 OCR 抓到的結果
    sample_ocr = {
        "總發數": "50",
        "一發命中數": "37",
        "二發命中數": "8",
        "失誤數": "5",
        "heatmap_matrix": [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6], [0.7, 0.8, 0.9]]
    }

    # 模擬數據：假設這是表單填寫的結果
    sample_manual = {
        "入睡時間": time(23, 0),    # 晚上 11 點入睡
        "起床時間": time(7, 0),     # 早上 7 點起床
        "射擊日期": date(2024, 1, 15),
        "到場時間": time(9, 0),
        "熱身時長": "20",
        "早餐熱量": "650",
        "蛋白質": "30",
        "咖啡因攝取": "100",
        "疲勞程度": 2,
        "緊張程度": 3,
        "射擊靶場": "A靶場"
    }

    # 執行整個清洗流程，回傳乾淨的 DataFrame
    clean_df = processor.process_record(sample_ocr, sample_manual)

    # 印出結果預覽
    print("--- 數據清洗成功 ---")
    print(clean_df.head())
    print(clean_df[['fatigue_level', 'tension_level']])