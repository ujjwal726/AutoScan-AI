import streamlit as st
import pandas as pd
import google.generativeai as genai
import io
import re
from PIL import Image

# --- CONFIGURATION & SETUP ---
st.set_page_config(page_title="WealthTrace AI", page_icon="📈", layout="wide")
st.title("📈 WealthTrace AI")
st.markdown("### Privacy-First Opportunity Cost & Wealth Engine")

# --- AUTHENTICATION ---
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = st.sidebar.text_input("Enter Gemini API Key", type="password")

if api_key:
    genai.configure(api_key=api_key)
    # Using the standard 1.5-flash model as it handles both text and vision flawlessly
    model = genai.GenerativeModel("gemini-1.5-flash-latest")
else:
    st.sidebar.warning("API Key required for the Vision Scanner (Tab 1) and Strategy modules (Tabs 2 & 3).")

# --- NAVIGATION TABS ---
tab1, tab2, tab3 = st.tabs(["🛡️ 1. Data Ingestion", "🧠 2. The Wealth Engine", "🛑 3. Pre-Spend Interceptor"])

# ==========================================
# TAB 1: DATA INGESTION (Hybrid Mode)
# ==========================================
with tab1:
    st.header("Step 1: Ingest & Clean Data")
    st.write("Choose your preferred privacy method to digitize your expenses.")
    
    colA, colB = st.columns(2)
    
    # --- METHOD A: THE ANALOG AIR-GAP (VISION) ---
    with colA:
        st.subheader("Method A: Paper Ledger (Vision AI)")
        st.caption("Highest Privacy. Upload a photo of handwritten transactions. No PII involved.")
        
        photo_file = st.file_uploader("Upload Photo (JPG/PNG)", type=["jpg", "jpeg", "png"])
        
        if photo_file and api_key:
            image = Image.open(photo_file)
            st.image(image, caption="Your Ledger", use_container_width=True)
            
            if st.button("Extract Data", type="primary"):
                with st.spinner("Digitizing handwriting..."):
                    try:
                        vision_prompt = """
                        Extract the transactions from this image. 
                        Output strictly as a valid CSV with three columns: Date, Description, Amount.
                        Do not use commas inside the text fields. Ensure amounts are just numbers.
                        Do not include any markdown formatting like ```csv. Just the raw text.
                        """
                        response = model.generate_content([vision_prompt, image])
                        clean_csv_text = response.text.replace("```csv\n", "").replace("```", "").strip()
                        
                        df_vision = pd.read_csv(io.StringIO(clean_csv_text))
                        df_vision["Tag"] = "Uncategorized"
                        
                        st.success("✅ Extracted Successfully!")
                        st.dataframe(df_vision)
                        
                        csv_buffer = io.StringIO()
                        df_vision.to_csv(csv_buffer, index=False)
                        st.download_button("⬇️ Download Clean CSV for Tab 2", data=csv_buffer.getvalue(), file_name="vision_expenses.csv", mime="text/csv")
                    except Exception as e:
                        st.error(f"Error reading image: {e}")

    # --- METHOD B: THE DIGITAL AUTO-SCRUBBER (CSV) ---
    with colB:
        st.subheader("Method B: Bank CSV (Auto-Scrubber)")
        st.caption("High Convenience. Upload your bank CSV. Python will scrub your PII locally.")
        
        raw_file = st.file_uploader("Upload Raw CSV", type=["csv"], key="raw_csv")
        
        if raw_file:
            df_csv = pd.read_csv(raw_file)
            
            with st.spinner("Scrubbing PII locally..."):
                cols_to_drop = ['Transaction ID', 'Reference No', 'Balance', 'Account Number', 'UTR']
                df_csv = df_csv.drop(columns=[col for col in cols_to_drop if col in df_csv.columns], errors='ignore')

                def scrub_text(text):
                    if pd.isna(text): return text
                    text = str(text)
                    text = re.sub(r'[a-zA-Z0-9.\-_]+@[a-zA-Z]+', '[UPI_HIDDEN]', text) 
                    text = re.sub(r'\b\d{10}\b', '[PHONE_HIDDEN]', text) 
                    text = re.sub(r'\b\d{9,18}\b', '[ACC_HIDDEN]', text) 
                    return text

                desc_columns = ['Transaction Details', 'Narration', 'Description', 'Remarks', 'Particulars']
                for col in desc_columns:
                    if col in df_csv.columns:
                        df_csv[col] = df_csv[col].apply(scrub_text)
                        
                if 'Type' in df_csv.columns: 
                    df_csv = df_csv[df_csv['Type'] == 'Debit']
                elif 'Withdrawal Amt.' in df_csv.columns: 
                    df_csv = df_csv[df_csv['Withdrawal Amt.'].notna()]
                    df_csv['Amount'] = df_csv['Withdrawal Amt.'] 
                elif 'Debit' in df_csv.columns: 
                    df_csv = df_csv[df_csv['Debit'].notna()]
                    df_csv['Amount'] = df_csv['Debit']
                
                df_csv["Tag"] = "Uncategorized"

            st.success("✅ Scrubbed Successfully!")
            st.dataframe(df_csv.head(3))
            
            csv_buffer2 = io.StringIO()
            df_csv.to_csv(csv_buffer2, index=False)
            st.download_button("⬇️ Download Safe CSV for Tab 2", data=csv_buffer2.getvalue(), file_name="safe_expenses.csv", mime="text/csv")

# ==========================================
# TAB 2: THE WEALTH ENGINE
# ==========================================
with tab2:
    st.header("Step 2: Tag & Analyze")
    clean_file = st.file_uploader("Upload the Cleaned Data (CSV from Step 1)", type=["csv"], key="clean_upload")
    
    if clean_file:
        df = pd.read_csv(clean_file)
        
        st.subheader("1. Triage Your Spending")
        st.caption("Double-click the 'Tag' column to label transactions as Need or Desire.")
        
        edited_df = st.data_editor(
            df,
            column_config={
                "Tag": st.column_config.SelectboxColumn("Tag", options=["Need", "Desire", "Uncategorized"], required=True)
            },
            use_container_width=True
        )
        
        desires_df = edited_df[edited_df["Tag"] == "Desire"]
        total_desire_spend = desires_df["Amount"].sum() if "Amount" in desires_df.columns else 0
        
        st.divider()
        st.subheader("2. Opportunity Cost Math")
        rate = 0.12 
        years = 10
        future_value = total_desire_spend * ((1 + rate) ** years)
        
        col1, col2 = st.columns(2)
        col1.metric("Total 'Desire' Spend", f"₹{total_desire_spend:,.2f}")
        col2.metric("10-Year Opportunity Cost (12% CAGR)", f"₹{future_value:,.2f}", delta=f"+₹{future_value - total_desire_spend:,.2f}")
        
        st.divider()
        st.subheader("3. AI Wealth Strategist")
        
        if not desires_df.empty and api_key and "Amount" in desires_df.columns:
            options = desires_df.apply(lambda row: f"₹{row['Amount']} on {row.get('Description', 'Item')}", axis=1).tolist()
            selected_trans = st.selectbox("Select a 'Desire' transaction to analyze:", options)
            
            if st.button("Generate Investment Alternatives"):
                amount_match = float(selected_trans.split("₹")[1].split(" ")[0].replace(',', ''))
                with st.spinner("Consulting AI..."):
                    prompt = f"""
                    A user spent ₹{amount_match} on a non-essential item. 
                    Provide 3 concrete, actionable investment or wealth-building alternatives for exactly ₹{amount_match} in India.
                    Format as a numbered list. Keep reasons brief. End with a 1-sentence macro recommendation.
                    """
                    try:
                        st.markdown(model.generate_content(prompt).text)
                    except Exception as e:
                        st.error(f"API Error: {e}")

# ==========================================
# TAB 3: THE INTERCEPTOR
# ==========================================
with tab3:
    st.header("Step 3: The Pre-Spend Interceptor")
    with st.container(border=True):
        item_name = st.text_input("What are you about to buy?")
        item_price = st.number_input("Price (₹)", min_value=0, step=100)
        
        if st.button("Evaluate Purchase", type="primary") and api_key and item_price > 0:
            fv = item_price * ((1 + 0.12) ** 10)
            st.error(f"⚠️ **Wait!** That ₹{item_price:,.2f} today will cost you **₹{fv:,.2f}** in 10 years.")
            
            with st.spinner("Finding better uses..."):
                prompt2 = f"A user is about to spend ₹{item_price} on '{item_name}'. Provide 2 concrete investment alternatives in India, and 1 psychological question to reconsider the purchase."
                try:
                    st.markdown("---")
                    st.markdown(model.generate_content(prompt2).text)
                except Exception as e:
                    st.error(f"API Error: {e}")
