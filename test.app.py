import streamlit as st
from pages import scan
# === PRO LAYOUT ===
st.set_page_config(layout="wide", page_title="PocketAI", page_icon="🧾")

# Header
col1, col2 = st.columns([1, 4])
with col1:
    #st.image("logo.png", width=80)  # add a 200×200 logo later
    st.caption("T")
with col2:
    st.title("PocketAI – AI Receipt Scanner")
    st.caption("by Ruben | Entry-level AI Engineer | NZ")

# Sidebar navigation
with st.sidebar:
    st.header("Navigation")
    page = st.radio("Go to", ["📸 Scan", "📊 Dashboard", "⚙️ Categories", "ℹ️ About"])

# === PAGE ROUTING ===
if page == "📸 Scan":
    # your existing upload + OCR + save code
    st.header("SCAN RECEIPT")
    scan.main()
elif page == "📊 Dashboard":
    st.header("Monthly Spending")
    # bar chart + totals

elif page == "⚙️ Categories":
    st.header("Manage Categories")
    # data_editor + save button

else:
    st.header("About")
    st.write("Built with Azure OCR + GPT-4o-mini + Cosmos DB")
    st.video("https://loom.com/share/your-link")