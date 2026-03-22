import streamlit as st
import pandas as pd
import google.generativeai as genai
import io
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
        
        if 'models/gemini-1.5-flash' in available_models:
            target_model = 'gemini-1.5-flash'
        elif 'models/gemini-1.5-flash-latest' in available_models:
            target_model = 'gemini-1.5-flash-latest'
        elif 'models/gemini-pro-vision' in available_models:
            target_model = 'gemini-pro-vision'
        elif available_models:
            target_model = available_models[0].replace('models/', '')
        else:
            target_model = 'gemini-1.5-flash'
            
        model = genai.GenerativeModel(target_model)
        st.sidebar.success(f"🟢 Secured Connection: {target_model.replace('models/', '')}")
    except Exception as e:
        st.sidebar.error(f"Connection Error: {e}")
else:
    st.sidebar.warning("API Key required to run the AI Wealth Engine.")

# --- NAVIGATION TABS ---
tab1, tab2, tab3 = st.tabs(["📸 1. Secure Ledger Upload", "🧠 2. The Wealth Engine", "🛑 3. Pre-Spend Interceptor"])

# ==========================================
# TAB 1: DATA INGESTION (Analog Air-Gap ONLY)
# ==========================================
with tab1:
    st.header("Step 1: Digitize Your Paper Ledger")
    
    st.error("🔒 **ZERO-TRUST PROTOCOL:** Do NOT upload official bank statements or screenshots of your banking apps.")
    
    st.write("To guarantee absolute privacy, write your expenses on paper and upload a photo. Our Vision AI will digitize it instantly.")
    
    with st.container(border=True):
        st.markdown("""
        **📝 Format Example:**
        * 12-March | Zomato (Burger) | 450
        * 14-March | Amazon Jacket | 8500
        * 15-March | Salary | 50000
        """)
        
    st.divider()
    
    photo_file = st.file_uploader("Upload Photo of Handwritten Ledger (JPG/PNG)", type=["jpg", "jpeg", "png"])
    
    if photo_file and model:
        image = Image.open(photo_file)
        st.image(image, caption="Your Secure Ledger", width=500)
        
        if st.button("Extract Data", type="primary"):
            with st.spinner("Digitizing handwriting..."):
                try:
                    vision_prompt = """
                    Extract the transactions from this handwritten image. 
                    Output strictly as a valid CSV with three columns: Date, Description, Amount.
                    Do not use commas inside the text fields. Ensure amounts are purely numbers.
                    Do not include markdown. Just raw text.
                    """
                    response = model.generate_content([vision_prompt, image])
                    clean_csv_text = response.text.replace("```csv\n", "").replace("```", "").strip()
                    
                    df_vision = pd.read_csv(io.StringIO(clean_csv_text))
                    df_vision["Tag"] = "Uncategorized"
                    
                    st.success("✅ Ledger Digitized Successfully!")
                    st.dataframe(df_vision)
                    
                    csv_buffer = io.StringIO()
                    df_vision.to_csv(csv_buffer, index=False)
                    st.download_button("⬇️ Download Clean CSV for Step 2", data=csv_buffer.getvalue(), file_name="secure_expenses.csv", mime="text/csv")
                except Exception as e:
                    st.error(f"Error reading image: Please ensure handwriting is clear. ({e})")

# ==========================================
# TAB 2: THE WEALTH ENGINE (V1.6 AI AUTO-TAG & PRAISE)
# ==========================================
with tab2:
    st.header("Step 2: Tag & Analyze")
    st.write("Upload the clean CSV you just downloaded from Step 1.")
    clean_file = st.file_uploader("Upload Digitized Data (CSV)", type=["csv"], key="clean_upload")
    
    if clean_file:
        # --- SMART PRE-PROCESSING: AUTO-TAGGING ---
        # We use session state so the AI only auto-tags once per file upload
        if "current_file" not in st.session_state or st.session_state.current_file != clean_file.name:
            df = pd.read_csv(clean_file)
            
            if model and "Description" in df.columns:
                with st.spinner("✨ AI is pre-reading your transactions and auto-tagging them..."):
                    try:
                        desc_list = df['Description'].tolist()
                        tag_prompt = f"""
                        Categorize these transactions into exactly one of these 4 tags: Need, Desire, Salary, Income.
                        Transactions: {desc_list}
                        Return ONLY a comma-separated list of tags in the exact order. No extra text.
                        """
                        tag_response = model.generate_content(tag_prompt)
                        tags = [t.strip().strip("'").strip('"') for t in tag_response.text.split(',')]
                        
                        if len(tags) == len(df):
                            df['Tag'] = tags
                    except Exception:
                        pass # If AI fails, it leaves them as "Uncategorized"
            
            st.session_state.working_df = df
            st.session_state.current_file = clean_file.name

        # --- THE INTERACTIVE EDITOR ---
        st.subheader("1. Financial Triage")
        st.info("💡 **Agency Check:** The AI has auto-tagged your transactions to save you time. Please review them. Double-click any tag to manually override it.")
        
        # We load the dataframe from session state so manual edits don't get erased
        edited_df = st.data_editor(
            st.session_state.working_df,
            column_config={
                "Tag": st.column_config.SelectboxColumn(
                    "Tag", 
                    options=["Need", "Desire", "Salary", "Income", "Uncategorized"], 
                    required=True
                )
            },
            use_container_width=True
        )
        
        # Update session state with manual edits
        st.session_state.working_df = edited_df
        
        if "Amount" in edited_df.columns:
            edited_df['Amount'] = pd.to_numeric(edited_df['Amount'], errors='coerce').fillna(0)
            
            desires_df = edited_df[edited_df["Tag"] == "Desire"]
            total_desire_spend = desires_df["Amount"].sum()
            
            st.divider()
            st.subheader("2. The 'Desire' Leakage & 1-Year SIP Potential")
            
            monthly_rate = 0.12 / 12
            months = 12
            sip_fv = total_desire_spend * (((1 + monthly_rate)**months - 1) / monthly_rate) * (1 + monthly_rate)
            
            col1, col2 = st.columns(2)
            col1.metric("Total Monthly 'Desire' Spend", f"₹{total_desire_spend:,.2f}")
            col2.metric("If Saved Monthly for 1 Year (12% SIP)", f"₹{sip_fv:,.2f}", delta=f"Wealth Created: +₹{sip_fv - (total_desire_spend * 12):,.2f}")
            
            st.divider()
            st.subheader("3. Comprehensive Financial Therapy")
            
            if st.button("Generate Strategy Report", type="primary") and model:
                with st.spinner("Analyzing market rates, finding opportunity costs, and generating insights..."):
                    csv_data = edited_df[['Description', 'Amount', 'Tag']].to_csv(index=False)
                    
                    prompt = f"""
                    You are an elite financial advisor and behavioral therapist in India.
                    Here is the user's categorized spending data:
                    {csv_data}
                    
                    Total Monthly Desire Spend: ₹{total_desire_spend}
                    1-Year SIP Future Value: ₹{sip_fv:,.2f}
                    
                    Format your response EXACTLY into these 5 sections:
                    
                    ### 🌟 1. Financial Wins
                    Identify 1 or 2 good financial decisions from the data (e.g., essential needs, income sources, or avoiding desires). Explicitly praise the user for these choices to reinforce good behavior.
                    
                    ### ⚠️ 2. Market Rate Warnings & Clarifications
                    Scan the amounts for ALL transactions. 
                    - Flag any transaction that seems exorbitant compared to standard Indian market rates (e.g., paying ₹1000 for a regular coffee). Warn them they are overpaying.
                    - If a transaction is high but lacks context (e.g., ₹15,000 on 'Amazon'), explicitly ask the user for more details to determine if it was justified or excessive.
                    
                    ### 🔍 3. Micro-Opportunity Costs
                    Create a Markdown table ONLY for transactions tagged as "Desire". 
                    For EACH desire, provide 3 highly specific, similarly-priced, pragmatic alternative uses for that exact amount in India (e.g., 'Half-month broadband', 'Tank of petrol', 'Term insurance premium').
                    Columns: Description | Amount (₹) | Viable Alternative 1 | Viable Alternative 2 | Viable Alternative 3
                    
                    ### 🎯 4. The 1-Year Tangible Upgrade
                    Based on the 1-Year SIP Future Value of ₹{sip_fv:,.2f}, suggest EXACTLY ONE tangible, high-value, life-enriching purchase or experience they could buy a year from now if they saved this money instead.
                    
                    ### 🧠 5. Behavioral Pattern & Verdict
                    Analyze the descriptions of their 'Desire' spending. 
                    - Identify their core spending trigger in ONE sentence. 
                    - If you notice a trend toward unhealthy habits (e.g., sugary/salty foods), explicitly flag the health risk.
                    - Give ONE sentence of actionable advice to shift to a better lifestyle/financial habit.
                    """
                    try:
                        response = model.generate_content(prompt)
                        st.markdown(response.text)
                    except Exception as e:
                        st.error(f"API Error: {e}")
        else:
            st.error("No 'Amount' column found in the uploaded data.")

# ==========================================
# TAB 3: THE INTERCEPTOR
# ==========================================
with tab3:
    st.header("Step 3: The Pre-Spend Interceptor")
    st.write("About to make an impulse purchase online? Run it through the engine first.")
    with st.container(border=True):
        item_name = st.text_input("What are you about to buy?")
        item_price = st.number_input("Price (₹)", min_value=0, step=100)
        
        if st.button("Evaluate Purchase", type="primary") and model and item_price > 0:
            fv = item_price * ((1 + 0.12) ** 10)
            st.error(f"⚠️ **Wait!** That ₹{item_price:,.2f} today will cost you **₹{fv:,.2f}** in 10 years.")
            
            with st.spinner("Finding better uses for this capital..."):
                prompt2 = f"A user is about to spend ₹{item_price} on '{item_name}'. Provide 2 concrete investment alternatives in India, and 1 psychological question to reconsider the purchase."
                try:
                    st.markdown("---")
                    st.markdown(model.generate_content(prompt2).text)
                except Exception as e:
                    st.error(f"API Error: {e}")
