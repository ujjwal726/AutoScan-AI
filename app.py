import streamlit as st
import pandas as pd
import google.generativeai as genai
import io
import re

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
    # Using the fast, high-quota model
    model = genai.GenerativeModel("gemini-1.5-flash-8b")
else:
    st.sidebar.warning("API Key required for the AI Strategy modules (Tabs 2 & 3).")

# --- NAVIGATION TABS ---
tab1, tab2, tab3 = st.tabs(["🛡️ 1. Auto-Sanitizer", "🧠 2. The Wealth Engine", "🛑 3. Pre-Spend Interceptor"])

# ==========================================
# TAB 1: DATA AUTO-SANITIZER (Zero AI, 100% Local Privacy)
# ==========================================
with tab1:
    st.header("Step 1: Auto-Sanitize Your Statement")
    st.write("Upload your raw PhonePe or Bank CSV. Our local script will automatically scrub your personal details in milliseconds. **No data is sent to the internet here.**")
    
    raw_file = st.file_uploader("Upload Raw Expenses (CSV)", type=["csv"], key="raw")
    
    if raw_file:
        df = pd.read_csv(raw_file)
        
        with st.spinner("Scrubbing PII..."):
            # 1. AUTO-DROP SENSITIVE COLUMNS
            cols_to_drop = ['Transaction ID', 'Reference No', 'Balance', 'Account Number', 'UTR']
            df = df.drop(columns=[col for col in cols_to_drop if col in df.columns], errors='ignore')

            # 2. AUTO-SCRUB NARRATIONS (Regex Magic)
            def scrub_text(text):
                if pd.isna(text):
                    return text
                text = str(text)
                text = re.sub(r'[a-zA-Z0-9.\-_]+@[a-zA-Z]+', '[UPI_HIDDEN]', text) # Hide UPI
                text = re.sub(r'\b\d{10}\b', '[PHONE_HIDDEN]', text) # Hide Phones
                text = re.sub(r'\b\d{9,18}\b', '[ACC_HIDDEN]', text) # Hide Bank Accounts
                return text

            desc_columns = ['Transaction Details', 'Narration', 'Description', 'Remarks', 'Particulars']
            for col in desc_columns:
                if col in df.columns:
                    df[col] = df[col].apply(scrub_text)
                    
            # 3. FILTER FOR DEBITS (Expenses only) & STANDARDIZE 'AMOUNT'
            if 'Type' in df.columns: # PhonePe format
                df = df[df['Type'] == 'Debit']
            elif 'Withdrawal Amt.' in df.columns: # SBI format
                df = df[df['Withdrawal Amt.'].notna()]
                df['Amount'] = df['Withdrawal Amt.'] # Standardize for Tab 2
            elif 'Debit' in df.columns: # HDFC/ICICI format
                df = df[df['Debit'].notna()]
                df['Amount'] = df['Debit']
            
            # Add a blank column for tagging in Step 2
            df["Tag"] = "Uncategorized"

        st.success("✅ Magic Complete! All personal data scrubbed locally.")
        
        st.write("Here is the safe data the AI will see:")
        st.dataframe(df.head(5))
        
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        st.download_button(
            label="⬇️ Download Safe Data for AI Analysis", 
            data=csv_buffer.getvalue(), 
            file_name="safe_expenses.csv", 
            mime="text/csv", 
            type="primary"
        )

# ==========================================
# TAB 2: THE WEALTH ENGINE (AI Strategy)
# ==========================================
with tab2:
    st.header("Step 2: Tag & Analyze")
    clean_file = st.file_uploader("Upload Cleaned Data (CSV)", type=["csv"], key="clean")
    
    if clean_file:
        df = pd.read_csv(clean_file)
        
        st.subheader("1. Triage Your Spending")
        st.caption("Double-click the 'Tag' column to label transactions as Need or Desire.")
        
        edited_df = st.data_editor(
            df,
            column_config={
                "Tag": st.column_config.SelectboxColumn(
                    "Tag",
                    help="Categorize this spend",
                    options=["Need", "Desire", "Uncategorized"],
                    required=True
                )
            },
            use_container_width=True
        )
        
        desires_df = edited_df[edited_df["Tag"] == "Desire"]
        total_desire_spend = desires_df["Amount"].sum() if "Amount" in desires_df.columns else 0
        
        st.divider()
        st.subheader("2. Opportunity Cost Math")
        rate = 0.12 # 12% expected market return
        years = 10
        future_value = total_desire_spend * ((1 + rate) ** years)
        
        col1, col2 = st.columns(2)
        col1.metric("Total 'Desire' Spend", f"₹{total_desire_spend:,.2f}")
        col2.metric(f"10-Year Opportunity Cost (12% CAGR)", f"₹{future_value:,.2f}", delta=f"+₹{future_value - total_desire_spend:,.2f}")
        
        st.divider()
        st.subheader("3. AI Wealth Strategist")
        st.write("Select a specific 'Desire' transaction to get 3 concrete investment alternatives.")
        
        if not desires_df.empty and api_key and "Amount" in desires_df.columns:
            transaction_options = desires_df.apply(lambda row: f"₹{row['Amount']} on {row.get('Date', 'Unknown Date')}", axis=1).tolist()
            selected_trans = st.selectbox("Select a transaction to analyze:", transaction_options)
            
            if st.button("Generate Alternatives"):
                amount_match = float(selected_trans.split("₹")[1].split(" ")[0].replace(',', ''))
                with st.spinner("Consulting AI Strategist..."):
                    prompt = f"""
                    A user spent ₹{amount_match} on a 'Desire' (non-essential item). 
                    As a pragmatic financial advisor, provide 3 concrete, actionable investment or wealth-building alternatives for exactly ₹{amount_match} in India.
                    Format as:
                    1. [Alternative 1] - [Brief Reason]
                    2. [Alternative 2] - [Brief Reason]
                    3. [Alternative 3] - [Brief Reason]
                    End with a 1-sentence macro recommendation.
                    """
                    try:
                        response = model.generate_content(prompt)
                        st.markdown(response.text)
                    except Exception as e:
                        st.error(f"API Error: {e}")

# ==========================================
# TAB 3: THE INTERCEPTOR (Real-Time Pre-Spend)
# ==========================================
with tab3:
    st.header("Step 3: The Pre-Spend Interceptor")
    st.write("About to buy something online? Paste the details here before you check out.")
    
    with st.container(border=True):
        product_link = st.text_input("Product Link (Optional)")
        item_name = st.text_input("What are you buying?")
        item_price = st.number_input("Price (₹)", min_value=0, step=100)
        
        if st.button("Evaluate Purchase", type="primary") and api_key and item_price > 0:
            interceptor_fv = item_price * ((1 + 0.12) ** 10)
            
            st.error(f"⚠️ **Wait!** That ₹{item_price:,.2f} today will cost you **₹{interceptor_fv:,.2f}** in 10 years.")
            
            with st.spinner("Finding better uses for this money..."):
                prompt2 = f"""
                A user is about to spend ₹{item_price} on '{item_name}'. 
                Provide 2 concrete investment alternatives for this exact amount in India, and 1 psychological question to make them reconsider if they really need it.
                """
                try:
                    response2 = model.generate_content(prompt2)
                    st.markdown("---")
                    st.markdown(response2.text)
                except Exception as e:
                    st.error(f"API Error: {e}")
