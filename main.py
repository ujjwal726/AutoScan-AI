from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Float, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import pandas as pd
import json
import io
import os
import random
from datetime import datetime, timedelta
from typing import Optional, List
import google.generativeai as genai
from groq import Groq
from PIL import Image

# --- CLOUD DATABASE CONNECTION ---
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- DATABASE MODELS ---
class Inventory(Base):
    __tablename__ = "inventory"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(String)
    item_name = Column(String)
    category = Column(String)
    quantity = Column(Float)
    unit_price = Column(Float)
    total = Column(Float)
    payment_mode = Column(String)

class Sales(Base):
    __tablename__ = "sales"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(String)
    item_name = Column(String)
    category = Column(String)
    quantity = Column(Float)
    unit_price = Column(Float)
    total = Column(Float)
    payment_mode = Column(String)

class Supplier(Base):
    __tablename__ = "suppliers"
    id = Column(Integer, primary_key=True, index=True)
    supplier_name = Column(String)
    item_name = Column(String)
    price_per_unit = Column(Float)
    distance_km = Column(Float)
    contact_info = Column(String)

Base.metadata.create_all(bind=engine)

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# --- AI & EXTRACTION ---
@app.post("/api/models")
def discover_models(payload: dict):
    try:
        if payload['provider'] == "Google Gemini":
            genai.configure(api_key=payload['api_key'])
            return {"models": [m.name.split('/')[-1] for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]}
        elif payload['provider'] == "Groq":
            client = Groq(api_key=payload['api_key'])
            return {"models": [m.id for m in client.models.list().data]}
        return {"models": []}
    except Exception as e: raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/extract")
async def extract_data(mode: str = Form(...), provider: str = Form(...), api_key: str = Form(...), 
                       model_name: str = Form(...), text_data: Optional[str] = Form(None), 
                       file: Optional[UploadFile] = File(None)):
    
    prompt = f"Extract {mode} into JSON array. Keys: date, item_name, category, quantity, unit_price, total, payment_mode."
    if mode == "suppliers": prompt = "Extract items/prices into JSON array. Keys: item_name, price_per_unit."
    
    contents = [prompt]
    if text_data: contents.append(text_data)
    elif file: contents.append(Image.open(io.BytesIO(await file.read())))

    try:
        if provider == "Google Gemini":
            genai.configure(api_key=api_key)
            res = genai.GenerativeModel(model_name).generate_content(contents)
            text = res.text
        else:
            client = Groq(api_key=api_key)
            res = client.chat.completions.create(model=model_name, messages=[{"role": "user", "content": str(contents)}])
            text = res.choices[0].message.content
        return json.loads(text.replace("```json", "").replace("```", "").strip())
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

# --- DASHBOARD & FORECAST ---
@app.get("/api/dashboard")
def get_dashboard():
    inv = pd.read_sql("SELECT * FROM inventory", engine)
    sales = pd.read_sql("SELECT * FROM sales", engine)
    metrics = {"investment": float(inv['total'].sum()) if not inv.empty else 0,
               "revenue": float(sales['total'].sum()) if not sales.empty else 0}
    metrics["balance"] = metrics["revenue"] - metrics["investment"]
    metrics["udhari"] = float(sales[sales['payment_mode'].str.contains('credit|udhari', case=False, na=False)]['total'].sum()) if not sales.empty else 0
    
    stock_in = inv.groupby('item_name')['quantity'].sum() if not inv.empty else pd.Series()
    stock_out = sales.groupby('item_name')['quantity'].sum() if not sales.empty else pd.Series()
    stock_final = (stock_in - stock_out).fillna(stock_in).to_dict()
    
    return {"metrics": metrics, "stock": stock_final}

@app.get("/api/forecast")
def get_forecast():
    sales = pd.read_sql("SELECT * FROM sales", engine)
    inv = pd.read_sql("SELECT * FROM inventory", engine)
    if sales.empty or inv.empty: return []
    sales['date'] = pd.to_datetime(sales['date'])
    cutoff = sales['date'].max() - pd.Timedelta(days=7)
    
    # Blended Velocity: 70% Recent Week / 30% Past Month
    out_total = sales.groupby('item_name')['quantity'].sum()
    out_recent = sales[sales['date'] >= cutoff].groupby('item_name')['quantity'].sum()
    in_total = inv.groupby('item_name')['quantity'].sum()

    results = []
    for item in in_total.index:
        total_s = out_total.get(item, 0); recent_s = out_recent.get(item, 0)
        remaining = in_total[item] - total_s
        vel = ((recent_s / 7) * 0.7) + (((total_s - recent_s) / 23) * 0.3)
        demand = round(vel * 7 * 1.15)
        results.append({"item_name": item, "stock": remaining, "demand": demand, "order": max(0, demand - remaining)})
    return results

@app.get("/api/smart-order")
def get_smart_order():
    forecast = get_forecast()
    suppliers = pd.read_sql("SELECT * FROM suppliers", engine)
    if not forecast or suppliers.empty: return []
    
    # Landed Cost = Price + (Distance * 2.0 transport factor)
    suppliers['landed'] = suppliers['price_per_unit'] + (suppliers['distance_km'] * 2.0)
    cheapest = suppliers.loc[suppliers.groupby('item_name')['landed'].idxmin()]
    
    final = []
    for f in forecast:
        if f['order'] > 0:
            match = cheapest[cheapest['item_name'] == f['item_name']]
            if not match.empty:
                final.append({"item": f['item_name'], "qty": f['order'], "supplier": match.iloc[0]['supplier_name'], 
                              "price": match.iloc[0]['price_per_unit'], "contact": match.iloc[0]['contact_info']})
    return final

# --- SYSTEM ACTIONS ---
@app.post("/api/save")
def save_data(payload: dict):
    db = SessionLocal()
    try:
        if payload['mode'] == 'stock': [db.add(Inventory(**i)) for i in payload['items']]
        elif payload['mode'] == 'sales': [db.add(Sales(**i)) for i in payload['items']]
        elif payload['mode'] == 'suppliers':
            db.query(Supplier).filter(Supplier.supplier_name == payload['supplier_name']).delete()
            [db.add(Supplier(supplier_name=payload['supplier_name'], distance_km=payload['distance_km'], **i)) for i in payload['items']]
        db.commit(); return {"status": "success"}
    finally: db.close()

@app.post("/api/simulate")
def run_simulation():
    db = SessionLocal()
    try:
        db.query(Inventory).delete(); db.query(Sales).delete(); db.query(Supplier).delete()
        items = [("Sugar", "Grocery", 38, 44), ("Atta 5kg", "Grains", 190, 220), ("Tea", "Grocery", 120, 145)]
        start_date = datetime.now() - timedelta(days=30)
        for n, c, b, s in items:
            db.add(Inventory(date=start_date.strftime("%Y-%m-%d"), item_name=n, category=c, quantity=200, unit_price=b, total=200*b, payment_mode="Cash"))
            for i in range(30):
                db.add(Sales(date=(start_date + timedelta(days=i)).strftime("%Y-%m-%d"), item_name=n, category=c, quantity=random.randint(2,6), unit_price=s, total=5*s, payment_mode="Cash"))
        db.add(Supplier(supplier_name="Nashik Mandi", item_name="Sugar", price_per_unit=37.0, distance_km=4.0, contact_info="9876543210"))
        db.commit(); return {"status": "success"}
    finally: db.close()

@app.post("/api/reset")
def reset_data():
    db = SessionLocal()
    try:
        db.query(Inventory).delete(); db.query(Sales).delete(); db.query(Supplier).delete(); db.commit()
        return {"status": "success"}
    finally: db.close()
