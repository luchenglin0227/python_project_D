import streamlit as st

st.title("睡眠與情緒分析系統")

sleep_hours = st.slider(
    "今天睡了幾小時？",
    0,
    12,
    7
)

mood = st.selectbox(
    "今天心情如何？",
    ["開心", "普通", "焦慮", "疲憊"]
)

uploaded_file = st.file_uploader(
    "請上傳今天的照片",
    type=["jpg", "png", "jpeg"]
)

if uploaded_file:
    st.image(uploaded_file)

if st.button("開始分析"):
    st.write(f"睡眠時間：{sleep_hours}")
    st.write(f"心情：{mood}")

    if uploaded_file:
        st.success("照片已上傳！")
