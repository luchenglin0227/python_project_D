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
    """【三色像素加權版】將彩色像素映射為 0.0 - 100.0 的方位命中率（綠色分數較高）"""
    """
    【高精準抗干擾版】
    1. 加強紅色極端值的捕捉能力
    2. 縮緊高位邊界，並引入微量像素過濾機制，防止光譜圖外框雜訊干擾
    """
    h_img, w_img, _ = img.shape
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)  # 轉換至 HSV 色彩空間進行顏色分析
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # ── 自動定位熱圖 ROI 的垂直範圍 ──
    # ── 自動定位熱圖 ROI ──
    mask_colored = cv2.inRange(hsv, np.array([0, 40, 40]), np.array([100, 255, 255]))
    row_counts   = np.sum(mask_colored > 0, axis=1)   # 每列的彩色像素數量
    search_start = int(h_img * 0.55)                  # 從圖片 55% 高度以下開始搜尋
    row_counts   = np.sum(mask_colored > 0, axis=1)
    search_start = int(h_img * 0.55)
    active_rows  = np.where(row_counts[search_start:] > (w_img * 0.01))[0]

    if len(active_rows) > 0:
        y_start = search_start + active_rows[0]  - 10
        # 【優化】高位（y_start）往內縮 5px 防止抓到上方的光譜圖邊框或文字
        y_start = search_start + active_rows[0]  + 5
        # 低位（y_end）維持向下延伸緩衝
        y_end   = search_start + active_rows[-1] + 10
        
        # 安全防護：確保範圍不超過圖片邊界
        y_start = max(0, y_start)
        y_end   = min(h_img, y_end)
    else:
        y_start, y_end = int(h_img * 0.63), int(h_img * 0.92)

    # 水平範圍：去除圖片左右各 6% 的邊框空白
    # 水平範圍：去除左右邊框
    x_start, x_end = int(w_img * 0.06), int(w_img * 0.94)
 
    # 擷取熱圖 ROI
    roi_hsv = hsv[y_start:y_end, x_start:x_end]

    # ── 建立三色獨立遮罩（在 ROI 範圍內）──
    # 紅色：HSV 色環首尾各一段，需分兩段建立再合併
    mask_red1  = cv2.inRange(roi_hsv, np.array([0,   60, 60]), np.array([15,  255, 255]))
    mask_red2  = cv2.inRange(roi_hsv, np.array([160, 60, 60]), np.array([180, 255, 255]))
    mask_red   = cv2.bitwise_or(mask_red1, mask_red2)   # 合併兩段紅色
    # ── 建立三色獨立遮罩（【優化】大幅增強紅色的捕捉寬容度）──
    # 紅色段 1：從 0~15 放寬到 0~18，飽和度/亮度從 60 下修到 30（抓取淡紅、深紅）
    mask_red1  = cv2.inRange(roi_hsv, np.array([0,   30, 30]), np.array([18,  255, 255]))
    # 紅色段 2：從 160~180 放寬到 155~180
    mask_red2  = cv2.inRange(roi_hsv, np.array([155, 30, 30]), np.array([180, 255, 255]))
    mask_red   = cv2.bitwise_or(mask_red1, mask_red2)

    # 綠色：Hue 35~85（涵蓋黃綠到純綠）
    mask_green  = cv2.inRange(roi_hsv, np.array([35, 60, 60]), np.array([85, 255, 255]))
    # 綠色段（同步放寬飽和度與亮度要求）
    mask_green  = cv2.inRange(roi_hsv, np.array([35, 30, 30]), np.array([85, 255, 255]))

    # 黃色：Hue 16~34（介於紅色與綠色之間）
    mask_yellow = cv2.inRange(roi_hsv, np.array([16, 60, 60]), np.array([34, 255, 255]))
    # 黃色段
    mask_yellow = cv2.inRange(roi_hsv, np.array([19, 30, 30]), np.array([34, 255, 255]))

    # ── 將 ROI 切割成 3×3 九宮格 ──
    # ── 切割九宮格 ──
    roi_rows_red    = np.array_split(mask_red,    3, axis=0)
    roi_rows_green  = np.array_split(mask_green,  3, axis=0)
    roi_rows_yellow = np.array_split(mask_yellow, 3, axis=0)

    values = []
    for r in range(3):   # 列：高(0) / 中(1) / 低(2)
        cols_red    = np.array_split(roi_rows_red[r],    3, axis=1)  # 沿水平方向切 3 欄
    for r in range(3):
        cols_red    = np.array_split(roi_rows_red[r],    3, axis=1)
        cols_green  = np.array_split(roi_rows_green[r],  3, axis=1)
        cols_yellow = np.array_split(roi_rows_yellow[r], 3, axis=1)

        for c in range(3):   # 欄：左(0) / 中(1) / 右(2)
            # 統計各色彩像素數量
        for c in range(3):
            n_red    = np.sum(cols_red[c]    > 0)
            n_green  = np.sum(cols_green[c]  > 0)
            n_yellow = np.sum(cols_yellow[c] > 0)
            
            # 【優化】抗噪機制：如果某個顏色在單一格子裡小於 5 個像素，視為光譜圖雜訊，直接歸零
            if n_red < 5:    n_red = 0
            if np.sum(cols_green[c] > 0) < 5:  n_green = 0
            if n_yellow < 5: n_yellow = 0
            
            total_colored = n_red + n_green + n_yellow

            if total_colored == 0:
                # 情況 1：此格無任何彩色像素 → 代表沒有任何失誤熱點，屬於完美狀態，直接填 100.0
                values.append(100.0)
                values.append(100.0)  # 無失誤熱點，完美狀態
            else:
                # 情況 2：調整加權權重，讓綠色拿最高分 (綠=100分，黃=50分，紅=0分)
                # 綠色像素越多，分數越接近 100.0；紅色像素越多，分數越接近 0.0
                # 綠色拿最高分 (綠=100分，黃=50分，紅=0分)
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