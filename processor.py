import os #先放標準庫（如 os, json），再放第三方庫
import sys

class DataProcessor:
    """處理專案數據的核心類別"""
    
    def __init__(self, config=None):
        self.config = config
        print("Processor 已初始化")

    def process_data(self, data):
        # 在此實作你的主要邏輯
        print(f"正在處理數據: {data}")
        return data

def main():
    # 專案執行入口
    processor = DataProcessor()
    sample_data = "Hello World"
    processor.process_data(sample_data)

if __name__ == "__main__":
    main()