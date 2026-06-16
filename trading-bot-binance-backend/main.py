import os
import time
import threading
import uuid
import logging
import typer
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from bot.client import BinanceClient, BinanceAPIError
from bot.logging_config import setup_logging
from bot.orders import place_market_order, place_limit_order, place_stop_limit_order
from bot.validators import (
    validate_symbol,
    validate_side,
    validate_order_type,
    validate_quantity,
    validate_price,
    validate_stop_price,
)

logger = setup_logging()
app = FastAPI(title="Binance Futures Trading Bot API")

# Enable CORS for local React dev server and Vercel deployments
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to frontend origin in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "Binance Futures Trading Bot REST API",
        "documentation": "/docs"
    }

def get_binance_client() -> BinanceClient:
    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_API_SECRET")
    base_url = os.getenv("BINANCE_BASE_URL", "https://testnet.binancefuture.com")
    
    if api_key:
        api_key = api_key.strip()
    if api_secret:
        api_secret = api_secret.strip()
        
    if not api_key or not api_secret:
        raise HTTPException(
            status_code=500,
            detail="BINANCE_API_KEY and BINANCE_API_SECRET must be configured in the backend .env"
        )
    return BinanceClient(api_key, api_secret, base_url)

# In-memory database to store TWAP progress
twap_tasks = {}

class OrderRequest(BaseModel):
    symbol: str
    side: str
    order_type: str = Field(alias="type")
    quantity: float
    price: float | None = None
    stop_price: float | None = Field(default=None, alias="stopPrice")

    class Config:
        populate_by_name = True

class TwapRequest(BaseModel):
    symbol: str
    side: str
    total_qty: float = Field(alias="qty")
    slices: int = 5
    interval: int = 60

    class Config:
        populate_by_name = True

@app.exception_handler(typer.BadParameter)
async def typer_validation_error_handler(request, exc: typer.BadParameter):
    return JSONResponse(
        status_code=400,
        content={"error": "Validation Error", "detail": exc.message}
    )

@app.exception_handler(BinanceAPIError)
async def binance_api_error_handler(request, exc: BinanceAPIError):
    return JSONResponse(
        status_code=400,
        content={"error": "Binance API Error", "code": exc.code, "detail": exc.message}
    )

@app.get("/api/balance")
def get_balance():
    client = get_binance_client()
    balances = client.get_account_balance()
    # Filter active balances
    active_balances = []
    for b in balances:
        if float(b.get("balance", 0)) > 0:
            active_balances.append({
                "asset": b["asset"],
                "balance": b["balance"],
                "available": b.get("availableBalance", "-")
            })
    return active_balances

@app.post("/api/order")
def create_order(req: OrderRequest):
    # Perform local validation checks
    symbol = validate_symbol(req.symbol)
    side = validate_side(req.side)
    order_type = validate_order_type(req.order_type)
    quantity = validate_quantity(req.quantity)
    price = validate_price(req.price, order_type)
    stop_price = validate_stop_price(req.stop_price, order_type)

    client = get_binance_client()
    
    if order_type == "MARKET":
        response = place_market_order(client, symbol, side, quantity)
    elif order_type == "LIMIT":
        response = place_limit_order(client, symbol, side, quantity, price)
    elif order_type == "STOP_LIMIT":
        response = place_stop_limit_order(client, symbol, side, quantity, price, stop_price)
    else:
        raise HTTPException(status_code=400, detail="Invalid order type")
        
    return {"message": "Order placed successfully", "response": response}

def run_twap_background(task_id: str, client: BinanceClient, symbol: str, side: str, total_qty: float, slices: int, interval: int):
    slice_qty = round(total_qty / slices, 3)
    logger.info(f"TWAP Task {task_id} started: symbol={symbol} qty={total_qty} slices={slices} interval={interval}s")
    
    for i in range(slices):
        if twap_tasks[task_id]["status"] == "CANCELLED":
            logger.info(f"TWAP Task {task_id} was cancelled.")
            return

        twap_tasks[task_id]["current_slice"] = i + 1
        try:
            logger.info(f"TWAP Task {task_id} running slice {i+1}/{slices} (qty={slice_qty})")
            res = place_market_order(client, symbol, side, slice_qty)
            twap_tasks[task_id]["orders"].append({
                "slice": i + 1,
                "orderId": res.get("orderId"),
                "status": res.get("status"),
                "executedQty": res.get("executedQty"),
                "timestamp": int(time.time() * 1000)
            })
        except Exception as e:
            logger.error(f"TWAP Task {task_id} failed on slice {i+1}: {e}")
            twap_tasks[task_id]["status"] = "FAILED"
            twap_tasks[task_id]["error"] = str(e)
            return

        if i < slices - 1:
            time.sleep(interval)
            
    twap_tasks[task_id]["status"] = "COMPLETED"
    logger.info(f"TWAP Task {task_id} finished successfully.")

@app.post("/api/twap")
def create_twap_order(req: TwapRequest, background_tasks: BackgroundTasks):
    symbol = validate_symbol(req.symbol)
    side = validate_side(req.side)
    total_qty = validate_quantity(req.total_qty)
    
    if req.slices <= 0:
        raise HTTPException(status_code=400, detail="Slices must be greater than 0")
    if req.interval <= 0:
        raise HTTPException(status_code=400, detail="Interval must be positive")

    client = get_binance_client()
    task_id = str(uuid.uuid4())[:8]
    
    twap_tasks[task_id] = {
        "id": task_id,
        "symbol": symbol,
        "side": side,
        "total_qty": total_qty,
        "slices": req.slices,
        "interval": req.interval,
        "current_slice": 0,
        "status": "RUNNING",
        "orders": [],
        "error": None,
        "timestamp": int(time.time() * 1000)
    }
    
    # Run TWAP sequence in a background thread to prevent blocking FastAPI
    threading.Thread(
        target=run_twap_background,
        args=(task_id, client, symbol, side, total_qty, req.slices, req.interval),
        daemon=True
    ).start()

    return {"message": "TWAP execution started", "task_id": task_id}

@app.get("/api/twap/status")
def get_twap_status():
    # Return tasks sorted by timestamp descending
    sorted_tasks = sorted(twap_tasks.values(), key=lambda x: x["timestamp"], reverse=True)
    return sorted_tasks

@app.delete("/api/twap/{task_id}")
def cancel_twap_order(task_id: str):
    if task_id not in twap_tasks:
        raise HTTPException(status_code=404, detail="TWAP task not found")
    
    if twap_tasks[task_id]["status"] == "RUNNING":
        twap_tasks[task_id]["status"] = "CANCELLED"
        return {"message": f"TWAP task {task_id} successfully cancelled"}
    else:
        return {"message": f"TWAP task {task_id} is not running (status: {twap_tasks[task_id]['status']})"}

@app.get("/api/logs")
def get_logs():
    log_path = "logs/trading_bot.log"
    if not os.path.exists(log_path):
        return {"logs": []}
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        # Return last 50 log lines
        return {"logs": [line.strip() for line in lines[-50:]]}
    except Exception as e:
        return {"error": str(e), "logs": []}
