# ocr_module.py (修改後：純後端 AI 邏輯)
import streamlit as st
import cv2
import numpy as np
import fitz
import easyocr
from datetime import datetime, timedelta

@st.cache_resource
def load_ocr():
    """載入 OCR 引擎 (僅初次執行會下載模型)"""
    return easyocr.Reader(['ch_tra', 'en'])

reader = load_ocr()

@st.cache_data(show_spinner=False)
def process_ocr_and_heatmap(file_bytes, is_pdf):
    """記憶緩衝區:辨識過便記住結果"""
    if is_pdf:
        img_doc = fitz.open(stream=file_bytes, filetype="pdf")
        page = img_doc.load_page(0)
        pix = page.get_pixmap(dpi=300)
        img = cv2.imdecode(np.frombuffer(pix.tobytes("png"), np.uint8), cv2.IMREAD_COLOR)
    else:
        img = cv2.imdecode(np.frombuffer(file_bytes, np.uint8), cv2.IMREAD_COLOR)
        
    #取文字內容
    ocr_results = reader.readtext(img)
    texts = []
    
    # 拆解 AI 辨識結構
    for res in ocr_results:
        # res 格式為: (bbox, text, confidence)
        texts.append(res[1])
        
    full_text = " ".join(texts)
    heat_scores = analyze_heatmap_to_values(img)

    # 回傳參數
    return img, full_text, heat_scores

def convert_pdf_to_img(file_bytes):
    """PDF 轉圖片邏輯"""
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    page = doc.load_page(0)
    pix = page.get_pixmap(dpi=300)
    return cv2.imdecode(np.frombuffer(pix.tobytes("png"), np.uint8), cv2.IMREAD_COLOR)

def analyze_heatmap_to_values(img: np.ndarray) -> list[float]:
    """
    【強效抗背景噪點 + 致命紅黃強勢扣分版】
    針對 ST0518 進行特化調校：
    1. 嚴格收緊飽和度門檻，徹底過濾背景「左低、右低」等灰色大字與網格。
    2. 紅色與黃色採取強勢扣分法，只要有紅色，命中率直接面臨毀滅性重審，不再被稀釋。
    """
    h_img, w_img, _ = img.shape
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
 
    # ── 自動定位熱圖 ROI ──
    # 【關鍵修正】為了抓到熱圖主體並排除淡淡的灰色背景字，色彩遮罩的飽和度/亮度門檻調高至 60/60
    mask_colored = cv2.inRange(hsv, np.array([0, 60, 60]), np.array([100, 255, 255]))
    row_counts   = np.sum(mask_colored > 0, axis=1)
    search_start = int(h_img * 0.55)
    active_rows  = np.where(row_counts[search_start:] > (w_img * 0.01))[0]
 
    if len(active_rows) > 0:
        # 【修正】高位向下內縮 15px，完美避開最上方的 0%~100% 光譜對照條
        y_start = search_start + active_rows[0]  + 15
        y_end   = search_start + active_rows[-1] + 5
        y_start = max(0, y_start)
        y_end   = min(h_img, y_end)
    else:
        y_start, y_end = int(h_img * 0.63), int(h_img * 0.92)
 
    # 水平範圍：兩側各往內縮一些（7%），防止抓到邊緣無意義的色塊
    x_start, x_end = int(w_img * 0.07), int(w_img * 0.93)
    
    roi_hsv = hsv[y_start:y_end, x_start:x_end]
 
    # ── 建立高精準三色獨立遮罩（調高 S, V 下限至 70 / 90，徹底擊殺灰色字體雜訊）──
    # 紅色：高飽和、高亮度
    mask_red1  = cv2.inRange(roi_hsv, np.array([0,   70,  90]),  np.array([15,  255, 255]))
    mask_red2  = cv2.inRange(roi_hsv, np.array([160, 70,  90]),  np.array([180, 255, 255]))
    mask_red   = cv2.bitwise_or(mask_red1, mask_red2)
 
    # 綠色：調高門檻，只認真正的綠色彈著點
    mask_green  = cv2.inRange(roi_hsv, np.array([35, 70,  90]),  np.array([85, 255, 255]))
 
    # 黃色：調高門檻
    mask_yellow = cv2.inRange(roi_hsv, np.array([16, 70,  90]),  np.array([34, 255, 255]))
 
    # ── 切割九宮格 ──
    roi_rows_red    = np.array_split(mask_red,    3, axis=0)
    roi_rows_green  = np.array_split(mask_green,  3, axis=0)
    roi_rows_yellow = np.array_split(mask_yellow, 3, axis=0)
 
    values = []
    for r in range(3):
        cols_red    = np.array_split(roi_rows_red[r],    3, axis=1)
        cols_green  = np.array_split(roi_rows_green[r],  3, axis=1)
        cols_yellow = np.array_split(roi_rows_yellow[r], 3, axis=1)
 
        for c in range(3):
            n_red    = np.sum(cols_red[c]    > 0)
            n_green  = np.sum(cols_green[c]  > 0)
            n_yellow = np.sum(cols_yellow[c] > 0)
            
            # 微量噪點過濾
            if n_red < 3:    n_red = 0
            if n_green < 3:  n_green = 0
            if n_yellow < 3: n_yellow = 0
            
            total_colored = n_red + n_green + n_yellow
 
            if total_colored == 0:
                values.append(100.0)  # 沒有任何失誤/彈著，維持完美 100
            else:
                # 【演算法升級：強勢扣分邏輯】
                # 為了避免紅色被少數綠色或雜訊稀釋，我們計算紅色與黃色佔「純失誤點」的比例
                # 如果格子內有紅色，採取極具侵略性的扣分法
                red_ratio = n_red / total_colored
                yellow_ratio = n_yellow / total_colored
                
                # 基底分 100，有黃色最高扣 50 分，有紅色最高直接扣 100 分 (變 0 分)
                hit_rate = 100.0 - (red_ratio * 100.0 + yellow_ratio * 50.0)
                
                # 額外安全機制：只要格子內真的存在顯著紅色像素（例如大於15個像素），命中率直接強制封頂不高於 10 分
                if n_red > 15:
                    hit_rate = min(hit_rate, 10.0)
                elif n_yellow > 15 and n_red == 0:
                    hit_rate = min(hit_rate, 50.0)
                
                values.append(round(min(100.0, max(0.0, hit_rate)), 1))
 
    return values

def calculate_sleep_duration(bed, wake):
    """計算睡眠時長"""
    today = datetime.today()
    t_bed = datetime.combine(today, bed)
    t_wake = datetime.combine(today, wake)
    if t_wake <= t_bed:
        t_wake += timedelta(days=1)
    diff = t_wake - t_bed
    return round(diff.seconds / 3600, 1)