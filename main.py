from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import pandas as pd
import json
import io
from typing import Optional, List

# AI Providers
import google.generativeai as genai
from openai import OpenAI
from groq import Groq
import anthropic
from PIL import Image

# --- 1. INITIALIZATION & DATABASE ---
app = FastAPI(title="KiranaAI Backend API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def init_db():
    conn = sqlite3.connect('shop_data.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, item_name TEXT, category TEXT, 
        quantity REAL, unit_price REAL, total REAL, payment_mode TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, item_name TEXT, category TEXT, 
        quantity REAL, unit_price REAL, total REAL, payment_mode TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS suppliers (
        id INTEGER PRIMARY KEY AUTOINCREMENT, supplier_name TEXT, item_name TEXT, 
        price_per_unit REAL, distance_km REAL, contact_info TEXT)''')
    conn.commit()
    conn.close()

init_db()

def get_db():
    return sqlite3.connect('shop_data.db')

# --- 2. AI EXTRACTION ENGINE (THE OCR ROUTE) ---
@app.post("/api/extract")
async def extract_data(
    mode: str = Form(...), # "stock", "sales", or "rate_card"
    provider: str = Form(...),
    api_key: str = Form(...),
    model_name: str = Form(...),
    text_data: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None)
):
    # Determine the strict system prompt based on the mode
    if mode in ["stock", "sales"]:
        system_prompt = """Extract the data and output ONLY a raw JSON array of objects.
        Each object MUST have exact keys: "date", "item_name", "category", "quantity", "unit_price", "total", "payment_mode".
        Output ONLY valid JSON. Normalization: Standard English names. Categories: [Grocery, Dairy, Personal Care, Household, Grains].
        quantity, unit_price, and total MUST be numbers."""
    else:
        system_prompt = """Extract items and prices from this rate card. Output ONLY a raw JSON array of objects.
        Keys MUST be exactly: "item_name", "price_per_unit".
        Output ONLY valid JSON. Normalization: Standard English names. Prices must be numbers."""

    # Prepare the payload
    contents = [system_prompt]
    if text_data:
        contents.append(text_data)
    elif file:
        image_bytes = await file.read()
        contents.append(Image.open(io.BytesIO(image_bytes)))
    else:
        raise HTTPException(status_code=400, detail="Must provide either text_data or a file.")

    try:
        # Route to the correct AI Provider
        result_text = ""
        if provider == "Google Gemini":
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(contents)
            result_text = response.text
            
        elif provider == "OpenAI (GPT)":
            client = OpenAI(api_key=api_key)
            # OpenAI requires a different format for images vs text, simplified here for text
            response = client.chat.completions.create(model=model_name, messages=[{"role": "user", "content": str(contents)}])
            result_text = response.choices[0].message.content
            
        elif provider == "Groq":
            client = Groq(api_key=api_key)
            response = client.chat.completions.create(model=model_name, messages=[{"role": "user", "content": str(contents)}])
            result_text = response.choices[0].message.content
            
        elif provider == "Anthropic (Claude)":
            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(model=model_name, max_tokens=2048, messages=[{"role": "user", "content": str(contents)}])
            result_text = response.content[0].text

        # Clean markdown from AI output
        clean_json = result_text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_json)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Processing Error: {str(e)}")

# --- 3. DATABASE WRITE OPERATIONS ---
class SavePayload(BaseModel):
    mode: str
    items: List[dict]
    supplier_name: Optional[str] = None
    distance_km: Optional[float] = None

@app.post("/api/save")
def save_data(payload: SavePayload):
    conn = get_db()
    c = conn.cursor()
    try:
        if payload.mode == "stock":
            for item in payload.items:
                c.execute('''INSERT INTO inventory (date, item_name, category, quantity, unit_price, total, payment_mode)
                             VALUES (?, ?, ?, ?, ?, ?, ?)''', 
                          (item.get('date', 'Today'), item.get('item_name'), item.get('category'), 
                           item.get('quantity', 0), item.get('unit_price', 0), item.get('total', 0), item.get('payment_mode', 'Cash')))
        elif payload.mode == "sales":
            for item in payload.items:
                c.execute('''INSERT INTO sales (date, item_name, category, quantity, unit_price, total, payment_mode)
                             VALUES (?, ?, ?, ?, ?, ?, ?)''', 
                          (item.get('date', 'Today'), item.get('item_name'), item.get('category'), 
                           item.get('quantity', 0), item.get('unit_price', 0), item.get('total', 0), item.get('payment_mode', 'Cash')))
        elif payload.mode == "rate_card":
            c.execute("DELETE FROM suppliers WHERE supplier_name = ?", (payload.supplier_name,))
            for item in payload.items:
                c.execute('''INSERT INTO suppliers (supplier_name, item_name, price_per_unit, distance_km, contact_info)
                             VALUES (?, ?, ?, ?, ?)''',
                          (payload.supplier_name, item.get('item_name'), float(item.get('price_per_unit', 0)), payload.distance_km, "WhatsApp"))
        conn.commit()
        return {"status": "success", "message": "Data saved to database."}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

# --- 4. THE KIRANA MATH ENGINES (READ OPERATIONS) ---

@app.get("/api/metrics")
def get_dashboard_metrics():
    # [Code from previous step remains exactly the same]
    try:
        conn = get_db()
        df_inventory = pd.read_sql_query("SELECT * FROM inventory", conn)
        df_sales = pd.read_sql_query("SELECT * FROM sales", conn)
        conn.close()

        total_investment = float(df_inventory['total'].sum()) if not df_inventory.empty else 0.0
        total_revenue = float(df_sales['total'].sum()) if not df_sales.empty else 0.0
        current_balance = total_revenue - total_investment

        total_credit = 0.0
        if not df_sales.empty:
            credit_mask = df_sales['payment_mode'].str.contains('credit|udhari', case=False, na=False)
            total_credit = float(df_sales.loc[credit_mask, 'total'].sum())

        return {"investment": total_investment, "revenue": total_revenue, "balance": current_balance, "udhari": total_credit}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stock")
def get_stock_levels():
    # [Code from previous step remains exactly the same]
    try:
        conn = get_db()
        df_inventory = pd.read_sql_query("SELECT * FROM inventory", conn)
        df_sales = pd.read_sql_query("SELECT * FROM sales", conn)
        conn.close()

        if df_inventory.empty: return []

        in_summary = df_inventory.groupby(['item_name', 'category'])['quantity'].sum().reset_index()
        in_summary.rename(columns={'quantity': 'Total_In'}, inplace=True)

        out_summary = pd.DataFrame(columns=['item_name', 'Total_Out'])
        if not df_sales.empty:
            out_summary = df_sales.groupby('item_name')['quantity'].sum().reset_index()
            out_summary.rename(columns={'quantity': 'Total_Out'}, inplace=True)

        dashboard_df = pd.merge(in_summary, out_summary, on='item_name', how='left').fillna(0)
        dashboard_df['Remaining_Stock'] = dashboard_df['Total_In'] - dashboard_df['Total_Out']
        
        def get_status(qty):
            if qty > 20: return "Healthy"
            elif qty > 5: return "Reorder Soon"
            else: return "Low Stock"
            
        dashboard_df['Status'] = dashboard_df['Remaining_Stock'].apply(get_status)
        return dashboard_df[['item_name', 'category', 'Remaining_Stock', 'Status']].to_dict(orient='records')
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/forecast")
def get_forecast():
    """Runs the advanced recency bias math and returns actionable orders."""
    try:
        conn = get_db()
        df_inv = pd.read_sql_query("SELECT * FROM inventory", conn)
        df_sal = pd.read_sql_query("SELECT * FROM sales", conn)
        conn.close()

        if df_inv.empty or df_sal.empty:
            return []

        # 1. Total Inventory In
        in_summary = df_inv.groupby('item_name')['quantity'].sum().reset_index()
        in_summary.rename(columns={'quantity': 'Total_In'}, inplace=True)

        # 2. Sales Math
        df_sal['date'] = pd.to_datetime(df_sal['date'])
        latest_date = df_sal['date'].max()
        cutoff_date = latest_date - pd.Timedelta(days=7)

        out_total = df_sal.groupby('item_name')['quantity'].sum().reset_index()
        out_recent = df_sal[df_sal['date'] >= cutoff_date].groupby('item_name')['quantity'].sum().reset_index()

        sales_stats = pd.merge(out_total, out_recent, on='item_name', how='left', suffixes=('_total', '_7d')).fillna(0)

        # 3. The Formula
        sales_stats['hist_vel'] = (sales_stats['quantity_total'] - sales_stats['quantity_7d']) / 23
        sales_stats['recent_vel'] = sales_stats['quantity_7d'] / 7
        sales_stats['Blended_Daily_Velocity'] = (sales_stats['recent_vel'] * 0.70) + (sales_stats['hist_vel'] * 0.30)
        sales_stats['Projected_7D_Demand'] = (sales_stats['Blended_Daily_Velocity'] * 7 * 1.15).round(0)

        # 4. Find what to order
        df_agent = pd.merge(in_summary, sales_stats, on='item_name', how='left').fillna(0)
        df_agent['Remaining_Stock'] = df_agent['Total_In'] - df_agent['quantity_total']
        df_agent['Suggested_Order_Qty'] = (df_agent['Projected_7D_Demand'] - df_agent['Remaining_Stock']).clip(lower=0)

        return df_agent[['item_name', 'Remaining_Stock', 'Projected_7D_Demand', 'Suggested_Order_Qty']].to_dict(orient='records')
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
