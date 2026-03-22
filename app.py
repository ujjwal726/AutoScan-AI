import streamlit as st
import pandas as pd
import google.generativeai as genai
import io

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
    st.sidebar.warning("API Key required for the AI Strategy modules.")

# --- NAVIGATION TABS ---
tab1, tab2, tab3 = st.tabs(["🛡️ 1. Data Sanitizer", "🧠 2. The Wealth Engine", "🛑 3. Pre-Spend Interceptor"])

# ==========================================
# TAB 1: DATA SANITIZER (Steps 1, 2, 3)
# ==========================================
with tab1:
    st.header("Step 1: Sanitize Your Bank Data")
    st.write("Upload your raw bank CSV. We will process it locally to remove Personal Identifiable Information (PII) before any AI analysis.")
    
    raw_file = st.file_uploader("Upload Raw Expenses (CSV)", type=["csv"], key="raw")
    
    if raw_file:
        raw_df = pd.read_csv(raw_file)
        st.write("Preview of Raw Data:")
        st.dataframe(raw_df.head(3))
        
        # Select columns to KEEP (dropping Merchant, Account No, etc.)
        st.info("Select ONLY the columns needed for financial math (e.g., Date, Amount, Generic Category).")
        safe_cols = st.multiselect("Select columns to keep:", raw_df.columns.tolist())
        
        if st.button("Sanitize & Download"):
            if safe_cols:
                clean_df = raw_df[safe_cols].copy()
                # Add a blank column for tagging later
                clean_df["Tag"] = "Uncategorized" 
                
                # Convert to CSV for download
                csv_buffer = io.StringIO()
                clean_df.to_csv(csv_buffer, index=False)
                
                st.success("Data sanitized! No personal info remains.")
                st.download_button(
                    label="⬇️ Download Cleaned Data",
                    data=csv_buffer.getvalue(),
                    file_name="clean_wealth_data.csv",
                    mime="text/csv"
                )
            else:
                st.warning("Please select at least one column.")

# ==========================================
# TAB 2: THE WEALTH ENGINE (Steps 4, 5, 6, 7, 8, 9)
# ==========================================
with tab2:
    st.header("Step 2: Tag & Analyze")
    clean_file = st.file_uploader("Upload Cleaned Data (CSV)", type=["csv"], key="clean")
    
    if clean_file:
        df = pd.read_csv(clean_file)
        
        st.subheader("1. Triage Your Spending")
        st.caption("Double-click the 'Tag' column to label transactions as Need or Desire.")
        
        # Interactive Data Editor for Tagging
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
        
        # Filter for Desires
        desires_df = edited_df[edited_df["Tag"] == "Desire"]
        total_desire_spend = desires_df["Amount"].sum() if "Amount" in desires_df.columns else 0
        
        st.divider()
        st.subheader("2. Opportunity Cost Math")
        # Formula: FV = PV * (1 + r)^n
        rate = 0.12 # 12% expected market return
        years = 10
        future_value = total_desire_spend * ((1 + rate) ** years)
        
        col1, col2 = st.columns(2)
        col1.metric("Total 'Desire' Spend", f"₹{total_desire_spend:,.2f}")
        col2.metric(f"10-Year Opportunity Cost (12% CAGR)", f"₹{future_value:,.2f}", delta=f"+₹{future_value - total_desire_spend:,.2f}")
        
        st.divider()
        st.subheader("3. AI Wealth Strategist")
        st.write("Select a specific 'Desire' transaction to get 3 concrete investment alternatives.")
        
        if not desires_df.empty and api_key:
            # Let user pick a transaction to deep dive
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
                    response = model.generate_content(prompt)
                    st.markdown(response.text)

# ==========================================
# TAB 3: THE INTERCEPTOR (Steps 10, 11)
# ==========================================
with tab3:
    st.header("Step 3: The Pre-Spend Interceptor")
    st.write("About to buy something online? Paste the details here before you check out.")
    
    with st.container(border=True):
        product_link = st.text_input("Product Link (Optional)")
        item_name = st.text_input("What are you buying?")
        item_price = st.number_input("Price (₹)", min_value=0, step=100)
        
        if st.button("Evaluate Purchase", type="primary") and api_key and item_price > 0:
            # Math
            interceptor_fv = item_price * ((1 + 0.12) ** 10)
            
            st.error(f"⚠️ **Wait!** That ₹{item_price:,.2f} today will cost you **₹{interceptor_fv:,.2f}** in 10 years.")
            
            with st.spinner("Finding better uses for this money..."):
                prompt2 = f"""
                A user is about to spend ₹{item_price} on '{item_name}'. 
                Provide 2 concrete investment alternatives for this exact amount, and 1 psychological question to make them reconsider if they really need it.
                """
                response2 = model.generate_content(prompt2)
                st.markdown("---")
                st.markdown(response2.text)
