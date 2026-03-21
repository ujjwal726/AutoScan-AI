import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import urllib.parse
import re

# --- 1. LOCAL NASHIK DATABASE (Edit these whenever you get new data!) ---
# As a PM, you own this data. AI just reads it.
MASTER_PRICE_LIST = {
    "BONNET": {"replace": 22160, "repair": 5500},
    "FRONT BUMPER": {"replace": 12325, "repair": 3500},
    "REAR BUMPER": {"replace": 10400, "repair": 3200},
    "HEADLIGHT (LED)": {"replace": 11150, "repair": 1200},
    "FENDER": {"replace": 8300, "repair": 4000},
    "SIDE MIRROR": {"replace": 5500, "repair": 1500},
    "DOOR PANEL": {"replace": 15000, "repair": 4500}
}

LOCAL_WORKSHOPS = [
    {"name": "Seva Automotive (Nexa)", "area": "Satpur MIDC", "map": "https://maps.google.com/?q=Seva+Automotive+Nashik"},
    {"name": "Jitendra Wheels", "area": "Mumbai-Agra Highway", "map": "https://maps.google.com/?q=Jitendra+Wheels+Nashik"},
    {"name": "Modern Auto Body", "area": "Panchavati", "map": "https://maps.google.com/?q=Panchavati+Nashik"}
]

# --- UI SETUP ---
st.set_page_config(page_title="AutoScan AI", page_icon="🚗", layout="centered")
st.title("🚗 AutoScan AI")
st.markdown("### 🔍 Verified Local Audit")
st.caption("2026 Nashik Dataset • VJTI Engineered")

# --- AUTHENTICATION ---
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = st.sidebar.text_input("Enter Gemini API Key", type="password")

if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    # --- INPUTS ---
    uploaded_file = st.file_uploader("Upload damage photo", type=["jpg", "jpeg", "png"])
    col1, col2 = st.columns(2)
    with col1:
        premium = st.number_input("Annual Premium (₹)", value=22000)
    with col2:
        ncb = st.slider("Current NCB %", 0, 50, 25)

    if uploaded_file:
        img = Image.open(uploaded_file)
        st.image(img, caption="Analyzing against local dataset...", use_container_width=True)

        if st.button("GENERATE VERIFIED REPORT"):
            with st.spinner("Gemini is matching image to your local price list..."):
                # FEEDING YOUR DATA INTO THE AI BRAIN
                prompt = f"""
                Act as an Expert Car Surveyor. Use ONLY this data for pricing: {MASTER_PRICE_LIST}
                
                1. Identify the car model from the photo.
                2. Identify all damaged parts. 
                3. For each part, decide if it needs 'REPLACE' (smashed/missing) or 'REPAIR' (dent/scratch).
                4. Use the EXACT prices from the provided data.
                
                FORMAT:
                VEHICLE: [Name]
                PART_LIST:
                - [Part Name] | ₹[Price] | [Action]
                VERDICT: [GO FOR CLAIM / GO FOR CASH] (Based on {premium} premium and {ncb}% NCB loss)
                """
                
                try:
                    response = model.generate_content([prompt, img])
                    res_text = response.text
                    
                    st.markdown("---")
                    st.subheader("📋 Official Audit Report")
                    
                    # Parsing Parts and creating the Actionable Table
                    parts_lines = re.findall(r"-\s*(.*?)\s*\|\s*₹([\d,]+)", res_text)
                    for name, price in parts_lines:
                        c1, c2, c3 = st.columns([2, 1, 1.5])
                        c1.write(f"**{name}**")
                        c2.write(f"₹{price}")
                        # Dynamic verification link
                        q = urllib.parse.quote(f"Maruti {name} price")
                        c3.link_button("🔗 Verify", f"https://boodmo.com/search/{q}/")
                        st.divider()
                    
                    # Final Advice
                    if "CLAIM" in res_text.upper():
                        st.success("🎯 **VERDICT: GO FOR CLAIM**")
                    else:
                        st.warning("💰 **VERDICT: GO FOR CASH**")

                    # --- WORKSHOP SECTION ---
                    st.subheader("📍 Recommended Local Garages")
                    for shop in LOCAL_WORKSHOPS:
                        with st.expander(f"📌 {shop['name']} - {shop['area']}"):
                            st.link_button("Open in Google Maps", shop['map'])

                except Exception as e:
                    st.error(f"Audit failed: {e}")
else:
    st.warning("Please enter your API Key in the sidebar.")
