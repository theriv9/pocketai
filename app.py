
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
from datetime import date

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
    '    {{"name": "string", "price": 0.0, "category": "Beverage|House Items|Transport|Groceries|Other"}}\n'
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


        # Connect to account
        client = CosmosClient(os.getenv("COSMOS_ENDPOINT"), os.getenv("COSMOS_KEY"))

        # CREATE DATABASE
        db = client.create_database_if_not_exists(id="PocketAI_DB")
        print("DATABASE 'PocketAI_DB' READY!")

        # REMOVE offer_throughput FOR SERVERLESS
        container = db.create_container_if_not_exists(
            id="Receipts",
            partition_key=PartitionKey(path="/id")
        )

        print("CONTAINER 'Receipts' READY!")
        count_query = "SELECT VALUE COUNT(1) FROM c"
        count_results = list(container.query_items(query=count_query, enable_cross_partition_query=True))
        total_receipts = count_results[0] if count_results else 0
        # === SAVE ===
        parsed["id"] = f"receipt_{total_receipts + 1}"
        receipt_date = result.documents[0].fields.get("TransactionDate")
        parsed["date"] = receipt_date.value.strftime("%Y-%m-%d") if receipt_date and receipt_date.value else "Unknown"
        container.upsert_item(parsed)
        st.success(f"SAVED ID: {parsed['id']} | {parsed.get('merchant', 'N/A')} – ${parsed.get('total', 0):.2f} on {parsed['date']}")

      # === QUERY: Total Receipts + Category Spend (COSMOS DB SAFE) ==
        # === TOTAL RECEIPTS ===
        count_query = "SELECT VALUE COUNT(1) FROM c"
        count_results = list(container.query_items(query=count_query, enable_cross_partition_query=True))
        total_receipts = count_results[0] if count_results else 0

        # === CATEGORY SPEND ===
        def get_category_total(cat):
            q = f"SELECT VALUE SUM(item.price) FROM c JOIN item IN c.items WHERE item.category = '{cat}'"
            results = list(container.query_items(query=q, enable_cross_partition_query=True))
            return results[0] if results else 0.0

        stats = {
            "total_receipts": total_receipts,
            "Beverage": get_category_total("Beverage"),
            "House Items": get_category_total("House Items"),
            "Transport": get_category_total("Transport"),
            "Groceries": get_category_total("Groceries"),
            "Other": get_category_total("Other")
        }


        # === DISPLAY ===
        st.success(f"SAVED: {parsed.get('merchant', 'N/A')} – ${parsed.get('total', 0):.2f}")

        st.write(f"**Total Receipts**: {stats.get('total_receipts', 0)}")

        st.write("**Spending by Category**:")
        categories = [
            ("Beverage", stats.get("beverage_total", 0)),
            ("House Items", stats.get("house_items_total", 0)),
            ("Transport", stats.get("transport_total", 0)),
            ("Groceries", stats.get("groceries_total", 0)),
            ("Other", stats.get("other_total", 0))
        ]
        # for cat, total in categories:
        #     st.write(f"  • **{cat}**: ${total:.2f}")



        #     query = """
        #     SELECT VALUE SUM(item.price) 
        #     FROM c 
        #     JOIN item IN c.items 
        #     WHERE item.category = 'Other'
        #     """
        #     results = list(container.query_items(query=query, enable_cross_partition_query=True))
        #     other_total = results[0] if results else 0.0
        #     st.write(f"OTHER SPEND: ${other_total:.2f}")
        # === LOOP THROUGH ALL CATEGORIES ===
        categories = ["Beverage", "House Items", "Transport", "Groceries", "Other"]

        for cat in categories:
            query = f"""
            SELECT VALUE SUM(item.price)
            FROM c
            JOIN item IN c.items
            WHERE item.category = '{cat}'
            """
            results = list(container.query_items(query=query, enable_cross_partition_query=True))
            total = results[0] if results else 0.0
            st.write(f"**{cat}**: ${total:.2f}")