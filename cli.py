import typer
import os
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint
from dotenv import load_dotenv
from bot.client import BinanceClient, BinanceAPIError
from bot.orders import place_market_order, place_limit_order, place_stop_limit_order, execute_twap
from bot.validators import validate_symbol, validate_side, validate_order_type, validate_quantity, validate_price, validate_stop_price
from bot.logging_config import setup_logging

load_dotenv()
app = typer.Typer(help="Binance Futures Testnet Trading Bot", add_completion=False)
console = Console()
logger = setup_logging()

def get_client() -> BinanceClient:
    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_API_SECRET")
    base_url = os.getenv("BINANCE_BASE_URL", "https://testnet.binancefuture.com")
    
    if api_key:
        api_key = api_key.strip()
    if api_secret:
        api_secret = api_secret.strip()
    if base_url:
        base_url = base_url.strip()

    if not api_key or not api_secret:
        console.print("[bold red]Error:[/] BINANCE_API_KEY and BINANCE_API_SECRET must be set in .env")
        raise typer.Exit(1)
    return BinanceClient(api_key, api_secret, base_url)

def print_order_summary(symbol, side, order_type, quantity, price=None, stop_price=None):
    table = Table(title="Order Request Summary", show_header=False, box=None)
    table.add_column("Field", style="bold")
    table.add_column("Value")
    table.add_row("Symbol", symbol)
    table.add_row("Side", f"[green]{side}[/]" if side == "BUY" else f"[red]{side}[/]")
    table.add_row("Type", order_type)
    table.add_row("Quantity", str(quantity))
    if price is not None:
        table.add_row("Price", str(price))
    if stop_price is not None:
        table.add_row("Stop Price", str(stop_price))
    console.print(Panel(table, border_style="blue"))

def print_order_response(response: dict):
    table = Table(title="Order Response", show_header=True, header_style="bold magenta")
    table.add_column("Field")
    table.add_column("Value")
    fields = ["orderId", "algoId", "symbol", "status", "side", "type", "origQty", "executedQty", "avgPrice", "price", "triggerPrice", "updateTime"]
    for field in fields:
        if field in response:
            table.add_row(field, str(response[field]))
    console.print(table)

@app.command()
def order(
    symbol: str = typer.Option(..., "--symbol", "-s", help="Trading pair e.g. BTCUSDT"),
    side: str = typer.Option(..., "--side", help="BUY or SELL"),
    order_type: str = typer.Option(..., "--type", "-t", help="MARKET, LIMIT, or STOP_LIMIT"),
    quantity: float = typer.Option(..., "--qty", "-q", help="Order quantity"),
    price: float = typer.Option(None, "--price", "-p", help="Limit price (required for LIMIT/STOP_LIMIT)"),
    stop_price: float = typer.Option(None, "--stop-price", help="Stop price (required for STOP_LIMIT)"),
):
    """Place a single order: MARKET, LIMIT, or STOP_LIMIT"""
    symbol = validate_symbol(symbol)
    side = validate_side(side)
    order_type = validate_order_type(order_type)
    quantity = validate_quantity(quantity)
    price = validate_price(price, order_type)
    stop_price = validate_stop_price(stop_price, order_type)

    print_order_summary(symbol, side, order_type, quantity, price, stop_price)
    client = get_client()

    try:
        if order_type == "MARKET":
            response = place_market_order(client, symbol, side, quantity)
        elif order_type == "LIMIT":
            response = place_limit_order(client, symbol, side, quantity, price)
        elif order_type == "STOP_LIMIT":
            response = place_stop_limit_order(client, symbol, side, quantity, price, stop_price)

        print_order_response(response)
        console.print("[bold green]✓ Order placed successfully[/]")

    except BinanceAPIError as e:
        logger.error(f"API error | code={e.code} message={e.message}")
        console.print(f"[bold red]✗ API Error {e.code}:[/] {e.message}")
        raise typer.Exit(1)
    except Exception as e:
        logger.error(f"Unexpected error | {e}")
        console.print(f"[bold red]✗ Error:[/] {str(e)}")
        raise typer.Exit(1)

@app.command()
def twap(
    symbol: str = typer.Option(..., "--symbol", "-s"),
    side: str = typer.Option(..., "--side"),
    total_qty: float = typer.Option(..., "--qty", "-q", help="Total quantity to split"),
    slices: int = typer.Option(5, "--slices", help="Number of time slices (default 5)"),
    interval: int = typer.Option(60, "--interval", help="Seconds between slices (default 60)"),
):
    """Execute a TWAP order — splits total quantity into equal time-based market orders"""
    symbol = validate_symbol(symbol)
    side = validate_side(side)
    total_qty = validate_quantity(total_qty)

    console.print(Panel(f"[bold]TWAP Order[/]\nSymbol: {symbol} | Side: {side} | Total: {total_qty} | Slices: {slices} | Interval: {interval}s", border_style="yellow"))

    if not typer.confirm(f"Execute {slices} orders of {round(total_qty/slices, 3)} each over {slices * interval}s?"):
        raise typer.Abort()

    client = get_client()
    try:
        results = execute_twap(client, symbol, side, total_qty, slices, interval)
        for i, r in enumerate(results, 1):
            console.print(f"[green]Slice {i}:[/] orderId={r.get('orderId')} status={r.get('status')} executedQty={r.get('executedQty')}")
        console.print(f"\n[bold green]✓ TWAP complete — {len(results)} orders placed[/]")
    except BinanceAPIError as e:
        console.print(f"[bold red]✗ API Error {e.code}:[/] {e.message}")
        raise typer.Exit(1)

@app.command()
def balance():
    """Show current testnet account balance"""
    client = get_client()
    try:
        balances = client.get_account_balance()
        table = Table(title="Account Balance (Testnet)", header_style="bold")
        table.add_column("Asset")
        table.add_column("Balance", justify="right")
        table.add_column("Available", justify="right")
        for b in balances:
            if float(b.get("balance", 0)) > 0:
                table.add_row(b["asset"], b["balance"], b.get("availableBalance", "-"))
        console.print(table)
    except BinanceAPIError as e:
        console.print(f"[bold red]✗ Error:[/] {e.message}")

if __name__ == "__main__":
    app()
