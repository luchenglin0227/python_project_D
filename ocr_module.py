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
    return img, full_text, heat_scores,

def convert_pdf_to_img(file_bytes):
    """PDF 轉圖片邏輯"""
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    page = doc.load_page(0)
    pix = page.get_pixmap(dpi=300)
    return cv2.imdecode(np.frombuffer(pix.tobytes("png"), np.uint8), cv2.IMREAD_COLOR)

def analyze_heatmap_to_values(img):
    """【光譜數值映射版】將彩色像素映射為 0.0 - 100.0 的方位命中率"""
    h, w, _ = img.shape
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    lower_bound = np.array([0, 40, 40])
    upper_bound = np.array([100, 255, 255])
    color_mask = cv2.inRange(hsv, lower_bound, upper_bound)
    
    row_counts = np.sum(color_mask > 0, axis=1)
    search_start = int(h * 0.55)
    active_rows = np.where(row_counts[search_start:] > (w * 0.01))[0]
    
    if len(active_rows) > 0:
        y_start = search_start + active_rows[0] - 10
        y_end = search_start + active_rows[-1] + 10
    else:
        y_start, y_end = int(h * 0.63), int(h * 0.92)
        
    x_start, x_end = int(w * 0.06), int(w * 0.94)
    
    roi_hsv = hsv[y_start:y_end, x_start:x_end]
    roi_mask = color_mask[y_start:y_end, x_start:x_end]
    
    h_rows = np.array_split(roi_hsv, 3, axis=0)
    values = []
    
    for r_idx in range(3):
        h_cols = np.array_split(h_rows[r_idx], 3, axis=1)
        m_cols = np.array_split(np.array_split(roi_mask, 3, axis=0)[r_idx], 3, axis=1)
        
        for c_idx in range(3):
            cell_hsv = h_cols[c_idx]
            cell_mask = m_cols[c_idx]
            colored_pixels = cell_hsv[cell_mask > 0]
            
            if len(colored_pixels) == 0:
                values.append(100.0)
            else:
                avg_hue = np.mean(colored_pixels[:, 0])
                hit_rate = (avg_hue / 85.0) * 100
                hit_rate = max(0.0, min(100.0, hit_rate))
                values.append(round(hit_rate, 1))
                
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