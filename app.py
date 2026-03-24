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
    model = genai.GenerativeModel('gemini-2.5-pro')
    
    # --- NEW: MEMORY INITIALIZATION (Waiting Room & Master Ledgers) ---
    if 'all_sales' not in st.session_state:
        st.session_state['all_sales'] = "" 
    if 'all_inventory' not in st.session_state:
        st.session_state['all_inventory'] = ""
    if 'temp_stock' not in st.session_state:
        st.session_state['temp_stock'] = None
    if 'temp_sales' not in st.session_state:
        st.session_state['temp_sales'] = None

    # --- NAVIGATION ---
    st.sidebar.divider()
    mode = st.sidebar.radio("Select Action:", ["📈 Daily Sales (Out)", "📦 Add New Stock (In)", "📊 Inventory Dashboard"])

    # --- NEW: ADMINISTRATIVE RESET SWITCH ---
    st.sidebar.divider()
    st.sidebar.subheader("⚠️ Administrative Actions")
    if st.sidebar.button("🗑️ Reset All Data", help="Permanently delete all saved Stock and Sales records."):
        st.session_state['all_sales'] = ""
        st.session_state['all_inventory'] = ""
        st.session_state['temp_stock'] = None
        st.session_state['temp_sales'] = None
        st.sidebar.success("System Reset Successful!")
        st.rerun()

    if 'inventory' not in st.session_state:
        st.session_state['inventory'] = {} 

    # --- MODE: STOCK IN ---
    if mode == "📦 Add New Stock (In)":
        st.header("📦 Inventory Intake (Stock-In)")
        st.info("Record new purchases or initial stock levels here.")

        stock_option = st.selectbox(
            'How are you recording this stock?',
            ('Manual Text Entry', 'Image/PDF of Purchase Bill', 'Excel/CSV Stock Sheet')
        )

        stock_data_to_process = None
        uploaded_stock_file = None

        if stock_option == 'Manual Text Entry':
            stock_data_to_process = st.text_area("List Items Purchased:", height=150, placeholder="Example: Bought 100kg Sugar at 40/kg, 50L Oil at 140/L...")
        elif stock_option == 'Image/PDF of Purchase Bill':
            uploaded_stock_file = st.file_uploader("Upload Bill/Invoice Photo", type=['png', 'jpg', 'jpeg', 'pdf'])
            if uploaded_stock_file:
                st.image(uploaded_stock_file, caption="Inward Bill Preview", width=300)
        elif stock_option == 'Excel/CSV Stock Sheet':
            digital_stock_file = st.file_uploader("Upload Stock Spreadsheet", type=['csv', 'xlsx'])
            if digital_stock_file:
                df_stock = pd.read_csv(digital_stock_file) if digital_stock_file.name.endswith('csv') else pd.read_excel(digital_stock_file)
                st.write("Preview of Digital Stock:")
                st.dataframe(df_stock.head())
                stock_data_to_process = df_stock.to_string()

        if st.button("🔍 Extract & Check Stock"):
            if stock_data_to_process or uploaded_stock_file:
                with st.spinner('AI is processing inward stock...'):
                    stock_system_prompt = """
                    You are an Inventory and Sales Specialist. Convert input into a Markdown Table.
                    Columns: [Item Name, Category, Quantity, Unit Price, Total, Type, Payment Mode].
                    Rules: 
                    1. Normalization: Standard English names.
                    2. Categories: [Grocery, Dairy, Personal Care, Household, Grains].
                    3. Type: Set to 'IN'.
                    4. Payment Mode: Use 'CASH' or 'CREDIT' (if Udhari/Baki).
                    """
                    if stock_option == 'Image/PDF of Purchase Bill' and uploaded_stock_file:
                        img = Image.open(uploaded_stock_file)
                        response = model.generate_content([stock_system_prompt, img])
                    else:
                        response = model.generate_content([stock_system_prompt, stock_data_to_process])
                    
                    st.session_state['temp_stock'] = response.text
            else:
                st.warning("Please provide stock data first.")

        if st.session_state['temp_stock']:
            st.divider()
            st.subheader("📋 Review Extracted Stock")
            st.markdown(st.session_state['temp_stock'])
            if st.button("💾 Save to Master Inventory"):
                st.session_state['all_inventory'] += "\n" + st.session_state['temp_stock']
                st.session_state['temp_stock'] = None 
                st.success("Stock saved successfully!")
                st.rerun()

    # --- MODE: SALES OUT ---
    elif mode == "📈 Daily Sales (Out)":
        st.header("Record Daily Transactions (Sales Out)")
        
        sales_option = st.selectbox(
            'How are you recording today\'s sales?',
            ('Manual Text Entry', 'Image/PDF of Paper Records', 'Excel/CSV Spreadsheet')
        )

        sales_data_to_process = None
        uploaded_sales_file = None

        if sales_option == 'Manual Text Entry':
            sales_data_to_process = st.text_area("Paste Sales Ledger:", height=150, placeholder="Example: Sugar 5kg, Oil 2L...")
        elif sales_option == 'Image/PDF of Paper Records':
            uploaded_sales_file = st.file_uploader("Upload photo/PDF of sales", type=['png', 'jpg', 'jpeg', 'pdf'])
            if uploaded_sales_file:
                st.image(uploaded_sales_file, caption="Sales Record Preview", width=300)
        elif sales_option == 'Excel/CSV Spreadsheet':
            digital_sales_file = st.file_uploader("Upload digital sales file", type=['csv', 'xlsx'])
            if digital_sales_file:
                df_sales = pd.read_csv(digital_sales_file) if digital_sales_file.name.endswith('csv') else pd.read_excel(digital_sales_file)
                st.write("Preview of Digital Sales:")
                st.dataframe(df_sales.head())
                sales_data_to_process = df_sales.to_string()

        if st.button("🔍 Extract & Check Sales"):
            if sales_data_to_process or uploaded_sales_file:
                with st.spinner('AI is extracting transaction data...'):
                    sales_system_prompt = """
                    You are an Inventory and Sales Specialist. Convert input into a Markdown Table.
                    Columns: [Item Name, Category, Quantity, Unit Price, Total, Type, Payment Mode].
                    Rules: 
                    1. Normalization: Standard English names.
                    2. Categories: [Grocery, Dairy, Personal Care, Household, Grains].
                    3. Type: Set to 'OUT'.
                    4. Payment Mode: Use 'CASH' or 'CREDIT' (if Udhari/Baki).
                    """
                    if sales_option == 'Image/PDF of Paper Records' and uploaded_sales_file:
                        img = Image.open(uploaded_sales_file)
                        response = model.generate_content([sales_system_prompt, img])
                    else:
                        response = model.generate_content([sales_system_prompt, sales_data_to_process])
                    
                    st.session_state['temp_sales'] = response.text
            else:
                st.warning("Please provide sales data first.")

        if st.session_state['temp_sales']:
            st.divider()
            st.subheader("✅ Extracted Sales Data (Preview)")
            st.markdown(st.session_state['temp_sales'])
            if st.button("💾 Save to Sales Ledger"):
                st.session_state['all_sales'] += "\n" + st.session_state['temp_sales']
                st.session_state['temp_sales'] = None
                st.success("Sales record saved successfully!")
                st.rerun()

    # --- MODE: DASHBOARD (Enhanced Audit Edition) ---
    elif mode == "📊 Inventory Dashboard":
        st.header("📊 Real-Time Inventory & Financial Dashboard")
        
        if not st.session_state['all_inventory'] and not st.session_state['all_sales']:
            st.warning("No data found. Please add verified Stock or Sales first.")
        else:
            with st.spinner('Calculating totals and auditing records...'):
                calculation_prompt = f"""
                You are a Senior Retail Auditor. Use these ledgers:
                INVENTORY: {st.session_state['all_inventory']}
                SALES: {st.session_state['all_sales']}
                
                OUTPUT RULES:
                1. All monetary values must be in Rupees (₹).
                2. You MUST follow this EXACT format:

                ### 📦 Inventory Status
                | Item Name | Category | Total In | Total Out | Remaining | Current Value (₹) |
                | :--- | :--- | :--- | :--- | :--- | :--- |
                | [Item] | [Cat] | [Qty] | [Qty] | [Qty] | [₹ Total] |

                ### 🚩 Financial Audit & Udhari
                - **Total Investment:** ₹[Amount]
                - **Total Potential Revenue:** ₹[Amount]
                - **Actual Cash in Hand:** ₹[Amount]
                - **Total Udhari (Outstanding Credit):** ₹[Amount]
                
                ### 🚀 Business Insights
                - **Fastest Moving Item:** [Name]
                - **Top Debtor:** [Name/Details]
                
                3. Do not add any conversational text before or after the tables.
                """
                
                calc_response = model.generate_content(calculation_prompt)
                
                st.success("Analysis Complete!")
                st.markdown(calc_response.text)
        
        st.divider()
        with st.expander("View Raw Saved Ledgers"):
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("📦 Master Inventory (IN)")
                st.markdown(st.session_state['all_inventory'] if st.session_state['all_inventory'] else "Empty")
            with col2:
                st.subheader("📉 Master Sales (OUT)")
                st.markdown(st.session_state['all_sales'] if st.session_state['all_sales'] else "Empty")

else:
    st.warning("Please enter your API Key to begin.")
