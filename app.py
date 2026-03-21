import streamlit as st
import google.generativeai as genai
from PIL import Image
import re

# --- 1. CLEAN DATA (Step 3: MSEDCL 2026 Ground Truth) ---
TARIFF_SLABS = [(100, 4.63), (300, 11.75), (500, 16.23), (float('inf'), 18.63)]
FIXED_CHARGE = 115.0
TAX_MULTIPLIER = 1.16  # 16% Electricity Duty
COST_PER_KW = 65000     # Nashik 2026 Standard
SUBSIDY_3KW = 78000

# --- UI SETUP ---
st.set_page_config(page_title="SolarOptima Nashik", page_icon="☀️", layout="centered")
st.title("☀️ SolarOptima Nashik")
st.markdown("### VJTI-Engineered ROI Calculator")
st.caption("Grounded in 2026 MSEDCL Tariffs & PM-Surya Ghar Subsidies")

# --- AUTHENTICATION ---
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = st.sidebar.text_input("Enter Gemini API Key", type="password")

if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    # --- 2. INPUT SECTION ---
    uploaded_bill = st.file_uploader("📸 Upload your MSEDCL Bill (Photo)", type=["jpg", "jpeg", "png"])
    
    if uploaded_bill:
        img = Image.open(uploaded_bill)
        st.image(img, caption="MSEDCL Bill Detected", use_container_width=True)

        if st.button("🚀 CALCULATE ROI"):
            with st.spinner("Step 4: Running Vision & Financial Algorithm..."):
                # VISION LOGIC
                prompt = "Analyze this MSEDCL bill. Find the 'Total Units Consumed' or 'Current Consumption'. Just output the number."
                try:
                    response = model.generate_content([prompt, img])
                    units = float(re.search(r'\d+', response.text).group())
                    
                    # --- STEP 4: THE ALGORITHM ---
                    # A. Sizing
                    suggested_kw = round((units / 120) * 2) / 2
                    suggested_kw = max(1.0, min(suggested_kw, 10.0))
                    
                    # B. Billing Math (Current vs After Solar)
                    def get_bill(u):
                        if u <= 100: e = u * 4.63
                        elif u <= 300: e = (100 * 4.63) + (u-100) * 11.75
                        else: e = (100 * 4.63) + (200 * 11.75) + (u-300) * 16.23
                        return (e + FIXED_CHARGE) * TAX_MULTIPLIER

                    current_bill = get_bill(units)
                    solar_gen = suggested_kw * 120
                    remaining_u = max(0, units - solar_gen)
                    new_bill = get_bill(remaining_u)
                    
                    monthly_savings = current_bill - new_bill
                    
                    # C. Investment Math
                    gross = suggested_kw * COST_PER_KW
                    subsidy = SUBSIDY_3KW if suggested_kw >= 3 else (suggested_kw * 30000)
                    net_cost = gross - subsidy
                    payback_yrs = net_investment = net_cost / (monthly_savings * 12)

                    # --- 3. OUTPUT REPORT ---
                    st.divider()
                    st.success(f"✅ Extracted Consumption: **{units} Units/Month**")
                    
                    c1, c2, c3 = st.columns(3)
                    c1.metric("System Size", f"{suggested_kw} kW")
                    c2.metric("Net Investment", f"₹{int(net_cost):,}")
                    c3.metric("Payback", f"{payback_yrs:.1f} Years")

                    st.info(f"💰 **Monthly Savings:** ₹{int(monthly_savings):,} (Including 16% Duty)")
                    
                    # --- STEP 6: FEEDBACK LOOP ---
                    st.markdown("---")
                    st.subheader("🏁 Step 6: Feedback for Enhancement")
                    correct = st.radio("Was the unit extraction accurate?", ("Yes", "No"))
                    if correct == "No":
                        real_units = st.number_input("What were the actual units on the bill?", value=units)
                        st.write("Thanks! This data will help us tune our OCR algorithm.")

                except Exception as e:
                    st.error(f"Processing Error: {e}")
else:
    st.warning("Please provide your API Key in the sidebar.")
