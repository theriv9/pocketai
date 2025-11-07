import streamlit as st


def main():
    # === RECEIPT UPLOAD ===
    uploaded_file = st.file_uploader("📸 Upload a receipt photo", type=["jpg", "jpeg", "png"])

    if uploaded_file:
        with st.spinner("Scanning receipt..."):
            st.image(uploaded_file, caption="Your Receipt")

if __name__ == "__main__":
    main()