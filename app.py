import streamlit as st
import pandas as pd
import google.generativeai as genai
import io
import json
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
        # THE DYNAMIC MODEL FINDER (The Working Logic)
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        if 'models/gemini-1.5-flash' in available_models:
            target_model = 'gemini-1.5-flash'
        elif 'models/gemini-1.5-flash-latest' in available_models:
            target_model = 'gemini-1.5-flash-latest'
        else:
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
    st.error("🔒 **ZERO-TRUST PROTOCOL:** Hand-written paper notes only.")
    
    photo_file = st.file_uploader("Upload Photo of Handwritten Ledger (JPG/PNG)", type=["jpg", "jpeg", "png"])
    
    if photo_file:
        image = Image.open(photo_file)
        st.image(image, caption="Your Secure Ledger", width=500)
        
        if st.button("Extract Data", type="primary"):
            with st.spinner("Digitizing handwriting..."):
                try:
                    vision_prompt = "Extract transactions. Output ONLY raw CSV format with columns: Date, Description, Amount. No headers or markdown."
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
# TAB 2: THE WEALTH ENGINE (V1.10 - AUTO-TAG & JUSTIFY)
# ==========================================
with tab2:
    st.header("Step 2: Tag & Analyze")
    clean_file = st.file_uploader("Upload Digitized Data (CSV)", type=["csv"], key="w_up")
    
    if clean_file:
        # 1. Load Data & Initialize Session State
        if "working_df" not in st.session_state or st.session_state.get("active_filename") != clean_file.name:
            df = pd.read_csv(clean_file)
            
            # Ensure proper columns
            if "Amount" in df.columns:
                df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
            if "Context" not in df.columns: df["Context"] = ""
            
            # --- NEW FEATURE 1: AUTO-TAGGING ON LOAD ---
            with st.spinner("✨ AI is pre-tagging your transactions..."):
                try:
                    desc_list = df['Description'].astype(str).tolist()
                    tag_prompt = f"Categorize into: Need, Desire, Salary, Income. Return ONLY a JSON list of strings. Items: {desc_list}"
                    res = model.generate_content(tag_prompt).text
                    start, end = res.find('['), res.rfind(']') + 1
                    tags = json.loads(res[start:end])
                    if len(tags) == len(df):
                        df["Tag"] = [t.title() if t.title() in ["Need", "Desire", "Salary", "Income"] else "Uncategorized" for t in tags]
                    else:
                        df["Tag"] = "Uncategorized"
                except:
                    df["Tag"] = "Uncategorized"
            
            st.session_state.working_df = df
            st.session_state.active_filename = clean_file.name

        st.subheader("1. Financial Triage & Clarification")
        st.info("💡 **Feature 1:** AI has auto-tagged your spending. You can still manually change them. **Feature 2:** If you see a warning about high costs in the report below, explain your purchase in the 'Context' column.")
        
        # DISPLAY THE TABLE (User has Agency to change tags)
        edited_df = st.data_editor(
            st.session_state.working_df,
            column_config={
                "Tag": st.column_config.SelectboxColumn("Tag", options=["Need", "Desire", "Salary", "Income", "Uncategorized"], required=True),
                "Context": st.column_config.TextColumn("Context (Optional)", help="Justify high-cost transactions here.")
            },
            use_container_width=True,
            key="v1.10_editor"
        )
        
        # Calculations
        desires = edited_df[edited_df["Tag"] == "Desire"]
        total_desire = desires["Amount"].sum()
        sip_fv = total_desire * (((1.01)**12 - 1) / 0.01) * 1.01
        
        st.divider()
        c1, c2 = st.columns(2)
        c1.metric("Monthly 'Desire' Leakage", f"₹{total_desire:,.2f}")
        c2.metric("1-Year SIP Potential", f"₹{sip_fv:,.2f}")
        
        if st.button("Generate Strategy Report", type="primary"):
            with st.spinner("Analyzing market rates and your justifications..."):
                csv_sum = edited_df[['Description', 'Amount', 'Tag', 'Context']].to_csv(index=False)
                
                # --- NEW FEATURE 2: ANALYZE JUSTIFICATION ---
                final_report_prompt = f"""
                Analyze this Indian spending data:
                {csv_sum}
                
                Report Requirements:
                1. FINANCIAL WINS: Praise the user for specific good choices.
                2. MARKET RATE & JUSTIFICATION ANALYSIS: 
                   - Flag any transaction that exceeds standard Indian market rates.
                   - If the user has provided a 'Context' (Justification) for a high-cost item: 
                     a) Analyze if their reasoning is financially rational.
                     b) Provide a rational counter-argument (e.g., 'While this brought joy, a second-hand version would have saved you 40%').
                     c) Or, validate it if it was a genuine investment/necessity.
                3. MICRO-OPPORTUNITY COSTS: Table for 'Desire' items showing 3 crisp Indian alternatives.
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
