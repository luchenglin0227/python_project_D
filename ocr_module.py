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
        texts.append(res[1])
        
    full_text = " ".join(texts)
    heat_scores = analyze_heatmap_to_values(img)

    # 📌 【修正重點 1】回傳 Dictionary，對齊 upload_page.py 的 .get() 取值方式
    return {
        "total_shots": 0,
        "first_hit": 0,
        "second_hit": 0,
        "miss": 0,
        "heatmap_matrix": heat_scores
    }

def convert_pdf_to_img(file_bytes):
    """PDF 轉圖片邏輯"""
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    page = doc.load_page(0)
    pix = page.get_pixmap(dpi=300)
    return cv2.imdecode(np.frombuffer(pix.tobytes("png"), np.uint8), cv2.IMREAD_COLOR)

def analyze_heatmap_to_values(img: np.ndarray) -> list[float]:
    """
    【高精準抗干擾版】
    1. 加強紅色極端值的捕捉能力
    2. 縮緊高位邊界，並引入微量像素過濾機制，防止光譜圖外框雜訊干擾
    """
    h_img, w_img, _ = img.shape
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
 
    # ── 自動定位熱圖 ROI ──
    mask_colored = cv2.inRange(hsv, np.array([0, 40, 40]), np.array([100, 255, 255]))
    row_counts   = np.sum(mask_colored > 0, axis=1)
    search_start = int(h_img * 0.55)
    active_rows  = np.where(row_counts[search_start:] > (w_img * 0.01))[0]
 
    if len(active_rows) > 0:
        y_start = search_start + active_rows[0]  + 5
        y_end   = search_start + active_rows[-1] + 10
        y_start = max(0, y_start)
        y_end   = min(h_img, y_end)
    else:
        y_start, y_end = int(h_img * 0.63), int(h_img * 0.92)
 
    x_start, x_end = int(w_img * 0.06), int(w_img * 0.94)
    roi_hsv = hsv[y_start:y_end, x_start:x_end]
 
    mask_red1  = cv2.inRange(roi_hsv, np.array([0,   30, 30]), np.array([18,  255, 255]))
    mask_red2  = cv2.inRange(roi_hsv, np.array([155, 30, 30]), np.array([180, 255, 255]))
    mask_red   = cv2.bitwise_or(mask_red1, mask_red2)
    mask_green  = cv2.inRange(roi_hsv, np.array([35, 30, 30]), np.array([85, 255, 255]))
    mask_yellow = cv2.inRange(roi_hsv, np.array([19, 30, 30]), np.array([34, 255, 255]))
 
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
            
            # 📌 【修正重點 2】統一邏輯寫法，直接使用已經算好的 n_green 變數
            if n_red < 5:    n_red = 0
            if n_green < 5:  n_green = 0 
            if n_yellow < 5: n_yellow = 0
            
            total_colored = n_red + n_green + n_yellow
 
            if total_colored == 0:
                values.append(100.0) 
            else:
                score = (n_green * 100.0 + n_yellow * 50.0 + n_red * 0.0) / total_colored
                values.append(round(min(100.0, max(0.0, score)), 1))
 
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