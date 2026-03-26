from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import pandas as pd

# 1. Initialize the API
app = FastAPI(title="KiranaAI Backend API")

# 2. CORS Middleware (Crucial!)
# This allows your HTML file (running locally in a browser) to securely talk to this Python server.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for local testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helper function to connect to your existing database
def get_db():
    return sqlite3.connect('shop_data.db')

# 3. Endpoint: Dashboard Financial Metrics
@app.get("/api/metrics")
def get_dashboard_metrics():
    try:
        conn = get_db()
        df_inventory = pd.read_sql_query("SELECT * FROM inventory", conn)
        df_sales = pd.read_sql_query("SELECT * FROM sales", conn)
        conn.close()

        total_investment = float(df_inventory['total'].sum()) if not df_inventory.empty else 0.0
        total_revenue = float(df_sales['total'].sum()) if not df_sales.empty else 0.0
        current_balance = total_revenue - total_investment

        # Calculate Udhari
        total_credit = 0.0
        if not df_sales.empty:
            credit_mask = df_sales['payment_mode'].str.contains('credit|udhari', case=False, na=False)
            total_credit = float(df_sales.loc[credit_mask, 'total'].sum())

        # Return the math as a clean JSON package
        return {
            "investment": total_investment,
            "revenue": total_revenue,
            "balance": current_balance,
            "udhari": total_credit
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# 4. Endpoint: Inventory Stock Levels
@app.get("/api/stock")
def get_stock_levels():
    try:
        conn = get_db()
        df_inventory = pd.read_sql_query("SELECT * FROM inventory", conn)
        df_sales = pd.read_sql_query("SELECT * FROM sales", conn)
        conn.close()

        if df_inventory.empty:
            return []

        # Group In
        in_summary = df_inventory.groupby(['item_name', 'category'])['quantity'].sum().reset_index()
        in_summary.rename(columns={'quantity': 'Total_In'}, inplace=True)

        # Group Out
        out_summary = pd.DataFrame(columns=['item_name', 'Total_Out'])
        if not df_sales.empty:
            out_summary = df_sales.groupby('item_name')['quantity'].sum().reset_index()
            out_summary.rename(columns={'quantity': 'Total_Out'}, inplace=True)

        # Merge & Calculate Remaining
        dashboard_df = pd.merge(in_summary, out_summary, on='item_name', how='left').fillna(0)
        dashboard_df['Remaining_Stock'] = dashboard_df['Total_In'] - dashboard_df['Total_Out']
        
        # Determine Status
        def get_status(qty):
            if qty > 20: return "Healthy"
            elif qty > 5: return "Reorder Soon"
            else: return "Low Stock"
            
        dashboard_df['Status'] = dashboard_df['Remaining_Stock'].apply(get_status)

        # Convert the dataframe to a list of dictionaries for the frontend
        return dashboard_df[['item_name', 'category', 'Remaining_Stock', 'Status']].to_dict(orient='records')
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
