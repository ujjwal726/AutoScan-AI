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

# --- AUTHENTICATION ---
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = st.sidebar.text_input("Enter Gemini API Key", type="password")

if api_key:
    genai.configure(api_key=api_key)
    # Using a stable model name directly to avoid discovery errors
    model = genai.GenerativeModel("gemini-1.5-flash")
    st.sidebar.success("🟢 Secured Connection Active")
else:
    st.sidebar.warning("API Key required for the AI modules.")
    st.stop() # Prevents the rest of the app from running without a key

# --- NAVIGATION ---
tab1, tab2, tab3 = st.tabs(["📸 1. Secure Ledger Upload", "🧠 2. The Wealth Engine", "🛑 3. Pre-Spend Interceptor"])

# ==========================================
# TAB 1: SECURE UPLOAD (HANDWRITTEN ONLY)
# ==========================================
with tab1:
    st.header("Step 1: Digitize Your Paper Ledger")
    st.error("🔒 **ZERO-TRUST PROTOCOL:** Hand-written paper notes only. We do not want your official bank data.")
    
    with st.container(border=True):
        st.markdown("""
        **📝 How to write it:**
        * 12-March | Zomato (Burger) | 450
        * 14-March | Amazon | 15000
        * 15-March | Salary | 50000
        """)
        
    photo_file = st.file_uploader("Upload Photo (JPG/PNG)", type=["jpg", "jpeg", "png"])
    
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
                    
                    st.success("✅ Ledger Digitized!")
                    st.dataframe(df_vision)
                    
                    csv_buffer = io.StringIO()
                    df_vision.to_csv(csv_buffer, index=False)
                    st.download_button("⬇️ Download Clean CSV for Step 2", data=csv_buffer.getvalue(), file_name="secure_expenses.csv", mime="text/csv")
                except Exception as e:
                    st.error(f"Handwriting Extraction Error: {e}")

# ==========================================
# TAB 2: THE WEALTH ENGINE (V1.8 REBUILT)
# ==========================================
with tab2:
    st.header("Step 2: Tag & Analyze")
    st.write("Upload the clean CSV you just downloaded from Step 1.")
    clean_file = st.file_uploader("Upload Digitized Data (CSV)", type=["csv"], key="wealth_upload")
    
    if clean_file:
        # Load file fresh every time to avoid state crashes
        df = pd.read_csv(clean_file)
        
        # Ensure base columns exist
        if "Amount" in df.columns:
            df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
        if "Context" not in df.columns:
            df["Context"] = ""
        
        # --- ROBUST AUTO-TAGGING ---
        # We check if tags already exist; if not, we ask AI to guess once.
        if "Tag" not in df.columns or df["Tag"].isnull().all() or (df["Tag"] == "Uncategorized").all():
            with st.spinner("✨ AI is pre-tagging your transactions..."):
                try:
                    desc_list = df['Description'].astype(str).tolist()
                    tag_prompt = f"Categorize these items into: Need, Desire, Salary, Income. Return as a JSON list of strings. Items: {desc_list}"
                    res_text = model.generate_content(tag_prompt).text
                    # JSON Cleanup
                    start = res_text.find('[')
                    end = res_text.rfind(']') + 1
                    tags = json.loads(res_text[start:end])
                    
                    if len(tags) == len(df):
                        df["Tag"] = [t.title() for t in tags]
                    else:
                        df["Tag"] = "Uncategorized"
                except:
                    df["Tag"] = "Uncategorized"

        st.subheader("1. Financial Triage & Clarification")
        st.info("💡 **Agency Check:** AI has auto-tagged your spending. Review them below. Use the 'Context' column to explain large amounts (e.g. 'New Phone') before generating the report.")
        
        # DISPLAY THE TABLE
        edited_df = st.data_editor(
            df,
            column_config={
                "Tag": st.column_config.SelectboxColumn("Tag", options=["Need", "Desire", "Salary", "Income", "Uncategorized"], required=True),
                "Context": st.column_config.TextColumn("Context (Optional)", help="Explain large purchases here.")
            },
            use_container_width=True,
            key="editor_stable_v1.8"
        )
        
        # --- ANALYSIS SECTION ---
        desires = edited_df[edited_df["Tag"] == "Desire"]
        total_desire = desires["Amount"].sum()
        
        st.divider()
        col1, col2 = st.columns(2)
        col1.metric("Total Monthly 'Desire' Spend", f"₹{total_desire:,.2f}")
        
        # SIP Calculation
        sip_fv = total_desire * (((1.01)**12 - 1) / 0.01) * 1.01
        col2.metric("1-Year SIP Potential (12% CAGR)", f"₹{sip_fv:,.2f}")
        
        if st.button("Generate Comprehensive Strategy Report", type="primary"):
            with st.spinner("Analyzing market rates and behavioral patterns..."):
                csv_summary = edited_df[['Description', 'Amount', 'Tag', 'Context']].to_csv(index=False)
                
                final_prompt = f"""
                Analyze this Indian spending data:
                {csv_summary}
                
                Report Requirements:
                1. FINANCIAL WINS: Praise the user for specific good decisions (essentials or income).
                2. MARKET RATE WARNINGS: Flag any exorbitant prices. Check the 'Context' column—if the user explained the purchase (e.g. 'Washing Machine'), acknowledge and validate it. If context is missing for a high amount, warn them.
                3. MICRO-OPPORTUNITY COSTS: Create a table for 'Desire' items showing 3 crisp Indian alternatives (e.g. petrol, bills, healthy groceries).
                4. SAVINGS VERTICAL: Suggest ONE high-value thing they can buy with the 1-year SIP wealth of ₹{sip_fv:,.2f}.
                5. BEHAVIORAL VERDICT: Identify their spending trigger (e.g. sugar, electronics) and flag health/financial risks in one line.
                """
                try:
                    st.markdown(model.generate_content(final_prompt).text)
                except Exception as e:
                    st.error(f"Analysis failed: {e}")

# ==========================================
# TAB 3: THE INTERCEPTOR (STABLE)
# ==========================================
with tab3:
    st.header("Step 3: Pre-Spend Interceptor")
    item = st.text_input("Product Name")
    price = st.number_input("Price (₹)", min_value=0)
    
    if st.button("Evaluate", type="primary") and price > 0:
        fv_10 = price * (1.12**10)
        st.error(f"🛑 10-Year Opportunity Cost: ₹{fv_10:,.2f}")
        st.markdown(model.generate_content(f"Item: {item}, Price: {price}. Give 2 Indian investment alternatives and 1 psychological question.").text)
