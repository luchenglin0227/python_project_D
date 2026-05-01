import pandas as pd
from processor import DataProcessor

def test_cleaning():
    # 1. 模擬一筆從 OCR 抓下來的原始數據 (故意放一些空格跟中文)
    raw_data = {
        "總發射數": [100, 150, 200],
        "第一發命中": [80, 120, 190],
        "第二發命中": [10, 20, 5],
        "命中率": ["80%", "85%", "95%"]  # 這種帶 % 的字串通常需要清洗
    }
    df_raw = pd.DataFrame(raw_data)
    
    print("--- 原始數據 ---")
    print(df_raw)

    # 2. 呼叫你的 DataProcessor
    # 假設你的類別裡面有一個處理 DataFrame 的方法叫做 clean_data
    processor = DataProcessor()
    
    # 這裡示範如何使用你定義的 SHOOTING_FIELD_MAP 來改名
    df_cleaned = df_raw.rename(columns=processor.field_map)
    
    print("\n--- 清洗後數據 (欄位已映射) ---")
    print(df_cleaned)
    
    # 3. 簡單檢查
    if "total_shots" in df_cleaned.columns:
        print("\n✅ 測試成功：欄位已正確轉換為英文 Schema！")
    else:
        print("\n❌ 測試失敗：欄位名稱沒有變動。")

if __name__ == "__main__":
    test_cleaning()