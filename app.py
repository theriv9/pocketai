# app.py
import streamlit as st

st.set_page_config(page_title="PocketAI", page_icon="🧾")
st.title("🧾 PocketAI – AI Receipt Scanner")

# === UPLOAD PHOTO ===
uploaded_file = st.file_uploader("📸 Upload a receipt photo", type=["jpg", "jpeg", "png"])

if uploaded_file:
    st.image(uploaded_file, caption="Your Receipt")
    st.success("Photo uploaded! Ready for OCR.")