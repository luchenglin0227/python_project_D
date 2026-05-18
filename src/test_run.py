from processor import DataProcessor
import pandas as pd

# 初始化處理器
proc = DataProcessor()

# 模擬三種不同的開發場景
test_cases = [
    {
        "name": "場景 1：正常數據",
        "ocr": {"總發射數": 100, "第一發命中": 60, "第二發命中": 20, "脫靶數": 20},
        "ui": {"mood": "專注", "fatigue_level": 1, "tension_level": 1}
    },
    {
        "name": "場景 2：總數為 0 (測試防呆)",
        "ocr": {"總發射數": 0, "第一發命中": 0, "第二發命中": 0, "脫靶數": 0},
        "ui": {"mood": "疲累", "fatigue_level": 5, "tension_level": 4}
    },
    {
        "name": "場景 3：OCR 誤讀數據 (總數小於命中數)",
        "ocr": {"總發射數": 10, "第一發命中": 15, "第二發命中": 5, "脫靶數": 0},
        "ui": {"mood": "普通", "fatigue_level": 3, "tension_level": 2}
    }
]

print("--- 開始執行壓力測試 ---")

for case in test_cases:
    print(f"\n[測試中] {case['name']}")
    try:
        # 執行清潔與計算
        result_df = proc.process_record(case['ocr'], case['ui'])
        
        # 檢查關鍵欄位是否產出 NaN 或 Inf
        if result_df['hit_rate'].isnull().any():
            print("❌ 警告：產出了空值 (NaN)")
        else:
            print(f"✅ 計算成功！命中率: {result_df.iloc[0]['hit_rate']:.2f}")
            
        # 顯示部分結果
        print(result_df[['total_shots', 'hit_rate', 'mood']].to_string(index=False))
        
    except Exception as e:
        print(f"💥 程式崩潰！錯誤原因: {e}")

print("\n--- 測試結束 ---")