from bot.client import BinanceClient
from bot.logging_config import setup_logging
import time
import math

logger = setup_logging()

def place_market_order(client: BinanceClient, symbol: str, side: str, quantity: float) -> dict:
    logger.info(f"Placing MARKET order | symbol={symbol} side={side} qty={quantity}")
    response = client.place_order(symbol=symbol, side=side, order_type="MARKET", quantity=quantity)
    logger.info(f"Order response | {response}")
    return response

def place_limit_order(client: BinanceClient, symbol: str, side: str, quantity: float, price: float) -> dict:
    logger.info(f"Placing LIMIT order | symbol={symbol} side={side} qty={quantity} price={price}")
    response = client.place_order(symbol=symbol, side=side, order_type="LIMIT", quantity=quantity, price=price)
    logger.info(f"Order response | {response}")
    return response

def place_stop_limit_order(client: BinanceClient, symbol: str, side: str, quantity: float, price: float, stop_price: float) -> dict:
    logger.info(f"Placing STOP_LIMIT | symbol={symbol} side={side} qty={quantity} price={price} stop={stop_price}")
    response = client.place_order(
        symbol=symbol, side=side, order_type="STOP", quantity=quantity,
        price=price, stop_price=stop_price, time_in_force="GTC"
    )
    logger.info(f"Order response | {response}")
    return response

def execute_twap(client: BinanceClient, symbol: str, side: str, total_qty: float, slices: int, interval_seconds: int) -> list[dict]:
    """TWAP: split total_qty into equal slices placed at regular intervals"""
    slice_qty = round(total_qty / slices, 3)
    results = []
    logger.info(f"TWAP start | symbol={symbol} side={side} total={total_qty} slices={slices} interval={interval_seconds}s")
    for i in range(slices):
        logger.info(f"TWAP slice {i+1}/{slices} | qty={slice_qty}")
        result = place_market_order(client, symbol, side, slice_qty)
        results.append(result)
        if i < slices - 1:
            time.sleep(interval_seconds)
    logger.info(f"TWAP complete | {slices} orders placed")
    return results
