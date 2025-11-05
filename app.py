
# app.py
import streamlit as st
from openai import AzureOpenAI
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import PromptTemplate
from azure.cosmos import CosmosClient, PartitionKey
from dotenv import load_dotenv
import io
from PIL import Image
import json
import os
import re

# === LOAD .env FIRST ===
load_dotenv()

# === DEBUG: Check key loads ===
st.write("DEBUG: OpenAI Key loaded:", bool(os.getenv("AZURE_OPENAI_KEY")))

# === LLM ===
llm = AzureChatOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    api_version="2024-02-01",
    deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
    temperature=0.0
)

# === PROMPT ===
prompt = PromptTemplate.from_template(
    "Extract from this receipt:\n"
    "{raw_receipt}\n\n"
    "Return ONLY valid JSON (no extra text):\n"
    "```json\n"
    "{{\n"
    '  "merchant": "string",\n'
    '  "total": 0.0,\n'
    '  "items": [\n'
    '    {{"name": "string", "price": 0.0, "category": "Food|House Items|Transport|Groceries|Other"}}\n'
    "  ]\n"
    "}}\n"
    "```"
)

# === AZURE OCR CLIENT (ADD THIS) ===
ocr_client = DocumentAnalysisClient(
    endpoint=os.getenv("AZURE_FORM_RECOGNIZER_ENDPOINT"),
    credential=AzureKeyCredential(os.getenv("AZURE_FORM_RECOGNIZER_KEY"))
)

# === STREAMLIT UI ===
st.set_page_config(page_title="PocketAI", page_icon="🧾")
st.title("🧾 PocketAI – AI Receipt Scanner")

# === RECEIPT UPLOAD ===
uploaded_file = st.file_uploader("📸 Upload a receipt photo", type=["jpg", "jpeg", "png"])

if uploaded_file:
    with st.spinner("Scanning receipt..."):
        st.image(uploaded_file, caption="Your Receipt")

# == OCR
        poller = ocr_client.begin_analyze_document("prebuilt-receipt", uploaded_file.getvalue())
        result = poller.result()

        receipt = {"items": []}
        for item in result.documents[0].fields.get("Items", {}).value or []:
            desc_field = item.value.get("Description")
            name = desc_field.value if desc_field else "Unknown"

            price_field = item.value.get("Price") or item.value.get("TotalPrice")
            price = price_field.value if price_field else 0.0

            receipt["items"].append({"name": name, "price": price})

        st.success("OCR COMPLETE!")
        st.write("**Items Found**:")
        for item in receipt["items"]:
            st.write(f"  • {item['name']}: ${item['price']:.2f}")

        # == FORMAT FOR LLM# === LANGCHAIN ===
        raw_output = llm.invoke(prompt.format(raw_receipt=str(receipt))).content

        # Extract JSON
        match = re.search(r"```json\s*(\{.*?\})\s*```", raw_output, re.DOTALL)
        parsed = json.loads(match.group(1)) if match else receipt

        st.success("CATEGORIZED!")
        st.write("**Items**:")
        for item in parsed["items"]:
            st.write(f"  • {item['name']} → **{item['category']}** → ${item['price']:.2f}")
