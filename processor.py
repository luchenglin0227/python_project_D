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
    "失誤數": "miss_count",
    # 注意：hit_rate、first_hit_rate、second_hit_rate、miss_rate
    # 不從 OCR 對應，而是由程式根據原始數字重新計算，確保正確

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
        # 預設值：total_shots 為 0 時，所有命中率都設為 0
        for rate_col in ['hit_rate', 'first_hit_rate', 'second_hit_rate', 'miss_rate']:
            df[rate_col] = 0.0

        if 'total_shots' in df.columns and df['total_shots'].iloc[0] > 0:
            total = df['total_shots'].iloc[0]  # .iloc[0] 取 DataFrame 第一筆資料的值

            # 射擊數字一致性檢查：一發命中 + 二發命中 + 失誤 應等於總發數
            # 人工確認後仍不一致，直接拋出錯誤阻止清洗，由 Streamlit 接住顯示給使用者
            expected = (df['first_hit_count'].iloc[0] +
                        df['second_hit_count'].iloc[0] +
                        df['miss_count'].iloc[0])
            if expected != total:
                raise ValueError(f"數字不一致：總發數={total}，一發+二發+失誤={expected}，請回頭修正")

            # total_shots > 0 才計算，如果發射次數是 0（OCR 沒讀到或是該次練習沒記錄），就直接填入 0
            df['hit_rate'] = np.where(df['total_shots'] > 0, (df['first_hit_count'] + df['second_hit_count']) / df['total_shots'], 0)

            df['first_hit_rate'] = np.where(df['total_shots'] > 0, df['first_hit_count'] / df['total_shots'], 0)

            df['miss_rate'] = np.where(df['total_shots'] > 0,  df['miss_count'] / df['total_shots'], 0)

        # 數值範圍驗證
        # 疲勞程度和緊張程度應在 1-5 之間，超出範圍自動修正
        for col in ['fatigue_level', 'tension_level']:
            if col in df.columns:
                df[col] = df[col].clip(1, 5)

        # 時間欄位格式統一
        # 如果是字串（OCR 傳來）才需要轉換，Streamlit time_input 傳來的已經是 time 物件
        time_cols = ['bedtime', 'wake_up_time', 'arrival_time']
        for col in time_cols:
            if col in df.columns:
                if isinstance(df[col].iloc[0], str):
                    df[col] = pd.to_datetime(
                        df[col], format='%H:%M:%S', errors='coerce'
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
    processor = DataProcessor()

    # 範例 A：數字一致，正常清洗（37+8+5=50）
    print("\n=== [測試 A：正常資料] ===")
    ocr_a = {"總發數": "50", "一發命中數": "37", "二發命中數": "8", "失誤數": "5"}
    manual_a = {
        "入睡時間": time(23, 0), "起床時間": time(7, 0), "射擊日期": date(2026, 5, 14),
        "到場時間": time(9, 0), "疲勞程度": 2, "緊張程度": 3, "射擊靶場": "大安靶場"
    }
    df_a = processor.process_record(ocr_a, manual_a)
    print(f"計算睡眠時長: {df_a.iloc[0]['sleep_hours']} 小時 (預期: 8.0)")
    print(f"命中率: {df_a.iloc[0]['hit_rate']:.2f} (預期: 0.90)")

    # 範例 B：數字不一致，應該拋出 ValueError（37+8+3=48 ≠ 50）
    print("\n=== [測試 B：數字不一致，應拋出錯誤] ===")
    ocr_b_bad = {"總發數": "50", "一發命中數": "37", "二發命中數": "8", "失誤數": "3"}
    try:
        processor.process_record(ocr_b_bad, manual_a)
    except ValueError as e:
        print(f"成功攔截錯誤：{e}")

    # 範例 C：總發數為 0 的防呆
    print("\n=== [測試 C：總發數為 0 的防呆] ===")
    ocr_c = {"總發數": "0", "一發命中數": "0", "二發命中數": "0", "失誤數": "0"}
    manual_c = {
        "入睡時間": time(0, 0), "起床時間": time(6, 0), "射擊日期": date(2026, 5, 15),
        "到場時間": time(8, 0), "疲勞程度": 5, "緊張程度": 5, "射擊靶場": "大安靶場"
    }
    df_c = processor.process_record(ocr_c, manual_c)
    print(f"總發數為 0 時的命中率: {df_c.iloc[0]['hit_rate']} (預期: 0.0)")

    # 範例 D：測試 3x3 熱區矩陣攤平
    print("\n=== [測試 D：熱區矩陣解析] ===")
    ocr_d = {
        "總發數": "10", "一發命中數": "5", "二發命中數": "2", "失誤數": "3",
        "heatmap_matrix": [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6], [0.7, 0.8, 0.9]]
    }
    df_d = processor.process_record(ocr_d, manual_a)
    print("熱區左上 (heat_lh):", df_d.iloc[0]['heat_lh'])
    print("熱區右下 (heat_rl):", df_d.iloc[0]['heat_rl'])