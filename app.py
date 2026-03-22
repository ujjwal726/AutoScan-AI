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
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        target_model = 'gemini-1.5-flash' if 'models/gemini-1.5-flash' in available_models else available_models[0].replace('models/', '')
        model = genai.GenerativeModel(target_model)
        st.sidebar.success(f"🟢 Connected: {target_model}")
    except Exception as e:
        st.sidebar.error(f"Discovery Error: {e}")
else:
    st.sidebar.warning("Enter API Key to start.")
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
            with st.spinner("Reading handwriting..."):
                try:
                    res = model.generate_content(["Extract transactions. Output ONLY raw CSV: Date, Description, Amount. No markdown.", image])
                    clean_text = res.text.replace("```csv\n", "").replace("```", "").strip()
                    df_v = pd.read_csv(io.StringIO(clean_text), names=["Date", "Description", "Amount"])
                    st.success("✅ Digitized!")
                    st.dataframe(df_v)
                    csv_b = io.StringIO()
                    df_v.to_csv(csv_b, index=False)
                    st.download_button("⬇️ Save CSV for Step 2", data=csv_b.getvalue(), file_name="secure_expenses.csv")
                except Exception as e:
                    st.error(f"Error: {e}")

# ==========================================
# TAB 2: WEALTH ENGINE (V1.12 - IRONCLAD AUTO-TAG)
# ==========================================
with tab2:
    st.header("Step 2: Tag & Analyze")
    clean_file = st.file_uploader("Upload CSV", type=["csv"], key="w_up")
    
    if clean_file:
        # Check if this is a fresh upload
        if "master_df" not in st.session_state or st.session_state.get("current_file_name") != clean_file.name:
            raw_df = pd.read_csv(clean_file)
            
            # Numeric cleanup
            if "Amount" in raw_df.columns:
                raw_df['Amount'] = pd.to_numeric(raw_df['Amount'], errors='coerce').abs().fillna(0)
            
            # --- THE AUTO-TAGGING ENGINE ---
            with st.spinner("🧠 AI is analyzing and tagging your transactions..."):
                try:
                    descriptions = raw_df['Description'].astype(str).tolist()
                    tag_prompt = f"""
                    Categorize each item as exactly 'Need', 'Desire', 'Salary', or 'Income'.
                    Items: {descriptions}
                    Return ONLY a JSON list of strings. No extra text.
                    Example: ["Need", "Desire", "Salary"]
                    """
                    tag_response = model.generate_content(tag_prompt).text
                    
                    # Extraction logic for JSON
                    start_idx = tag_response.find('[')
                    end_idx = tag_response.rfind(']') + 1
                    tags_list = json.loads(tag_response[start_idx:end_idx])
                    
                    # Ensure alignment
                    if len(tags_list) == len(raw_df):
                        raw_df["Tag"] = [t.strip().title() for t in tags_list]
                    else:
                        raw_df["Tag"] = "Uncategorized"
                except:
                    raw_df["Tag"] = "Uncategorized"
            
            # Prepare final DataFrame structure
            raw_df["Context"] = ""
            st.session_state.master_df = raw_df
            st.session_state.current_file_name = clean_file.name
            st.toast("✅ Auto-Tagging Complete!", icon="✨")

        # Display the editor using the Session State (Preserves manual changes)
        edited_df = st.data_editor(
            st.session_state.master_df,
            column_config={
                "Tag": st.column_config.SelectboxColumn(
                    "Tag", 
                    options=["Need", "Desire", "Salary", "Income", "Uncategorized"], 
                    required=True
                ),
                "Context": st.column_config.TextColumn("Context (Justify high costs here)")
            },
            use_container_width=True,
            key="v12_stable_editor"
        )
        
        # Immediate Math Summary
        desires = edited_df[edited_df["Tag"] == "Desire"]
        total_desire = desires["Amount"].sum()
        sip_fv = total_desire * (((1.01)**12 - 1) / 0.01) * 1.01
        
        st.divider()
        c1, c2 = st.columns(2)
        c1.metric("Monthly 'Desire' Leakage", f"₹{total_desire:,.2f}")
        c2.metric("1-Year SIP Potential", f"₹{sip_fv:,.2f}")
        
        # --- CRISP STRATEGY REPORT ---
        if st.button("Generate Strategy Report", type="primary"):
            with st.spinner("Analyzing..."):
                csv_data = edited_df[['Description', 'Amount', 'Tag', 'Context']].to_csv(index=False)
                crisp_prompt = f"""
                Data: {csv_data} | SIP Total: ₹{sip_fv:,.2f}
                Provide a CRISP Indian financial report.
                1. WINS: 1 bullet praise for good choices.
                2. WARNINGS: List exorbitant items. If user provided 'Context', analyze their reasoning rationally.
                3. ALTERNATIVES: Table of Desires with 3 crisp Indian alternatives (petrol, bills, specific groceries).
                4. GOAL: One life-upgrade for ₹{sip_fv:,.2f}.
                5. VERDICT: 1-sentence behavioral pattern fix.
                STRICT: Max 180 words. Direct tone.
                """
                try:
                    st.markdown(model.generate_content(crisp_prompt).text)
                except Exception as e:
                    st.error(f"Quota issue? Wait 60s. Error: {e}")

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
