import typer
from bot.logging_config import setup_logging

logger = setup_logging()

VALID_SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "AVAXUSDT"]
VALID_SIDES = ["BUY", "SELL"]
VALID_ORDER_TYPES = ["MARKET", "LIMIT", "STOP_LIMIT"]

def validate_symbol(symbol: str) -> str:
    if not symbol:
        reason = "Symbol cannot be empty"
        logger.error(f"Validation error | field=symbol value={symbol} reason={reason}")
        raise typer.BadParameter(reason)
    symbol_upper = symbol.upper()
    if symbol_upper not in VALID_SYMBOLS:
        reason = f"Symbol must be one of: {', '.join(VALID_SYMBOLS)}"
        logger.error(f"Validation error | field=symbol value={symbol} reason={reason}")
        raise typer.BadParameter(reason)
    return symbol_upper

def validate_side(side: str) -> str:
    if not side:
        reason = "Side cannot be empty"
        logger.error(f"Validation error | field=side value={side} reason={reason}")
        raise typer.BadParameter(reason)
    side_upper = side.upper()
    if side_upper not in VALID_SIDES:
        reason = f"Side must be one of: {', '.join(VALID_SIDES)}"
        logger.error(f"Validation error | field=side value={side} reason={reason}")
        raise typer.BadParameter(reason)
    return side_upper

def validate_order_type(order_type: str) -> str:
    if not order_type:
        reason = "Order type cannot be empty"
        logger.error(f"Validation error | field=order_type value={order_type} reason={reason}")
        raise typer.BadParameter(reason)
    ot_upper = order_type.upper()
    if ot_upper not in VALID_ORDER_TYPES:
        reason = f"Order type must be one of: {', '.join(VALID_ORDER_TYPES)}"
        logger.error(f"Validation error | field=order_type value={order_type} reason={reason}")
        raise typer.BadParameter(reason)
    return ot_upper

def validate_quantity(quantity: float) -> float:
    if quantity <= 0:
        reason = "must be positive"
        logger.error(f"Validation error | field=quantity value={quantity} reason={reason}")
        raise typer.BadParameter(f"Quantity must be positive: {quantity}")
    if quantity > 1000:
        reason = "must be <= 1000"
        logger.error(f"Validation error | field=quantity value={quantity} reason={reason}")
        raise typer.BadParameter(f"Quantity exceeds safety cap of 1000: {quantity}")
    return quantity

def validate_price(price: float | None, order_type: str) -> float | None:
    if order_type in ("LIMIT", "STOP_LIMIT") and price is None:
        reason = "Price is required for LIMIT orders"
        logger.error(f"Validation error | field=price value={price} reason={reason}")
        raise typer.BadParameter(reason)
    if price is not None and price <= 0:
        reason = "Price must be positive"
        logger.error(f"Validation error | field=price value={price} reason={reason}")
        raise typer.BadParameter(reason)
    return price

def validate_stop_price(stop_price: float | None, order_type: str) -> float | None:
    if order_type == "STOP_LIMIT" and stop_price is None:
        reason = "Stop price required for STOP_LIMIT orders"
        logger.error(f"Validation error | field=stop_price value={stop_price} reason={reason}")
        raise typer.BadParameter(reason)
    if stop_price is not None and stop_price <= 0:
        reason = "Stop price must be positive"
        logger.error(f"Validation error | field=stop_price value={stop_price} reason={reason}")
        raise typer.BadParameter(reason)
    return stop_price
