import streamlit as st
import pandas as pd
import google.generativeai as genai
import io
from PIL import Image

# --- CONFIGURATION ---
st.set_page_config(page_title="WealthTrace AI", page_icon="📈", layout="wide")
st.title("📈 WealthTrace AI")
st.markdown("### The Zero-Trust Opportunity Cost Engine")

# --- AUTHENTICATION & DYNAMIC MODEL FINDER ---
model = None
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = st.sidebar.text_input("Enter Gemini API Key", type="password")

if api_key:
    genai.configure(api_key=api_key)
    try:
        # THE DYNAMIC MODEL FINDER: We return to the logic that worked!
        # It asks the API: "What models do you have?" and picks the right one.
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        if 'models/gemini-1.5-flash' in available_models:
            target_model = 'gemini-1.5-flash'
        elif 'models/gemini-1.5-flash-latest' in available_models:
            target_model = 'gemini-1.5-flash-latest'
        elif 'models/gemini-pro-vision' in available_models:
            target_model = 'gemini-pro-vision'
        else:
            # Fallback to the first available content-generating model
            target_model = available_models[0].replace('models/', '')
            
        model = genai.GenerativeModel(target_model)
        st.sidebar.success(f"🟢 Secured Connection: {target_model}")
    except Exception as e:
        st.sidebar.error(f"Model Discovery Error: {e}")
else:
    st.sidebar.warning("API Key required to run the AI Wealth Engine.")
    st.stop()

# --- NAVIGATION TABS ---
tab1, tab2, tab3 = st.tabs(["📸 1. Secure Ledger Upload", "🧠 2. The Wealth Engine", "🛑 3. Pre-Spend Interceptor"])

# ==========================================
# TAB 1: SECURE UPLOAD (HANDWRITTEN ONLY)
# ==========================================
with tab1:
    st.header("Step 1: Digitize Your Paper Ledger")
    st.error("🔒 **ZERO-TRUST PROTOCOL:** Hand-written paper notes only. We do not want your official bank data.")
    
    with st.container(border=True):
        st.markdown("**📝 Format Example:** 12-March | Zomato (Burger) | 450")
        
    photo_file = st.file_uploader("Upload Photo of Handwritten Ledger (JPG/PNG)", type=["jpg", "jpeg", "png"])
    
    if photo_file:
        image = Image.open(photo_file)
        st.image(image, caption="Your Secure Ledger", width=500)
        
        if st.button("Extract Data", type="primary"):
            with st.spinner("Digitizing handwriting..."):
                try:
                    vision_prompt = "Extract transactions. Output ONLY raw CSV format with columns: Date, Description, Amount. Do not include headers or markdown."
                    response = model.generate_content([vision_prompt, image])
                    clean_csv_text = response.text.replace("```csv\n", "").replace("```", "").strip()
                    df_vision = pd.read_csv(io.StringIO(clean_csv_text), names=["Date", "Description", "Amount"])
                    
                    st.success("✅ Ledger Digitized Successfully!")
                    st.dataframe(df_vision)
                    
                    csv_buffer = io.StringIO()
                    df_vision.to_csv(csv_buffer, index=False)
                    st.download_button("⬇️ Download Clean CSV for Step 2", data=csv_buffer.getvalue(), file_name="secure_expenses.csv", mime="text/csv")
                except Exception as e:
                    st.error(f"Handwriting Extraction Error: {e}")

# ==========================================
# TAB 2: THE WEALTH ENGINE (WITH CONTEXT & PRAISE)
# ==========================================
with tab2:
    st.header("Step 2: Tag & Analyze")
    st.write("Upload the clean CSV you just downloaded from Step 1.")
    clean_file = st.file_uploader("Upload Digitized Data (CSV)", type=["csv"], key="w_up")
    
    if clean_file:
        df = pd.read_csv(clean_file)
        
        # Ensure critical columns exist
        if "Amount" in df.columns:
            df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
        if "Tag" not in df.columns: df["Tag"] = "Uncategorized"
        if "Context" not in df.columns: df["Context"] = ""

        st.subheader("1. Financial Triage & Clarification")
        st.info("💡 Review the tags. Add a note in **'Context'** for large expenses (e.g., 'Parents Anniversary Gift') to defend the purchase to the AI.")
        
        edited_df = st.data_editor(
            df,
            column_config={
                "Tag": st.column_config.SelectboxColumn("Tag", options=["Need", "Desire", "Salary", "Income", "Uncategorized"], required=True),
                "Context": st.column_config.TextColumn("Context (Optional)")
            },
            use_container_width=True,
            key="final_stable_editor"
        )
        
        # Analysis calculations
        desires = edited_df[edited_df["Tag"] == "Desire"]
        total_desire = desires["Amount"].sum()
        sip_fv = total_desire * (((1.01)**12 - 1) / 0.01) * 1.01
        
        st.divider()
        c1, c2 = st.columns(2)
        c1.metric("Monthly 'Desire' Leakage", f"₹{total_desire:,.2f}")
        c2.metric("1-Year SIP Potential (12% CAGR)", f"₹{sip_fv:,.2f}")
        
        if st.button("Generate Strategy Report", type="primary"):
            with st.spinner("Analyzing market rates and behavioral patterns..."):
                csv_sum = edited_df[['Description', 'Amount', 'Tag', 'Context']].to_csv(index=False)
                final_report_prompt = f"""
                Analyze this Indian spending data:
                {csv_sum}
                
                Report Requirements:
                1. FINANCIAL WINS: Praise specific good choices (e.g., essential needs, income).
                2. MARKET WARNINGS: Flag exorbitant prices. IMPORTANT: Check the 'Context' column—if the user explained the purchase, validate it instead of warning them.
                3. MICRO-OPPORTUNITY COSTS: Table for 'Desire' items showing 3 crisp Indian alternatives (e.g., broadband, fuel, healthy food).
                4. SAVINGS GOAL: Suggest what tangible thing they can buy with ₹{sip_fv:,.2f} in 1 year.
                5. BEHAVIORAL VERDICT: Identify spending triggers and flag health/financial risks.
                """
                try:
                    st.markdown(model.generate_content(final_report_prompt).text)
                except Exception as e:
                    st.error(f"Analysis failed: {e}")

# ==========================================
# TAB 3: THE INTERCEPTOR
# ==========================================
with tab3:
    st.header("Step 3: Pre-Spend Interceptor")
    item = st.text_input("What are you about to buy?")
    price = st.number_input("Price (₹)", min_value=0)
    
    if st.button("Evaluate Purchase", type="primary") and price > 0:
        fv_10 = price * (1.12**10)
        st.error(f"🛑 10-Year Opportunity Cost: ₹{fv_10:,.2f}")
        st.markdown(model.generate_content(f"Item: {item}, Price: {price}. Give 2 Indian investment alternatives and 1 psychological question.").text)
