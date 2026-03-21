import streamlit as st
import re

# --- 1. CLEAN DATA (Step 3: MSEDCL 2026 Ground Truth from Ujjwal's Bill) ---
# Rates: 0-100: 4.63 | 101-300: 11.75 | 301-500: 16.23 | 500+: 18.63
FIXED_CHARGE = 115.0
TAX_MULTIPLIER = 1.16  # 16% Electricity Duty
COST_PER_KW = 65000     # Nashik 2026 Standard Market Rate
SUBSIDY_MAX = 78000     # PM-Surya Ghar 3kW Cap

# --- UI SETUP ---
st.set_page_config(page_title="SolarOptima Nashik", page_icon="☀️", layout="centered")
st.title("☀️ SolarOptima Nashik")
st.markdown("### ⚡ Instant Solar ROI Calculator")
st.caption("Grounded in 2026 MSEDCL Tariffs • Designed by Ujjwal Patil (VJTI)")

# --- 2. INPUT SECTION ---
with st.container(border=True):
    units = st.number_input("Average Monthly Units (kWh)", min_value=1, value=300, step=10, help="Check your MSEDCL bill for 'Current Consumption'")
    st.info("💡 Tip: A typical 3BHK in Nashik uses 300-450 units.")

# --- 3. THE ANALYZE BUTTON ---
if st.button("🚀 ANALYZE SOLAR SAVINGS", use_container_width=True, type="primary"):
    with st.spinner("Step 4: Running Financial Algorithm..."):
        
        # --- STEP 4: THE ALGORITHM ---
        # A. Sizing (1kW = 120 units/month in Nashik)
        suggested_kw = round((units / 120) * 2) / 2
        suggested_kw = max(1.0, min(suggested_kw, 10.0)) # Capped at 10kW for Residential
        
        # B. Billing Math (Current vs After Solar)
        def get_bill(u):
            if u <= 100: e = u * 4.63
            elif u <= 300: e = (100 * 4.63) + (u-100) * 11.75
            elif u <= 500: e = (100 * 4.63) + (200 * 11.75) + (u-300) * 16.23
            else: e = (100 * 4.63) + (200 * 11.75) + (200 * 16.23) + (u-500) * 18.63
            return (e + FIXED_CHARGE) * TAX_MULTIPLIER

        current_bill = get_bill(units)
        solar_gen = suggested_kw * 120
        remaining_u = max(0, units - solar_gen)
        new_bill = get_bill(remaining_u)
        
        monthly_savings = current_bill - new_bill
        
        # C. Investment Math (PM Surya Ghar 2026)
        gross_investment = suggested_kw * COST_PER_KW
        if suggested_kw >= 3:
            subsidy = SUBSIDY_MAX
        else:
            subsidy = suggested_kw * 30000 # 30k per kW for < 3kW
            
        net_investment = gross_investment - subsidy
        payback_yrs = net_investment / (monthly_savings * 12)

        # --- 4. OUTPUT REPORT ---
        st.divider()
        st.subheader("📊 Your Solar Investment Report")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("System Size", f"{suggested_kw} kW")
        c2.metric("Net Cost", f"₹{int(net_investment):,}")
        c3.metric("Payback", f"{payback_yrs:.1f} Years")

        with st.expander("🔍 See Detailed Breakdown"):
            st.write(f"**Current Monthly Bill:** ₹{int(current_bill):,}")
            st.write(f"**Bill After Solar:** ₹{int(new_bill):,}")
            st.write(f"**Annual Savings:** ₹{int(monthly_savings * 12):,}")
            st.caption("Note: Calculations include 16% Electricity Duty and Fixed Charges.")
        
        st.balloons()

# --- 5. FEEDBACK LOOP (Step 6) ---
st.markdown("---")
st.caption("💬 Feedback for Step 6: Are these rates matching your last bill? If not, we will update the Dataset.")
