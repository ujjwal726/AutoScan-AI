import streamlit as st
import google.generativeai as genai
from openai import OpenAI
from groq import Groq
import anthropic # Added for Claude integration
import pandas as pd
from PIL import Image

st.set_page_config(page_title="End-to-End Inventory System", layout="wide")

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

    # --- NAVIGATION ---
    st.sidebar.divider()
    mode = st.sidebar.radio("Select Action:", ["📈 Daily Sales (Out)", "📦 Add New Stock (In)", "📊 Inventory Dashboard", "🔮 Weekly Sales Forecast"])

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
                    stock_system_prompt = """You are an Inventory Specialist. Convert input into a Markdown Table.
                    Columns: [Date, Item Name, Category, Quantity, Unit Price, Total, Type, Payment Mode].

                    RULES:
                    1. Output ONLY the markdown table. 
                    2. DO NOT include any introductory text, explanations, or Python code blocks.
                    3. Normalization: Standard English names.
                    4. Categories: [Grocery, Dairy, Personal Care, Household, Grains].
                    5. Type: Set to 'IN'
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
                    sales_system_prompt = """You are a Sales Specialist. Convert input into a Markdown Table.
                    Columns: [Date, Item Name, Category, Quantity, Unit Price, Total, Type, Payment Mode].

                    RULES:
                    1. Output ONLY the markdown table. 
                    2. DO NOT include any introductory text, explanations, or Python code blocks.
                    3. Normalization: Standard English names.
                    4. Categories: [Grocery, Dairy, Personal Care, Household, Grains].
                    5. Type: Set to 'OUT'
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
            if st.button("💾 Save to Sales Ledger"):
                st.session_state['all_sales'] += "\n" + st.session_state['temp_sales']
                st.session_state['temp_sales'] = None
                st.success("Sales record saved successfully!")
                st.rerun()

    # --- MODE: DASHBOARD ---
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
                
                calc_response = safe_generate(calculation_prompt)
                
                if calc_response:
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

    # --- MODE: WEEKLY SALES FORECAST ---
    elif mode == "🔮 Weekly Sales Forecast":
        st.header("🔮 AI Sales & Inventory Forecast (Next 7 Days)")
        
        if not st.session_state['all_sales']:
            st.warning("Please upload sales data first to predict the future.")
        else:
            with st.spinner('AI is simulating market demand for next week...'):
                prediction_prompt = f"""
                You are a Senior Supply Chain Data Scientist and Retail Coach. 
                TODAY'S DATE: March 24, 2026.
                
                DATA:
                SALES: {st.session_state['all_sales']}
                STOCK: {st.session_state['all_inventory']}
                
                STRICT MATHEMATICAL INSTRUCTIONS:
                1. Calculate Weighted Velocity (Vw): (Avg sales of last 3 days * 0.7) + (Avg sales of previous 4 days * 0.3).
                2. Calculate Momentum Factor (M): (Avg sales of last 2 days / Avg sales of first 5 days).
                3. Calculate Volatility Buffer (SS): If daily sales variance is > 30%, add a 40% safety stock. Otherwise, add 15%.
                4. Projected 7-Day Demand (D7): (Vw * 7 * M) + SS.
                5. Net Purchase Requirement: D7 - Current On-Hand Stock.
                
                OUTPUT RULES FOR LAYMAN:
                - Convert these complex results into a 'Simple Shopkeeper View'.
                - Use 'Traffic Light' Status (🔴 Critical/Out soon, 🟡 Order soon, 🟢 Healthy).
                - Use plain English for 'Why' (e.g., 'Demand is spiking fast' or 'Stock is clearing slow').
                
                OUTPUT FORMAT:
                ### 🔮 Professional 7-Day Forecast & Order Guide
                | Item Name | Status | Recommendation(Buy Quantity) | Why this? |
                | :--- | :--- | :--- | :--- |
                | [Item] | [🔴/🟡/🟢] | **[Buy Qty]** | [Reasoning in plain English] |

                ### 🚦 Inventory Runway
                - **Critical Stock-Out Alert:** [List items running out in < 48 hours]
                - **The 'Cash-Cow' (Most Profitable Item):** [Identify highest margin/velocity item]
                
                ### 💡 AI Shop Strategy
                Provide one 'High-Impact' retail tip (e.g., 'Bundle Sugar with Tea this week as both are trending up together').
                
                RULES:
                - DO NOT show the math formulas in the output.
                - Output ONLY the markdown sections.
                - If Net Purchase is < 0, recommend 0.
                """
                forecast_res = safe_generate(prediction_prompt)
                
                if forecast_res:
                    st.success("7-Day Forecast Ready!")
                    st.markdown(forecast_res.text)

else:
    st.warning("Please enter your API Key to begin.")
