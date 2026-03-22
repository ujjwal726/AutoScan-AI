import streamlit as st
import pandas as pd
import google.generativeai as genai
import io
import json
from PIL import Image

# --- CONFIGURATION & SETUP ---
st.set_page_config(page_title="WealthTrace AI", page_icon="📈", layout="wide")
st.title("📈 WealthTrace AI")
st.markdown("### The Zero-Trust Opportunity Cost Engine")

# --- AUTHENTICATION & DYNAMIC MODEL SELECTION ---
model = None
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = st.sidebar.text_input("Enter Gemini API Key", type="password")

if api_key:
    genai.configure(api_key=api_key)
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        target_model = 'gemini-1.5-flash'
        if 'models/gemini-1.5-flash' not in available_models and available_models:
            target_model = available_models[0].replace('models/', '')
        
        model = genai.GenerativeModel(target_model)
        st.sidebar.success(f"🟢 Secured Connection: {target_model}")
    except Exception as e:
        st.sidebar.error(f"Connection Error: {e}")
else:
    st.sidebar.warning("API Key required for the AI modules.")

# --- NAVIGATION TABS ---
tab1, tab2, tab3 = st.tabs(["📸 1. Secure Ledger Upload", "🧠 2. The Wealth Engine", "🛑 3. Pre-Spend Interceptor"])

# ==========================================
# TAB 1: DATA INGESTION
# ==========================================
with tab1:
    st.header("Step 1: Digitize Your Paper Ledger")
    st.error("🔒 **ZERO-TRUST PROTOCOL:** Hand-written paper notes only. No bank statements.")
    
    with st.container(border=True):
        st.markdown("**📝 Format Example:** 12-March | Zomato (Burger) | 450")
        
    photo_file = st.file_uploader("Upload Photo (JPG/PNG)", type=["jpg", "jpeg", "png"])
    
    if photo_file and model:
        image = Image.open(photo_file)
        st.image(image, caption="Your Secure Ledger", width=500)
        
        if st.button("Extract Data", type="primary"):
            with st.spinner("Digitizing handwriting..."):
                try:
                    vision_prompt = "Extract transactions. Output ONLY raw CSV format with columns: Date, Description, Amount. No markdown or headers."
                    response = model.generate_content([vision_prompt, image])
                    clean_csv_text = response.text.replace("```csv\n", "").replace("```", "").strip()
                    df_vision = pd.read_csv(io.StringIO(clean_csv_text))
                    
                    # Ensure minimal columns exist
                    df_vision["Tag"] = "Uncategorized"
                    df_vision["Context"] = ""
                    
                    st.success("✅ Ledger Digitized!")
                    st.dataframe(df_vision)
                    
                    csv_buffer = io.StringIO()
                    df_vision.to_csv(csv_buffer, index=False)
                    st.download_button("⬇️ Download Clean CSV for Step 2", data=csv_buffer.getvalue(), file_name="secure_expenses.csv", mime="text/csv")
                except Exception as e:
                    st.error(f"Handwriting Extraction Error: {e}")

# ==========================================
# TAB 2: THE WEALTH ENGINE (V1.7.2 RE-STABILIZED)
# ==========================================
with tab2:
    st.header("Step 2: Tag & Analyze")
    clean_file = st.file_uploader("Upload Digitized Data (CSV)", type=["csv"], key="clean_upload")
    
    if clean_file:
        # Load and verify file
        if "final_df" not in st.session_state or st.session_state.get("active_file") != clean_file.name:
            df = pd.read_csv(clean_file)
            
            # 1. Clean data basics and handle numeric conversion
            if "Amount" in df.columns:
                df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
            
            for col in ["Tag", "Context"]:
                if col not in df.columns:
                    df[col] = "" if col == "Context" else "Uncategorized"
            
            # 2. Stable Auto-Tagging
            if model and "Description" in df.columns:
                with st.spinner("✨ AI is analyzing your transactions..."):
                    try:
                        desc_list = df['Description'].astype(str).tolist()
                        tag_prompt = f"""
                        Categorize each item in this list into exactly one category: Need, Desire, Salary, Income.
                        Items: {desc_list}
                        Return your response as a JSON list of strings only.
                        Example: ["Need", "Desire", "Salary"]
                        """
                        res_text = model.generate_content(tag_prompt).text
                        # Extract JSON list even if AI adds extra text
                        start_idx = res_text.find('[')
                        end_idx = res_text.rfind(']') + 1
                        tags = json.loads(res_text[start_idx:end_idx])
                        
                        # Apply tags with strict length matching
                        if len(tags) == len(df):
                            df['Tag'] = [t.title() if t.title() in ["Need", "Desire", "Salary", "Income"] else "Uncategorized" for t in tags]
                    except:
                        df['Tag'] = "Uncategorized"
            
            st.session_state.final_df = df
            st.session_state.active_file = clean_file.name

        st.subheader("1. Financial Triage & Clarification")
        
        # Display the editor safely
        edited_df = st.data_editor(
            st.session_state.final_df,
            key="v1.7.2_editor",
            column_config={
                "Tag": st.column_config.SelectboxColumn("Tag", options=["Need", "Desire", "Salary", "Income", "Uncategorized"], required=True),
                "Context": st.column_config.TextColumn("Context (Optional)", help="Explain large or unusual expenses here.")
            },
            use_container_width=True
        )
        
        # Math Section
        if "Amount" in edited_df.columns:
            edited_df['Amount'] = pd.to_numeric(edited_df['Amount'], errors='coerce').fillna(0)
            desires = edited_df[edited_df["Tag"] == "Desire"]
            total_desire = desires["Amount"].sum()
            
            st.divider()
            col1, col2 = st.columns(2)
            col1.metric("Monthly 'Desire' Leakage", f"₹{total_desire:,.2f}")
            
            # Simple SIP FV calculation (12% annual / 1% monthly)
            sip_fv = total_desire * (((1.01)**12 - 1) / 0.01) * 1.01
            col2.metric("1-Year SIP Wealth Potential", f"₹{sip_fv:,.2f}", delta=f"Profit: ₹{sip_fv - (total_desire*12):,.0f}")
            
            if st.button("Generate Strategy Report", type="primary") and model:
                with st.spinner("Analyzing market rates and behavioral patterns..."):
                    csv_data = edited_df[['Description', 'Amount', 'Tag', 'Context']].to_csv(index=False)
                    report_prompt = f"""
                    Analyze this spending data for an Indian user:
                    {csv_data}
                    
                    Total Desire Spend: ₹{total_desire}
                    1-Year SIP Potential: ₹{sip_fv:,.2f}
                    
                    Provide a report with:
                    1. Financial Wins (Praise the user)
                    2. Market Rate Warnings (Flag exorbitant prices, check 'Context' for justifications)
                    3. Micro-Opportunity Cost Table (3 crisp Indian alternatives for each 'Desire')
                    4. 1-Year Tangible Goal (What they can buy with the SIP wealth)
                    5. Behavioral Verdict (Identify spending triggers & health risks)
                    """
                    try:
                        st.markdown(model.generate_content(report_prompt).text)
                    except Exception as e:
                        st.error(f"Analysis Error: {e}")

# ==========================================
# TAB 3: THE INTERCEPTOR
# ==========================================
with tab3:
    st.header("Step 3: Pre-Spend Interceptor")
    item_name = st.text_input("Product Name (e.g., iPhone, Fancy Watch)")
    item_price = st.number_input("Price (₹)", min_value=0, step=100)
    if st.button("Evaluate Purchase", type="primary") and model and item_price > 0:
        st.error(f"🛑 10-Year Opportunity Cost (12% CAGR): ₹{item_price * (1.12**10):,.2f}")
        st.markdown(model.generate_content(f"Item: {item_name}, Price: {item_price}. Give 2 Indian investments and 1 psychological question.").text)
