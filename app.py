import streamlit as st
import google.generativeai as genai
from PIL import Image
import urllib.parse
import re
import time

# --- 1. DATASET (2026 MGP) ---
PARTS_DATABASE = {
    "BONNET": {"replace": 22163, "repair": 5500},
    "FRONT BUMPER": {"replace": 12325, "repair": 3500},
    "REAR BUMPER": {"replace": 10396, "repair": 3200},
    "HEADLIGHT (LED)": {"replace": 11152, "repair": 1500},
    "FENDER": {"replace": 8335, "repair": 4000},
    "DOOR": {"replace": 14665, "repair": 4500},
    "WINDSHIELD": {"replace": 18564, "repair": 0}
}

st.set_page_config(page_title="AutoScan AI", page_icon="🚗", layout="wide")
st.title("🚗 AutoScan Insurance AI")
st.caption("Running on High-Quota 1.5-Flash-8B Engine")

if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = st.sidebar.text_input("Enter Gemini API Key", type="password")

if api_key:
    genai.configure(api_key=api_key)
    # SWITCHED MODEL: gemini-1.5-flash-8b has higher free-tier limits
    model = genai.GenerativeModel("gemini-1.5-flash-8b")

    with st.sidebar:
        st.header("🛡️ Policy Context")
        premium = st.number_input("Annual Premium (₹)", value=22000)
        ncb_pct = st.slider("Current NCB %", 0, 50, 25)
        potential_loss = ((premium * ncb_pct) / 100) + 1000
        st.error(f"Loss on Claim: ₹{int(potential_loss):,}")

    uploaded_file = st.file_uploader("Upload Damage Photo", type=["jpg", "jpeg", "png"])

    if uploaded_file:
        img = Image.open(uploaded_file)
        st.image(img, use_container_width=True)

        if st.button("🚀 ANALYZE DAMAGE"):
            # Robust Retry Logic
            max_retries = 3
            success = False
            
            for attempt in range(max_retries):
                try:
                    with st.spinner(f"Analyzing... (Attempt {attempt + 1})"):
                        prompt = f"Identify Maruti model and damaged parts from this image. Use this exact pricing: {PARTS_DATABASE}. Format output strictly as: VEHICLE: [Model], DAMAGED_PARTS: - [Part Name] | ₹[Price] | [Action]"
                        response = model.generate_content([prompt, img])
                        res_text = response.text
                        success = True
                        break
                except Exception as e:
                    if "429" in str(e):
                        time.sleep(3)
                    else:
                        st.error(f"Error: {e}")
                        break
            
            if success:
                st.markdown("---")
                # Parse and Display (Same logic as before)
                try:
                    vehicle = re.search(r"VEHICLE:\s*(.*)", res_text).group(1)
                    st.subheader(f"📑 Audit: {vehicle}")
                    
                    parts_lines = re.findall(r"-\s*(.*?)\s*\|\s*₹([\d,]+)", res_text)
                    total_repair = 0
                    
                    c1, c2, c3 = st.columns([2, 1, 1])
                    c1.write("**Component**"); c2.write("**2026 MGP Rate**"); c3.write("**Action**")
                    st.divider()

                    for name, price in parts_lines:
                        p_val = int(price.replace(',', ''))
                        total_repair += p_val
                        col1, col2, col3 = st.columns([2, 1, 1])
                        col1.write(f"**{name}**")
                        col2.write(f"₹{price}")
                        q = urllib.parse.quote(f"Maruti {vehicle} {name} price")
                        col3.link_button("🔗 Verify", f"https://boodmo.com/search/{q}/")
                        st.divider()

                    if total_repair > potential_loss:
                        st.success(f"🎯 **SUGGESTION: GO FOR CLAIM** (Repair ₹{total_repair:,} > Loss ₹{int(potential_loss):,})")
                    else:
                        st.warning(f"🎯 **SUGGESTION: PAY CASH** (Protect your NCB)")
                except:
                    st.error("Format error. Please try a clearer photo.")
else:
    st.warning("Please enter your API Key.")
