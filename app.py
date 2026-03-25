import streamlit as st
import google.generativeai as genai
from openai import OpenAI
from groq import Groq
import anthropic # Added for Claude integration
import pandas as pd
from PIL import Image
import sqlite3

st.set_page_config(page_title="End-to-End Inventory System", layout="wide")
#--- DATABASE SETUP ---
def init_db():
    # This creates a file named 'shop_data.db' in your folder. 
    # If it already exists, it just connects to it.
    import sqlite3
    conn = sqlite3.connect('shop_data.db')
    c = conn.cursor()
    
    # Create an INVENTORY table
    c.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            item_name TEXT,
            category TEXT,
            quantity REAL,
            unit_price REAL,
            total REAL,
            payment_mode TEXT
        )
    ''')
    
    # Create a SALES table
    c.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            item_name TEXT,
            category TEXT,
            quantity REAL,
            unit_price REAL,
            total REAL,
            payment_mode TEXT
        )
    ''')

    # --- NEW: Create a SUPPLIERS table ---
    c.execute('''
        CREATE TABLE IF NOT EXISTS suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier_name TEXT,
            item_name TEXT,
            price_per_unit REAL,
            distance_km REAL,
            contact_info TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

# Run this function every time the app starts
init_db()
# ----------------------

# --- 1. MULTI-PROVIDER AUTHENTICATION & DISCOVERY ---
st.sidebar.title("🔐 System Access")

# Provider Selection - Updated with Anthropic
provider = st.sidebar.selectbox("🌐 Choose AI Provider:", ["Google Gemini", "Groq (Llama - High Speed)", "OpenAI (GPT)", "Anthropic (Claude)"])

# Dynamic Help Notes for Users
if provider == "Google Gemini":
    st.sidebar.info("💡 **Note:** You need a **Google AI Studio API Key**.")
    st.sidebar.caption("[Get Gemini Key here](https://aistudio.google.com/app/apikey)")
elif provider == "Groq (Llama - High Speed)":
    st.sidebar.info("💡 **Note:** Groq is 10x faster for large CSV processing.")
    st.sidebar.caption("[Get Groq Key here](https://console.groq.com/keys)")
elif provider == "OpenAI (GPT)":
    st.sidebar.info("💡 **Note:** You need an **OpenAI Platform API Key**.")
    st.sidebar.caption("[Get OpenAI Key here](https://platform.openai.com/api-keys)")
elif provider == "Anthropic (Claude)":
    st.sidebar.info("💡 **Note:** Claude is the 'Reasoning King'—perfect for complex math.")
    st.sidebar.caption("[Get Anthropic Key here](https://console.anthropic.com/)")

api_key = st.sidebar.text_input(f"Enter {provider} API Key", type="password")
model_instance = None

if api_key:
    # --- GOOGLE GEMINI DISCOVERY ---
    if provider == "Google Gemini":
        genai.configure(api_key=api_key)
        try:
            gemini_models = [m.name.split('/')[-1] for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            selected_model = st.sidebar.selectbox("🧠 Select Discovered Model:", gemini_models)
            model_instance = genai.GenerativeModel(selected_model)
        except Exception as e:
            st.sidebar.error("❌ Invalid Gemini Key or Connection Error.")

    # --- GROQ DISCOVERY ---
    elif provider == "Groq (Llama - High Speed)":
        client = Groq(api_key=api_key)
        try:
            raw_models = client.models.list()
            groq_list = [m.id for m in raw_models.data if 'llama' in m.id or 'mixtral' in m.id]
            selected_model = st.sidebar.selectbox("🧠 Select Discovered Model:", sorted(groq_list))
            
            class GroqWrapper:
                def __init__(self, client, name): self.client, self.name = client, name
                def generate_content(self, contents):
                    res = self.client.chat.completions.create(model=self.name, messages=[{"role": "user", "content": str(contents)}])
                    class Resp: 
                        def __init__(self, t): self.text = t
                    return Resp(res.choices[0].message.content)
            model_instance = GroqWrapper(client, selected_model)
        except Exception as e:
            st.sidebar.error("❌ Invalid Groq Key or Connection Error.")

    # --- OPENAI DISCOVERY ---
    elif provider == "OpenAI (GPT)":
        client = OpenAI(api_key=api_key)
        try:
            raw_models = client.models.list()
            gpt_models = [m.id for m in raw_models if 'gpt' in m.id]
            selected_model = st.sidebar.selectbox("🧠 Select Discovered Model:", sorted(gpt_models))
            
            class OpenAIWrapper:
                def __init__(self, client, name): self.client, self.name = client, name
                def generate_content(self, contents):
                    res = self.client.chat.completions.create(model=self.name, messages=[{"role": "user", "content": str(contents)}])
                    class Resp: 
                        def __init__(self, t): self.text = t
                    return Resp(res.choices[0].message.content)
            model_instance = OpenAIWrapper(client, selected_model)
        except Exception as e:
            st.sidebar.error("❌ Invalid OpenAI Key or Connection Error.")

    # --- ANTHROPIC (CLAUDE) INTEGRATION ---
    elif provider == "Anthropic (Claude)":
        try:
            client = anthropic.Anthropic(api_key=api_key)
            claude_models = ["claude-3-5-sonnet-latest", "claude-3-5-haiku-latest", "claude-3-opus-latest"]
            selected_model = st.sidebar.selectbox("🧠 Select Claude Model:", claude_models)
            
            class ClaudeWrapper:
                def __init__(self, client, name):
                    self.client = client
                    self.name = name
                def generate_content(self, contents):
                    # Convert input format to Claude's message structure
                    res = self.client.messages.create(
                        model=self.name,
                        max_tokens=2048,
                        messages=[{"role": "user", "content": str(contents)}]
                    )
                    class Resp: 
                        def __init__(self, t): self.text = t
                    return Resp(res.content[0].text)
            model_instance = ClaudeWrapper(client, selected_model)
        except Exception as e:
            st.sidebar.error("❌ Invalid Anthropic Key or Connection Error.")

# --- 2. THE ERROR-HANDLING WRAPPER ---
def safe_generate(prompt_data):
    """Executes AI call and catches Quota/Resource errors."""
    if not model_instance:
        st.error("Please enter a valid API Key and select a model in the sidebar.")
        return None
    try:
        return model_instance.generate_content(prompt_data)
    except Exception as e:
        err_msg = str(e).lower()
        if any(x in err_msg for x in ["429", "resource_exhausted", "insufficient_quota", "rate_limit", "overloaded"]):
            st.error("🚨 **AI Provider Busy or Limit Reached!**")
            st.warning("Please switch to another model or provider in the sidebar.")
        else:
            st.error(f"⚠️ AI Connection Error: {e}")
        return None

if api_key:
    # --- MEMORY INITIALIZATION ---
    if 'all_sales' not in st.session_state:
        st.session_state['all_sales'] = "" 
    if 'all_inventory' not in st.session_state:
        st.session_state['all_inventory'] = ""
    if 'temp_stock' not in st.session_state:
        st.session_state['temp_stock'] = None
    if 'temp_sales' not in st.session_state:
        st.session_state['temp_sales'] = None
    if 'temp_rc' not in st.session_state:
        st.session_state['temp_rc'] = None

    # --- NAVIGATION ---
    st.sidebar.divider()
    mode = st.sidebar.radio("Select Action:", [
        "📈 Daily Sales (Out)", 
        "📦 Add New Stock (In)", 
        "📊 Inventory Dashboard", 
        "🔮 Weekly Sales Forecast",
        "📑 Smart Procurement (Rate Cards)" # <--- Updated this line
    ])

    # --- ADMINISTRATIVE RESET SWITCH ---
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

    # --- NEW: DEVELOPER SIMULATION BUTTON ---
    if st.sidebar.button("🧪 Run 30-Day Kirana Simulation", help="Injects 30 days of fake data for testing."):
        import random
        from datetime import datetime, timedelta
        import sqlite3

        with st.spinner("Building time machine and generating 30 days of data..."):
            try:
                conn = sqlite3.connect('shop_data.db')
                c = conn.cursor()
                
                # Wipe old test data
                c.execute("DELETE FROM inventory")
                c.execute("DELETE FROM sales")
                
                catalog = [
                    ("Aashirvaad Atta 5kg", "Grains", 180, 210),
                    ("Fortune Sunflower Oil 1L", "Grocery", 110, 135),
                    ("Tata Salt 1kg", "Grocery", 18, 24),
                    ("Maggi 140g", "Grocery", 22, 28),
                    ("Surf Excel Matic 1kg", "Household", 170, 205),
                    ("Amul Butter 100g", "Dairy", 45, 54),
                    ("Parle-G 250g", "Snacks", 20, 25),
                    ("Red Label Tea 250g", "Grocery", 120, 140),
                    ("Sugar 1kg", "Grocery", 38, 42),
                    ("Lifebuoy Soap", "Personal Care", 25, 30)
                ]
                
                start_date = datetime.now() - timedelta(days=30)
                
                # Buy initial stock
                for item in catalog:
                    name, category, buy_price, _ = item
                    qty = random.randint(50, 200)
                    c.execute('''INSERT INTO inventory (date, item_name, category, quantity, unit_price, total, payment_mode)
                                 VALUES (?, ?, ?, ?, ?, ?, ?)''', 
                              (start_date.strftime("%Y-%m-%d"), name, category, qty, buy_price, qty * buy_price, 'Cash'))
                              
                # Simulate 30 days of sales with occasional Udhari
                payment_methods = ['UPI', 'Cash', 'UPI', 'Cash', 'Credit (Udhari)']
                
                for day_offset in range(30):
                    current_date = start_date + timedelta(days=day_offset)
                    date_str = current_date.strftime("%Y-%m-%d")
                    is_weekend = current_date.weekday() >= 5
                    num_transactions = random.randint(15, 30) if is_weekend else random.randint(5, 15)
                    
                    for _ in range(num_transactions):
                        item = random.choice(catalog)
                        name, category, _, sell_price = item
                        qty_sold = random.randint(1, 3)
                        pay_mode = random.choice(payment_methods)
                        c.execute('''INSERT INTO sales (date, item_name, category, quantity, unit_price, total, payment_mode)
                                     VALUES (?, ?, ?, ?, ?, ?, ?)''', 
                                  (date_str, name, category, qty_sold, sell_price, qty_sold * sell_price, pay_mode))

                conn.commit()
                conn.close()
                st.sidebar.success("✅ 30 Days of Kirana Data Injected!")
                st.rerun() # Refresh the screen to show the new data
            except Exception as e:
                st.sidebar.error(f"Error running simulation: {e}")
    # --- NEW: SUPPLIER SIMULATION BUTTON ---
    if st.sidebar.button("🏭 Generate Rate Cards", help="Injects 5 rival suppliers for testing."):
        import random
        import sqlite3

        with st.spinner("Generating rival supplier data..."):
            try:
                conn = sqlite3.connect('shop_data.db')
                c = conn.cursor()
                
                # Wipe old supplier data so we start fresh
                c.execute("DELETE FROM suppliers")
                
                # Our standard Kirana catalog (Base Prices)
                catalog = [
                    ("Aashirvaad Atta 5kg", 180), ("Fortune Sunflower Oil 1L", 110),
                    ("Tata Salt 1kg", 18), ("Maggi 140g", 22),
                    ("Surf Excel Matic 1kg", 170), ("Amul Butter 100g", 45),
                    ("Parle-G 250g", 20), ("Red Label Tea 250g", 120),
                    ("Sugar 1kg", 38), ("Lifebuoy Soap", 25)
                ]
                
                # 5 Rival Suppliers (Name, Distance, Min Multiplier, Max Multiplier)
                # We give them different pricing strategies to test our math later!
                suppliers_list = [
                    ("Raju Traders", 3.0, 0.98, 1.05),
                    ("Metro Cash & Carry", 12.0, 0.92, 0.99), # Generally cheaper, but far
                    ("Gupta Wholesale", 1.5, 0.99, 1.08),     # Close, but expensive
                    ("Udaan B2B", 8.0, 0.95, 1.02),
                    ("Local Mandi", 5.0, 0.90, 1.00)          # Wildcard pricing
                ]
                
                # Generate the realistic prices
                for item_name, base_price in catalog:
                    for sup_name, dist, min_var, max_var in suppliers_list:
                        sup_price = round(base_price * random.uniform(min_var, max_var), 2)
                        
                        c.execute('''INSERT INTO suppliers (supplier_name, item_name, price_per_unit, distance_km, contact_info) 
                                     VALUES (?, ?, ?, ?, ?)''', 
                                  (sup_name, item_name, sup_price, dist, f"orders@{sup_name.replace(' ', '').lower()}.in"))
                                  
                conn.commit()
                conn.close()
                st.sidebar.success("✅ 5 Fake Rate Cards Injected!")
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"Error generating suppliers: {e}")

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
                    stock_system_prompt = """You are an Inventory Specialist. Extract the data and output ONLY a raw JSON array of objects.
                    Each object MUST have these exact keys: "date", "item_name", "category", "quantity", "unit_price", "total", "payment_mode".
                    
                    RULES:
                    1. Output ONLY valid JSON. Do NOT wrap it in ```json or include any conversational text.
                    2. Normalization: Standard English names.
                    3. Categories: [Grocery, Dairy, Personal Care, Household, Grains].
                    4. quantity, unit_price, and total MUST be numbers, not strings.
                    """
                    if stock_option == 'Image/PDF of Purchase Bill' and uploaded_stock_file:
                        img = Image.open(uploaded_stock_file)
                        response = safe_generate([stock_system_prompt, img])
                    else:
                        response = safe_generate([stock_system_prompt, stock_data_to_process])
                    
                    if response:
                        st.session_state['temp_stock'] = response.text
            else:
                st.warning("Please provide stock data first.")

        if st.session_state['temp_stock']:
            st.divider()
            st.subheader("📋 Review Extracted Stock")
            st.markdown(st.session_state['temp_stock'])
            if st.button("💾 Save to Database"):
                try:
                    import json # We use this to read the AI's JSON output
                    import sqlite3
                    
                    # 1. Read the JSON data from the AI
                    items = json.loads(st.session_state['temp_stock'])
                    
                    # 2. Open the Database we created in Step 1
                    conn = sqlite3.connect('shop_data.db')
                    c = conn.cursor()
                    
                    # 3. Loop through the AI's data and insert it into the database rows
                    for item in items:
                        c.execute('''INSERT INTO inventory (date, item_name, category, quantity, unit_price, total, payment_mode)
                                     VALUES (?, ?, ?, ?, ?, ?, ?)''', 
                                  (item.get('date', 'Today'), item.get('item_name', 'Unknown'), 
                                   item.get('category', 'Other'), item.get('quantity', 0), 
                                   item.get('unit_price', 0), item.get('total', 0), item.get('payment_mode', 'Cash')))
                    
                    # 4. Save and close
                    conn.commit()
                    conn.close()
                    
                    # 5. Clear temporary memory and refresh the screen
                    st.session_state['temp_stock'] = None
                    st.success("✅ Stock permanently saved to the Database!")
                    st.rerun()
                    
                except Exception as e:
                    # If the AI messes up the format, we catch the error here so the app doesn't crash
                    st.error(f"❌ Error saving to database. The AI didn't format the JSON correctly. Error: {e}")

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
                    sales_system_prompt = """You are a Sales Specialist. Extract the transaction data and output ONLY a raw JSON array of objects.
                    Each object MUST have these exact keys: "date", "item_name", "category", "quantity", "unit_price", "total", "payment_mode".
                    
                    RULES:
                    1. Output ONLY valid JSON. Do NOT wrap it in ```json or include any conversational text.
                    2. Normalization: Standard English names.
                    3. Categories: [Grocery, Dairy, Personal Care, Household, Grains].
                    4. quantity, unit_price, and total MUST be numbers, not strings.
                    """
                    if sales_option == 'Image/PDF of Paper Records' and uploaded_sales_file:
                        img = Image.open(uploaded_sales_file)
                        response = safe_generate([sales_system_prompt, img])
                    else:
                        response = safe_generate([sales_system_prompt, sales_data_to_process])
                    
                    if response:
                        st.session_state['temp_sales'] = response.text
            else:
                st.warning("Please provide sales data first.")

        if st.session_state['temp_sales']:
            st.divider()
            st.subheader("✅ Extracted Sales Data (Preview)")
            st.markdown(st.session_state['temp_sales'])
            if st.button("💾 Save to Database"):
                try:
                    import json 
                    import sqlite3
                    
                    # 1. Read the JSON data from the AI
                    items = json.loads(st.session_state['temp_sales'])
                    
                    # 2. Open the Database
                    conn = sqlite3.connect('shop_data.db')
                    c = conn.cursor()
                    
                    # 3. Insert into the SALES table (Notice it says 'sales' here, not 'inventory')
                    for item in items:
                        c.execute('''INSERT INTO sales (date, item_name, category, quantity, unit_price, total, payment_mode)
                                     VALUES (?, ?, ?, ?, ?, ?, ?)''', 
                                  (item.get('date', 'Today'), item.get('item_name', 'Unknown'), 
                                   item.get('category', 'Other'), item.get('quantity', 0), 
                                   item.get('unit_price', 0), item.get('total', 0), item.get('payment_mode', 'Cash')))
                    
                    # 4. Save and close
                    conn.commit()
                    conn.close()
                    
                    # 5. Clear temporary memory
                    st.session_state['temp_sales'] = None
                    st.success("✅ Sales permanently saved to the Database!")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Error saving to database. The AI didn't format the JSON correctly. Error: {e}")

    # --- MODE: DASHBOARD 
    elif mode == "📊 Inventory Dashboard":
        st.header("📊 Real-Time Inventory & Financial Dashboard")
        
        import sqlite3
        import pandas as pd
        
        try:
            # 1. Connect to database and load data directly into Pandas DataFrames
            conn = sqlite3.connect('shop_data.db')
            df_inventory = pd.read_sql_query("SELECT * FROM inventory", conn)
            df_sales = pd.read_sql_query("SELECT * FROM sales", conn)
            conn.close()
            
            if df_inventory.empty:
                st.warning("No inventory data found in the database. Please add stock first.")
            else:
                # 2. Python does the exact math (No AI Hallucinations!)
                st.subheader("📦 Accurate Inventory Status")
                
                # Group inventory by item_name to get total quantity bought
                in_summary = df_inventory.groupby('item_name')['quantity'].sum().reset_index()
                in_summary.rename(columns={'quantity': 'Total_In'}, inplace=True)
                
                # Group sales by item_name to get total quantity sold
                out_summary = pd.DataFrame(columns=['item_name', 'Total_Out']) # Default empty just in case
                if not df_sales.empty:
                    out_summary = df_sales.groupby('item_name')['quantity'].sum().reset_index()
                    out_summary.rename(columns={'quantity': 'Total_Out'}, inplace=True)
                
                # Merge them together to find remaining stock
                dashboard_df = pd.merge(in_summary, out_summary, on='item_name', how='left').fillna(0)
                dashboard_df['Remaining_Stock'] = dashboard_df['Total_In'] - dashboard_df['Total_Out']
                
                # 3. Display the exact numbers in a clean Streamlit table
                st.dataframe(dashboard_df, use_container_width=True)
                
                # 4. Calculate and show Top-Level Financial Metrics
                st.divider()
                st.subheader("💰 Financial Overview")
                
                total_investment = df_inventory['total'].sum()
                total_revenue = df_sales['total'].sum() if not df_sales.empty else 0
                
                # --- NEW: CALCULATE UDHARI (CREDIT) ---
                total_credit = 0
                if not df_sales.empty:
                    # Filter for 'credit' or 'udhari' (case-insensitive search)
                    credit_mask = df_sales['payment_mode'].str.contains('credit|udhari', case=False, na=False)
                    total_credit = df_sales.loc[credit_mask, 'total'].sum()
                
                # Streamlit metrics are great for high-level KPIs
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Total Investment", f"₹{total_investment:,.2f}")
                col2.metric("Total Revenue", f"₹{total_revenue:,.2f}")
                col3.metric("Current Balance", f"₹{(total_revenue - total_investment):,.2f}")
                # Show Udhari in red!
                col4.metric("🚨 Pending Udhari", f"₹{total_credit:,.2f}")

        except Exception as e:
            st.error(f"❌ Error loading dashboard: {e}")

    # --- MODE: WEEKLY SALES FORECAST (THE AGENT) ---
    elif mode == "🔮 Weekly Sales Forecast":
        st.header("🔮 Smart Sales Forecast & Restock Agent")
        st.info("📊 Mathematical forecast generated instantly (Zero API Cost).")
        
        if 'latest_email' not in st.session_state:
            st.session_state['latest_email'] = None
            
        import sqlite3
        import pandas as pd
        
        conn = sqlite3.connect('shop_data.db')
        df_inventory = pd.read_sql_query("SELECT * FROM inventory", conn)
        df_sales = pd.read_sql_query("SELECT * FROM sales", conn)
        conn.close()
        
        if df_inventory.empty or df_sales.empty:
            st.warning("Please add both stock and sales data to run the AI Agent.")
        else:
            with st.spinner("Calculating Kirana Intuition Math..."):
                # 1. Total Inventory In
                in_summary = df_inventory.groupby('item_name')['quantity'].sum().reset_index()
                in_summary.rename(columns={'quantity': 'Total_In'}, inplace=True)
                
                # 2. Advanced Sales Math (Recency Bias)
                df_sales['date'] = pd.to_datetime(df_sales['date'])
                latest_date = df_sales['date'].max()
                cutoff_date = latest_date - pd.Timedelta(days=7)
                
                # Get total out AND last 7 days out
                out_total = df_sales.groupby('item_name')['quantity'].sum().reset_index()
                out_recent = df_sales[df_sales['date'] >= cutoff_date].groupby('item_name')['quantity'].sum().reset_index()
                
                # Merge sales stats
                sales_stats = pd.merge(out_total, out_recent, on='item_name', how='left', suffixes=('_total', '_7d')).fillna(0)
                
                # 3. The "Kirana Intuition" Formula
                # Velocity = (70% weight to recent week) + (30% weight to older history)
                sales_stats['hist_vel'] = (sales_stats['quantity_total'] - sales_stats['quantity_7d']) / 23 # approx 23 older days
                sales_stats['recent_vel'] = sales_stats['quantity_7d'] / 7
                
                sales_stats['Blended_Daily_Velocity'] = (sales_stats['recent_vel'] * 0.70) + (sales_stats['hist_vel'] * 0.30)
                
                # Next 7 Days Demand + 15% Safety Stock
                sales_stats['Projected_7D_Demand'] = (sales_stats['Blended_Daily_Velocity'] * 7 * 1.15).round(0)
                
                # 4. Merge with Inventory to find what to order
                df_agent = pd.merge(in_summary, sales_stats, on='item_name', how='left').fillna(0)
                df_agent['Remaining_Stock'] = df_agent['Total_In'] - df_agent['quantity_total']
                df_agent['Suggested_Order_Qty'] = df_agent['Projected_7D_Demand'] - df_agent['Remaining_Stock']
                df_agent['Suggested_Order_Qty'] = df_agent['Suggested_Order_Qty'].clip(lower=0) # No negative orders
                
                # 5. Format a beautiful table for the user to see instantly
                display_df = df_agent[['item_name', 'Remaining_Stock', 'Projected_7D_Demand', 'Suggested_Order_Qty']].copy()
                display_df.columns = ['Item Name', 'Current Stock', 'Expected Demand (Next 7D)', 'Qty to Order']
                
            # --- THE TRANSPARENT UI ---
            st.subheader("📋 Data-Driven Restock Recommendation")
            st.dataframe(display_df, use_container_width=True)
            
            items_to_order = display_df[display_df['Qty to Order'] > 0]
            
            st.divider()
            st.subheader("🤖 AI Communication Agent")
            st.caption("Let the AI draft emails to your suppliers based on the table above.")
            
            # The API is gated behind this button!
            if st.button("🚀 Draft Supplier Emails (Uses AI)"):
                with st.spinner('Agent is drafting emails...'):
                    try:
                        exact_data_str = items_to_order.to_string(index=False)
                        
                        agent_prompt = f"""
                        You are an Autonomous Supply Chain Agent. 
                        Our backend Python engine has calculated exactly what needs to be ordered for the next 7 days.
                        
                        CRITICAL REORDER DATA:
                        {exact_data_str if not items_to_order.empty else "NO ITEMS NEED REORDERING."}
                        
                        YOUR MISSION:
                        1. If the data says "NO ITEMS NEED REORDERING", simply output: "🟢 Stock levels are healthy. No orders needed."
                        2. If there is data, output ONLY a markdown report with this section:
                           
                           ### 📧 Automated Purchase Order Drafts
                           (Write professional email/WhatsApp templates to the suppliers to place the order for these EXACT quantities. You can group items logically if you want. Leave [Blank] for the supplier names).
                        
                        RULES:
                        - NEVER change the 'Qty to Order' numbers.
                        - Do not explain the math, just write the emails.
                        """
                        
                        agent_response = safe_generate(agent_prompt)
                        
                        if agent_response:
                            st.session_state['latest_email'] = agent_response.text
                            st.success("✅ Emails Drafted!")
                            
                    except Exception as e:
                        st.error(f"❌ Agent encountered an error: {e}")

            if st.session_state['latest_email']:
                st.markdown(st.session_state['latest_email'])
    # --- MODE: SMART PROCUREMENT (RATE CARDS) ---
    elif mode == "📑 Smart Procurement (Rate Cards)":
        st.header("📑 Upload Supplier Rate Cards")
        st.info("Upload your supplier rate cards one by one. You can add up to 5 suppliers.")
        # --- NEW: CLEAR DATA BUTTON ---
        if st.button("🗑️ Clear All Saved Rate Cards"):
            try:
                import sqlite3
                conn = sqlite3.connect('shop_data.db')
                c = conn.cursor()
                c.execute("DELETE FROM suppliers")
                conn.commit()
                conn.close()
                st.success("✅ All supplier rate cards have been permanently deleted!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error clearing data: {e}")

        # 1. Global Transport Cost Setting
        st.subheader("🚚 Transport Setting")
        if 'transport_rate' not in st.session_state:
            st.session_state['transport_rate'] = 2.0
        st.session_state['transport_rate'] = st.number_input("Transport Cost (₹ per km per kg/unit)", value=st.session_state['transport_rate'], step=0.5)

        # 2. Supplier Details
        st.divider()
        st.subheader("1. Supplier Details")
        col1, col2 = st.columns(2)
        supplier_name = col1.text_input("Supplier Name", placeholder="e.g., Raju Traders")
        distance_km = col2.number_input("Distance from Shop (km)", value=5.0, step=0.5)

        st.divider()
        st.subheader("2. Upload Rate Data")

        # 3. The exact same UI pattern as Inventory/Sales
        rc_option = st.selectbox(
            'How are you uploading this rate card?',
            ('Manual Text Entry', 'Image/PDF of Rate Card', 'Excel/CSV Spreadsheet')
        )

        rc_data_to_process = None
        uploaded_rc_file = None

        if rc_option == 'Manual Text Entry':
            rc_data_to_process = st.text_area("Paste Rate Card Items:", height=150, placeholder="Example: Sugar 40, Maggi 22...")
        elif rc_option == 'Image/PDF of Rate Card':
            uploaded_rc_file = st.file_uploader("Upload Rate Card Photo/PDF", type=['png', 'jpg', 'jpeg', 'pdf'])
            if uploaded_rc_file:
                st.image(uploaded_rc_file, caption="Rate Card Preview", width=300)
        elif rc_option == 'Excel/CSV Spreadsheet':
            digital_rc_file = st.file_uploader("Upload Digital Rate Card", type=['csv', 'xlsx'])
            if digital_rc_file:
                import pandas as pd
                df_rc = pd.read_csv(digital_rc_file) if digital_rc_file.name.endswith('csv') else pd.read_excel(digital_rc_file)
                st.write("Preview of Digital Rate Card:")
                st.dataframe(df_rc.head())
                rc_data_to_process = df_rc.to_string()

        # 4. Extract Button
        if st.button("🔍 Extract Rate Card"):
            if not supplier_name:
                st.warning("⚠️ Please enter a Supplier Name at the top first!")
            elif rc_data_to_process or uploaded_rc_file:
                with st.spinner('AI is extracting prices...'):
                    rc_prompt = """You are a Procurement Agent. Extract the items and prices from this rate card.
                    Output ONLY a raw JSON array of objects.
                    Keys MUST be exactly: "item_name", "price_per_unit".
                    RULES:
                    1. Output ONLY valid JSON. Do not wrap in markdown.
                    2. Normalization: Standard English names (e.g. "Sugar", "Atta").
                    3. Make sure prices are raw numbers, not strings.
                    """
                    try:
                        if rc_option == 'Image/PDF of Rate Card' and uploaded_rc_file:
                            from PIL import Image
                            img = Image.open(uploaded_rc_file)
                            response = safe_generate([rc_prompt, img])
                        else:
                            response = safe_generate([rc_prompt, rc_data_to_process])

                        if response:
                            st.session_state['temp_rc'] = response.text
                            st.session_state['temp_sup_name'] = supplier_name
                            st.session_state['temp_dist'] = distance_km
                    except Exception as e:
                        st.error(f"Error during AI extraction: {e}")
            else:
                st.warning("Please provide rate card data first.")

        # 5. Preview and Save
        if st.session_state.get('temp_rc'):
            st.divider()
            st.subheader("✅ Extracted Prices (Preview)")
            st.markdown(st.session_state['temp_rc'])

            if st.button("💾 Save to Supplier Database"):
                try:
                    import json
                    import sqlite3

                    items = json.loads(st.session_state['temp_rc'])
                    conn = sqlite3.connect('shop_data.db')
                    c = conn.cursor()

                    # Delete old prices from this specific supplier to prevent duplicates
                    c.execute("DELETE FROM suppliers WHERE supplier_name = ?", (st.session_state['temp_sup_name'],))

                    for item in items:
                        c.execute('''INSERT INTO suppliers (supplier_name, item_name, price_per_unit, distance_km, contact_info)
                                     VALUES (?, ?, ?, ?, ?)''',
                                  (st.session_state['temp_sup_name'], item.get('item_name', 'Unknown'),
                                   float(item.get('price_per_unit', 0)), st.session_state['temp_dist'], "WhatsApp"))

                    conn.commit()
                    conn.close()

                    st.session_state['temp_rc'] = None
                    st.success(f"✅ {st.session_state['temp_sup_name']} saved successfully!")
                    st.rerun()

                except Exception as e:
                    st.error(f"❌ Error saving to database. Ensure AI formatted JSON correctly. Error: {e}")
            # --- 6. PROCUREMENT DASHBOARD ---
        st.divider()
        st.header("🏆 Procurement Dashboard")

        try:
            import pandas as pd
            import sqlite3

            # 1. Read the saved data from the database
            conn = sqlite3.connect('shop_data.db')
            df_suppliers = pd.read_sql_query("SELECT * FROM suppliers", conn)
            conn.close()

            # 2. Display the Dashboard if we have data
            if not df_suppliers.empty:
                st.subheader("📊 Price Comparison Matrix")
                st.caption("Green highlights the cheapest rate for each item.")
                
                # Create a table comparing all suppliers side-by-side
                pivot_df = df_suppliers.pivot_table(index='item_name', columns='supplier_name', values='price_per_unit', aggfunc='min')
                st.dataframe(pivot_df.style.highlight_min(axis=1, color='lightgreen'), use_container_width=True)

                st.divider()
                st.subheader("📦 Smart Order List (Cheapest Options)")
                st.info("Here is exactly what you should buy from each supplier to save the most money.")
                
                # Find the absolute lowest price for each item using Python math
                cheapest_items = df_suppliers.loc[df_suppliers.groupby('item_name')['price_per_unit'].idxmin()]
                
                # Group those winning items by the supplier
                grouped_orders = cheapest_items.groupby('supplier_name')

                # Display a clean list for each supplier
                for supplier, items in grouped_orders:
                    with st.expander(f"🛒 Order from: {supplier}", expanded=True):
                        display_df = items[['item_name', 'price_per_unit']].copy()
                        display_df.columns = ['Item Name', 'Rate (₹)']
                        st.dataframe(display_df, hide_index=True)
            else:
                st.info("📭 No rate cards saved yet. Use the form above to add some!")

        except Exception as e:
            st.error(f"⚠️ Error loading dashboard: {e}")
    #7. FINAL ORDER GENERATION (THE BRIDGE) ---
        st.divider()
        st.header("🚀 Final Step: Smart Purchase Orders")
        st.info("Automatically merging your Weekly Forecast with your Cheapest Suppliers.")
        
        try:
            import pandas as pd
            import sqlite3
            import urllib.parse
            
            conn = sqlite3.connect('shop_data.db')
            df_inv = pd.read_sql_query("SELECT * FROM inventory", conn)
            df_sal = pd.read_sql_query("SELECT * FROM sales", conn)
            df_sup = pd.read_sql_query("SELECT * FROM suppliers", conn)
            conn.close()
            
            # We need all three pieces of data to do this math
            if df_inv.empty or df_sal.empty or df_sup.empty:
                st.warning("⚠️ Need Inventory, Sales, AND Supplier data to generate final orders.")
            else:
                #  FORECAST MATH (Syncing the exact "Kirana Intuition" logic from the Forecast tab)
                in_summary = df_inv.groupby('item_name')['quantity'].sum().reset_index()
                in_summary.rename(columns={'quantity': 'Total_In'}, inplace=True)
                
                # Calculate Recency Bias
                df_sal['date'] = pd.to_datetime(df_sal['date'])
                latest_date = df_sal['date'].max()
                cutoff_date = latest_date - pd.Timedelta(days=7)
                
                out_total = df_sal.groupby('item_name')['quantity'].sum().reset_index()
                out_recent = df_sal[df_sal['date'] >= cutoff_date].groupby('item_name')['quantity'].sum().reset_index()
                
                sales_stats = pd.merge(out_total, out_recent, on='item_name', how='left', suffixes=('_total', '_7d')).fillna(0)
                
                # The "Kirana Intuition" Formula
                sales_stats['hist_vel'] = (sales_stats['quantity_total'] - sales_stats['quantity_7d']) / 23
                sales_stats['recent_vel'] = sales_stats['quantity_7d'] / 7
                sales_stats['Blended_Daily_Velocity'] = (sales_stats['recent_vel'] * 0.70) + (sales_stats['hist_vel'] * 0.30)
                sales_stats['Demand_7D'] = (sales_stats['Blended_Daily_Velocity'] * 7 * 1.15).round(0)
                
                # Merge and find final Qty_to_Order
                df_forecast = pd.merge(in_summary, sales_stats, on='item_name', how='left').fillna(0)
                df_forecast['Remaining'] = df_forecast['Total_In'] - df_forecast['quantity_total']
                df_forecast['Qty_to_Order'] = (df_forecast['Demand_7D'] - df_forecast['Remaining']).clip(lower=0)
                
                # Filter out items we don't need to buy
                items_needed = df_forecast[df_forecast['Qty_to_Order'] > 0]
                
                if items_needed.empty:
                    st.success("🟢 Your stock levels are perfectly healthy! No orders needed this week.")
                else:
                    # 2. THE MATHEMATICAL FIX: LANDED COST
                    # Get the transport rate from the UI
                    t_rate = st.session_state.get('transport_rate', 2.0)
                    
                    # Calculate the TRUE cost of the item: Base Price + (Distance * Transport Rate)
                    df_sup['landed_cost'] = df_sup['price_per_unit'] + (df_sup['distance_km'] * t_rate)
                    
                    # NOW we find the cheapest supplier based on the Landed Cost!
                    cheapest_idx = df_sup.groupby('item_name')['landed_cost'].idxmin()
                    cheapest_sup = df_sup.loc[cheapest_idx]
                    
                    # 3. THE BRIDGE (Merge needed items with TRUE cheapest suppliers)
                    final_orders = pd.merge(items_needed, cheapest_sup, on='item_name', how='inner')
                    
                    if final_orders.empty:
                        st.warning("You need to restock items, but your uploaded suppliers don't sell them!")
                    else:
                        st.subheader("🛒 Your Actionable Orders")
                        
                        # Group by supplier to bundle orders together
                        grouped_final = final_orders.groupby('supplier_name')
                        
                        for supplier, items in grouped_final:
                            dist = items.iloc[0]['distance_km']
                            trip_cost = dist * t_rate
                            
                            with st.expander(f"📦 Send Order to {supplier} (Distance: {dist}km)", expanded=True):
                                # Show the exact quantities and the TRUE math
                                display_df = items[['item_name', 'Qty_to_Order', 'price_per_unit', 'landed_cost']].copy()
                                display_df.columns = ['Item Name', 'Qty Needed', 'Base Rate (₹)', 'True Landed Cost (₹)']
                                st.dataframe(display_df, hide_index=True)
                                
                                # --- 4. GENERATE DEEP LINKS WITH EXACT QUANTITIES ---
                                order_text = f"Hello {supplier},\n\nPlease prepare the following order for pickup:\n\n"
                                for _, row in items.iterrows():
                                    order_text += f"- {int(row['Qty_to_Order'])} units of {row['item_name']}\n"
                                order_text += "\nThank you!"
                                
                                encoded_text = urllib.parse.quote(order_text)
                                wa_url = f"https://wa.me/?text={encoded_text}"
                                gmail_url = f"mailto:{items.iloc[0]['contact_info']}?subject=New%20Restock%20Order&body={encoded_text}"
                                
                                c1, c2 = st.columns(2)
                                c1.link_button("💬 Send via WhatsApp", wa_url, use_container_width=True)
                                c2.link_button("📧 Send via Gmail", gmail_url, use_container_width=True)
                                
        except Exception as e:
            st.error(f"⚠️ Error generating final orders: {e}")
else:
    st.warning("Please enter your API Key to begin.")
