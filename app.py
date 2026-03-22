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
        # Stable Model Discovery
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
            with st.spinner("Reading..."):
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
# TAB 2: WEALTH ENGINE (V1.11 - AUTO-TAG & CRISP AI)
# ==========================================
with tab2:
    st.header("Step 2: Tag & Analyze")
    clean_file = st.file_uploader("Upload CSV", type=["csv"], key="w_up")
    
    if clean_file:
        # Load and verify Session State to prevent repeat API calls
        if "final_df" not in st.session_state or st.session_state.get("file_id") != clean_file.name:
            df = pd.read_csv(clean_file)
            
            # MATH FIX: Convert all amounts to positive (absolute) numbers for clean math
            if "Amount" in df.columns:
                df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').abs().fillna(0)
            
            df["Context"] = ""
            
            # --- FEATURE 1: ACTIVE AUTO-TAGGING ---
            with st.spinner("✨ AI Auto-Tagging..."):
                try:
                    items = df['Description'].astype(str).tolist()
                    tag_res = model.generate_content(f"Categorize as Need, Desire, Salary, or Income. JSON list only: {items}").text
                    s, e = tag_res.find('['), tag_res.rfind(']') + 1
                    tags = json.loads(tag_res[s:e])
                    df["Tag"] = [t.title() for t in tags] if len(tags) == len(df) else "Uncategorized"
                except:
                    df["Tag"] = "Uncategorized"
            
            st.session_state.final_df = df
            st.session_state.file_id = clean_file.name

        # Interactive Table
        edited_df = st.data_editor(
            st.session_state.final_df,
            column_config={
                "Tag": st.column_config.SelectboxColumn("Tag", options=["Need", "Desire", "Salary", "Income"], required=True),
                "Context": st.column_config.TextColumn("Context (Justify here)")
            },
            use_container_width=True, key="editor_v11"
        )
        
        # Summary Math
        desires = edited_df[edited_df["Tag"] == "Desire"]
        total_desire = desires["Amount"].sum()
        sip_fv = total_desire * (((1.01)**12 - 1) / 0.01) * 1.01
        
        st.divider()
        c1, c2 = st.columns(2)
        c1.metric("Monthly 'Desire' Leakage", f"₹{total_desire:,.2f}")
        c2.metric("1-Year SIP Potential", f"₹{sip_fv:,.2f}")
        
        # --- FEATURE 2: CRISP SUGGESTIONS ---
        if st.button("Generate Strategy Report", type="primary"):
            with st.spinner("Analyzing..."):
                csv_data = edited_df[['Description', 'Amount', 'Tag', 'Context']].to_csv(index=False)
                crisp_prompt = f"""
                Data: {csv_data} | SIP Total: ₹{sip_fv:,.2f}
                Task: Provide a CRISP financial report for an Indian user.
                1. WINS: 1 bullet point of praise.
                2. WARNINGS: Flag exorbitant costs. If 'Context' is provided, keep it brief (max 15 words per item).
                3. ALTERNATIVES: Table for Desires with 3 ultra-crisp Indian alternatives.
                4. GOAL: One life-upgrade for ₹{sip_fv:,.2f}.
                5. VERDICT: 1-sentence behavioral fix.
                STRICT RULE: No fluff. Max 200 words total.
                """
                try:
                    st.markdown(model.generate_content(crisp_prompt).text)
                except Exception as e:
                    st.error(f"Quota exceeded? Wait 60s. Error: {e}")

# ==========================================
# TAB 3: INTERCEPTOR
# ==========================================
with tab3:
    st.header("Step 3: Pre-Spend Interceptor")
    item = st.text_input("Product Name")
    price = st.number_input("Price (₹)", min_value=0)
    if st.button("Evaluate", type="primary") and price > 0:
        st.error(f"10-Year Cost: ₹{price * (1.12**10):,.2f}")
        st.markdown(model.generate_content(f"Item: {item}, Price: {price}. Give 2 crisp Indian investments.").text)
