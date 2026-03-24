import streamlit as st
import google.generativeai as genai
import pandas as pd
from PIL import Image

st.set_page_config(page_title="End-to-End Inventory System", layout="wide")

# --- AUTHENTICATION ---
st.sidebar.title("🔐 System Access")
user_key = st.sidebar.text_input("Enter Gemini API Key", type="password")

if user_key:
    genai.configure(api_key=user_key)
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    # --- NAVIGATION ---
    st.sidebar.divider()
    mode = st.sidebar.radio("Select Action:", ["📈 Daily Sales (Out)", "📦 Add New Stock (In)", "📊 Inventory Dashboard"])

    # We use 'session_state' to keep a simple 'database' in memory for today
    if 'inventory' not in st.session_state:
        st.session_state['inventory'] = {} # Format: {"Item": Quantity}

    if mode == "📦 Add New Stock (In)":
        st.header("Add Inventory to Warehouse")
        stock_input = st.text_area("List items purchased (e.g., 'Bought 50kg Sugar @ 38/kg')")
        if st.button("Update Stock Baseline"):
            # AI Task: Extract Item and Qty and add to session_state
            prompt = f"Extract items and quantities as a Python dictionary from: {stock_input}. Return ONLY the dictionary."
            res = model.generate_content(prompt)
            st.success(f"Stock Updated! Raw Data: {res.text}")
            # In the next step, we will make this 'math' real.

    elif mode == "📈 Daily Sales (Out)":
        st.header("Record Daily Transactions")
        # --- EXISTING UPLOAD LOGIC ---
        option = st.selectbox('Source:', ('Manual Entry', 'Image/PDF'))
        uploaded_file = st.file_uploader("Upload", type=['png', 'jpg', 'jpeg'])
        
        if st.button("🛠️ Process Sales & Calculate Balance"):
            # This is where we will link Sales to Inventory in Phase 7
            st.info("Processing sales and subtracting from stock...")

    elif mode == "📊 Inventory Dashboard":
        st.header("Real-Time Inventory Status")
        st.write("Current Stock Levels will appear here once we link the math.")
        # We will build a table here showing [Item | Starting | Sold | Remaining]

else:
    st.warning("Please enter your API Key to begin.")
