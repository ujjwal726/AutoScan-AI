import streamlit as st
import pandas as pd
import google.generativeai as genai
import io
import json
import time
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
    model = genai.GenerativeModel("gemini-1.5-flash")
    st.sidebar.success("🟢 System Online")
else:
    st.sidebar.warning("API Key required.")
    st.stop()

tab1, tab2, tab3 = st.tabs(["📸 1. Secure Upload", "🧠 2. Wealth Engine", "🛑 3. Interceptor"])

# ==========================================
# TAB 1: SECURE UPLOAD
# ==========================================
with tab1:
    st.header("Step 1: Digitize Your Ledger")
    photo_file = st.file_uploader("Upload Ledger Photo", type=["jpg", "jpeg", "png"])
    
    if photo_file:
        image = Image.open(photo_file)
        st.image(image, width=400)
        if st.button("Extract Data", type="primary"):
            with st.spinner("Vision AI reading handwriting..."):
                try:
                    res = model.generate_content(["Extract transactions. Output ONLY raw CSV: Date, Description, Amount. No markdown.", image])
                    clean_text = res.text.replace("```csv\n", "").replace("```", "").strip()
                    df_v = pd.read_csv(io.StringIO(clean_text), names=["Date", "Description", "Amount"])
                    st.success("✅ Extraction Complete!")
                    st.dataframe(df_v)
                    csv_b = io.StringIO()
                    df_v.to_csv(csv_b, index=False)
                    st.download_button("⬇️ Save CSV for Step 2", data=csv_b.getvalue(), file_name="secure_expenses.csv")
                except Exception as e:
                    st.error(f"Quota issue. Wait 60s. Error: {e}")

# ==========================================
# TAB 2: WEALTH ENGINE (V1.16 - MANUAL TRIGGER)
# ==========================================
with tab2:
    st.header("Step 2: Tag & Analyze")
    clean_file = st.file_uploader("Upload CSV", type=["csv"], key="w_up")
    
    if clean_file:
        if "master_df" not in st.session_state or st.session_state.get("current_file_name") != clean_file.name:
            df = pd.read_csv(clean_file)
            if "Amount" in df.columns:
                df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').abs().fillna(0)
            
            df["Tag"] = "Uncategorized"
            df["Context"] = ""
            st.session_state.master_df = df
            st.session_state.current_file_name = clean_file.name

        # --- THE NEW MANUAL AUTO-TAGGER ---
        col_tag1, col_tag2 = st.columns([1, 4])
        if col_tag1.button("✨ Run Auto-Tagger"):
            with st.spinner("AI analyzing..."):
                try:
                    df_to_tag = st.session_state.master_df
                    items = df_to_tag['Description'].astype(str).tolist()
                    tag_prompt = f"Categorize as 'Need', 'Desire', 'Salary', or 'Income'. JSON list only: {items}"
                    
                    tag_response = model.generate_content(tag_prompt).text
                    start_idx = tag_response.find('[')
                    end_idx = tag_response.rfind(']') + 1
                    tags_list = json.loads(tag_response[start_idx:end_idx])
                    
                    if len(tags_list) == len(df_to_tag):
                        st.session_state.master_df["Tag"] = [str(t).strip().title() for t in tags_list]
                        st.rerun() # Refresh to show tags
                except Exception as e:
                    st.error("Quota full. Please wait 60 seconds and try again.")

        edited_df = st.data_editor(
            st.session_state.master_df,
            column_config={
                "Tag": st.column_config.SelectboxColumn("Tag", options=["Need", "Desire", "Salary", "Income", "Uncategorized"], required=True),
                "Context": st.column_config.TextColumn("Context (Justification)")
            },
            use_container_width=True,
            key="v16_editor"
        )
        
        # Summary Math
        desires = edited_df[edited_df["Tag"] == "Desire"]
        total_desire = desires["Amount"].sum()
        sip_fv = total_desire * (((1.01)**12 - 1) / 0.01) * 1.01
        
        st.divider()
        c1, c2 = st.columns(2)
        c1.metric("Monthly 'Desire' Leakage", f"₹{total_desire:,.2f}")
        c2.metric("1-Year SIP Potential", f"₹{sip_fv:,.2f}")
        
        if st.button("Generate Strategy Report", type="primary"):
            with st.spinner("Analyzing..."):
                csv_data = edited_df[['Description', 'Amount', 'Tag', 'Context']].to_csv(index=False)
                prompt = f"Data: {csv_data}\nSIP: ₹{sip_fv:,.2f}\nProvide CRISP wins, warnings, alternatives, and behavioral verdict (Max 180 words)."
                try:
                    st.markdown(model.generate_content(prompt).text)
                except Exception as e:
                    st.error("Google is busy. Wait 60s and try again.")

# ==========================================
# TAB 3: INTERCEPTOR
# ==========================================
with tab3:
    st.header("Step 3: Pre-Spend Interceptor")
    item = st.text_input("Product Name")
    price = st.number_input("Price (₹)", min_value=0)
    if st.button("Evaluate", type="primary") and price > 0:
        st.error(f"🛑 10-Year Opportunity Cost: ₹{price * (1.12**10):,.2f}")
        st.markdown(model.generate_content(f"Item: {item}, Price: {price}. Give 2 crisp Indian investment alternatives.").text)
