import streamlit as st

# --- 1. CLEAN DATA (Step 3: MSEDCL 2026 Ground Truth) ---
# Rates derived from Ujjwal's MSEDCL Bill images
TARIFF_SLABS = [
    (100, 4.63),   # 0-100 units
    (300, 11.75),  # 101-300 units
    (500, 16.23),  # 301-500 units
    (float('inf'), 18.63) # 500+ units
]
FIXED_CHARGE = 115.0
TAX_MULTIPLIER = 1.16  # 16% Electricity Duty
COST_PER_KW = 65000     # Nashik 2026 Average
SUBSIDY_3KW = 78000

# --- UI SETUP ---
st.set_page_config(page_title="SolarOptima Nashik", page_icon="☀️", layout="centered")
st.title("☀️ SolarOptima Nashik")
st.markdown("### ⚡ Precision Solar ROI Calculator")
st.caption("Grounded in 2026 MSEDCL Tariffs)

# --- 2. INPUT SECTION ---
with st.container(border=True):
    units = st.number_input("Average Monthly Consumption (Units)", min_value=1, value=350, step=10)
    phase = st.selectbox("Connection Type", ["Single Phase", "Three Phase"])
    st.info("💡 A 3-4kW system is usually optimal for 300-500 units in Nashik.")

# --- 3. THE ANALYZE BUTTON ---
if st.button("🚀 CALCULATE ROI", use_container_width=True, type="primary"):
    
    # --- STEP 4: THE ALGORITHM ---
    # A. Sizing (1kW = 120 units/month in Nashik)
    suggested_kw = round((units / 120) * 2) / 2
    suggested_kw = max(1.0, min(suggested_kw, 10.0))
    
    # B. Billing Math (Slab-Based Deduction)
    def calculate_bill(u):
        total_energy = 0
        if u <= 100: total_energy = u * 4.63
        elif u <= 300: total_energy = (100 * 4.63) + (u-100) * 11.75
        elif u <= 500: total_energy = (100 * 4.63) + (200 * 11.75) + (u-300) * 16.23
        else: total_energy = (100 * 4.63) + (200 * 11.75) + (200 * 16.23) + (u-500) * 18.63
        
        # Adding Fixed Charges + 16% Duty
        return (total_energy + FIXED_CHARGE) * TAX_MULTIPLIER

    current_monthly_bill = calculate_bill(units)
    solar_generation = suggested_kw * 120
    remaining_units = max(0, units - solar_generation)
    new_monthly_bill = calculate_bill(remaining_units)
    
    monthly_savings = current_monthly_bill - new_monthly_bill
    
    # C. Investment Math (PM Surya Ghar 2026)
    gross_investment = suggested_kw * COST_PER_KW
    # Subsidy Logic: 30k/kW for first 2kW, 18k for 3rd kW, Capped at 78k
    if suggested_kw >= 3:
        subsidy = SUBSIDY_3KW
    else:
        subsidy = suggested_kw * 30000
        
    net_investment = gross_investment - subsidy
    payback_years = net_investment / (monthly_savings * 12)

    # --- 4. OUTPUT DISPLAY ---
    st.divider()
    st.subheader("📋 Investment Summary")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Recommended Size", f"{suggested_kw} kW")
    col2.metric("Net Cost", f"₹{int(net_investment):,}")
    col3.metric("Payback Time", f"{payback_years:.1f} Yrs")

    with st.expander("🔍 View Financial Breakdown"):
        st.write(f"**Current Monthly Bill:** ₹{int(current_monthly_bill):,}")
        st.write(f"**Estimated New Bill:** ₹{int(new_monthly_bill):,}")
        st.write(f"**Annual Savings:** ₹{int(monthly_savings * 12):,}")
        st.write(f"**Total Subsidy:** ₹{int(subsidy):,}")
        st.caption("Calculations include 16% Electricity Duty as per MSEDCL 2026 norms.")
    
    st.balloons()

# --- STEP 6: FEEDBACK LOOP ---
st.markdown("---")
st.caption("💬 Feedback: Does this match your actual bill? If the rates have changed, let us know to update dataset")
