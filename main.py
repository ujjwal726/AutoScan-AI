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
from groq import Groq
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

# --- 2. DYNAMIC MODEL DISCOVERY ---
class ModelRequest(BaseModel):
    provider: str
    api_key: str

@app.post("/api/models")
def discover_models(payload: ModelRequest):
    try:
        if payload.provider == "Google Gemini":
            genai.configure(api_key=payload.api_key)
            # Find all models that support generating content
            models = [m.name.split('/')[-1] for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            return {"models": models}
            
        elif payload.provider == "Groq":
            client = Groq(api_key=payload.api_key)
            raw_models = client.models.list()
            # Filter for fast Llama/Mixtral/Gemma models
            models = sorted([m.id for m in raw_models.data if 'llama' in m.id or 'mixtral' in m.id or 'gemma' in m.id])
            return {"models": models}
            
        return {"models": []}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid API Key or Connection Error: {str(e)}")


# --- 3. AI EXTRACTION ENGINE (THE OCR ROUTE) ---
@app.post("/api/extract")
async def extract_data(
    mode: str = Form(...), # "stock", "sales", or "rate_card"
    provider: str = Form(...),
    api_key: str = Form(...),
    model_name: str = Form(...),
    text_data: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None)
):
    if mode in ["stock", "sales"]:
        system_prompt = """Extract the data and output ONLY a raw JSON array of objects.
        Each object MUST have exact keys: "date", "item_name", "category", "quantity", "unit_price", "total", "payment_mode".
        Output ONLY valid JSON. Normalization: Standard English names. Categories: [Grocery, Dairy, Personal Care, Household, Grains].
        quantity, unit_price, and total MUST be numbers."""
    else:
        system_prompt = """Extract items and prices from this rate card. Output ONLY a raw JSON array of objects.
        Keys MUST be exactly: "item_name", "price_per_unit".
        Output ONLY valid JSON. Normalization: Standard English names. Prices must be numbers."""

    contents = [system_prompt]
    if text_data:
        contents.append(text_data)
    elif file:
        image_bytes = await file.read()
        contents.append(Image.open(io.BytesIO(image_bytes)))
    else:
        raise HTTPException(status_code=400, detail="Must provide either text_data or a file.")

    try:
        result_text = ""
        if provider == "Google Gemini":
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(contents)
            result_text = response.text
            
        elif provider == "Groq":
            client = Groq(api_key=api_key)
            response = client.chat.completions.create(model=model_name, messages=[{"role": "user", "content": str(contents)}])
            result_text = response.choices[0].message.content

        clean_json = result_text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_json)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Processing Error: {str(e)}")

# --- 4. DATABASE WRITE OPERATIONS ---
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
        if payload.mode == "stock" or payload.mode == "sales":
            table = payload.mode # "stock" saves to inventory temporarily for this example logic, lets keep it strictly as inventory
            table_name = 'inventory' if payload.mode == 'stock' else 'sales'
            for item in payload.items:
                c.execute(f'''INSERT INTO {table_name} (date, item_name, category, quantity, unit_price, total, payment_mode)
                             VALUES (?, ?, ?, ?, ?, ?, ?)''', 
                          (item.get('date', 'Today'), item.get('item_name'), item.get('category', 'Other'), 
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

# --- 5. THE KIRANA MATH ENGINES (READ OPERATIONS) ---
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

        total_credit = 0.0
        if not df_sales.empty:
            credit_mask = df_sales['payment_mode'].str.contains('credit|udhari', case=False, na=False)
            total_credit = float(df_sales.loc[credit_mask, 'total'].sum())

        return {"investment": total_investment, "revenue": total_revenue, "balance": current_balance, "udhari": total_credit}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stock")
def get_stock_levels():
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
