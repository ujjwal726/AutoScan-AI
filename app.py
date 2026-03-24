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
        st.header("Record Daily Transactions (Sales Out)")
        
        # 1. Select the Input Method
        sales_option = st.selectbox(
            'How are you recording today\'s sales?',
            ('Manual Text Entry', 'Image/PDF of Paper Records', 'Excel/CSV Spreadsheet')
        )

        sales_data_to_process = None
        uploaded_sales_file = None

        # 2. Handle the 3 Input Options
        if sales_option == 'Manual Text Entry':
            sales_data_to_process = st.text_area("Paste Sales Ledger:", height=150, placeholder="Example: Sugar 5kg, Oil 2L...")

        elif sales_option == 'Image/PDF of Paper Records':
            uploaded_sales_file = st.file_uploader("Upload photo/PDF of sales", type=['png', 'jpg', 'jpeg', 'pdf'])
            if uploaded_sales_file:
                st.image(uploaded_sales_file, caption="Sales Record Preview", width=300)
                # We pass the image object directly to the AI later

        elif sales_option == 'Excel/CSV Spreadsheet':
            digital_sales_file = st.file_uploader("Upload digital sales file", type=['csv', 'xlsx'])
            if digital_sales_file:
                df_sales = pd.read_csv(digital_sales_file) if digital_sales_file.name.endswith('csv') else pd.read_excel(digital_sales_file)
                st.write("Preview of Digital Sales:")
                st.dataframe(df_sales.head())
                sales_data_to_process = df_sales.to_string()

        # 3. The Extraction Engine (The Brain)
        if st.button("🚀 Extract & Show Sales Table"):
            if sales_data_to_process or uploaded_sales_file:
                with st.spinner('AI is extracting transaction data...'):
                    sales_system_prompt = """
                    You are a Data Extraction Specialist for a retail shop. 
                    Convert the input into a clean Markdown Table.
                    Columns: Date, Item Name, Category, Quantity, Unit Price, Total, Payment Type (Cash/Credit).
                    Rules: 
                    1. If 'Udhari' is mentioned, Payment Type is 'Credit'.
                    2. Normalize names (e.g., 'Tel' -> 'Oil', 'Sakhar' -> 'Sugar').
                    3. If an image is provided, perform OCR to find all line items.
                    """
                    
                    # Call the AI based on what was uploaded
                    if sales_option == 'Image/PDF of Paper Records' and uploaded_sales_file:
                        img = Image.open(uploaded_sales_file)
                        response = model.generate_content([sales_system_prompt, img])
                    else:
                        response = model.generate_content([sales_system_prompt, sales_data_to_process])

                    # 4. Display the "Extracted Sales"
                    st.divider()
                    st.subheader("✅ Extracted Sales Data")
                    st.markdown(response.text)
                    
                    # Store this in session_state so we can use it for 'Inventory Subtraction' next
                    st.session_state['latest_sales_table'] = response.text
            else:
                st.warning("Please provide sales data first.")
        
        if st.button("🛠️ Process Sales & Calculate Balance"):
            # This is where we will link Sales to Inventory in Phase 7
            st.info("Processing sales and subtracting from stock...")

    elif mode == "📊 Inventory Dashboard":
        st.header("Real-Time Inventory Status")
        st.write("Current Stock Levels will appear here once we link the math.")
        # We will build a table here showing [Item | Starting | Sold | Remaining]

else:
    st.warning("Please enter your API Key to begin.")
