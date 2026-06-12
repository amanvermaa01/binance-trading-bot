import os
import hmac
import hashlib
import time
import logging
import requests
from urllib.parse import urlencode
from dotenv import load_dotenv
from bot.logging_config import setup_logging

load_dotenv()
API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")
BASE_URL = os.getenv("BINANCE_BASE_URL", "https://testnet.binancefuture.com")

logger = setup_logging()

class BinanceAPIError(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"Binance API Error {code}: {message}")

class BinanceClient:
    def __init__(self, api_key: str, api_secret: str, base_url: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip("/")
        self.time_offset = self._get_time_offset()

    def _get_time_offset(self) -> int:
        url = f"{self.base_url}/fapi/v1/time"
        try:
            resp = requests.get(url, timeout=5)
            server_time = resp.json()["serverTime"]
            system_time = int(time.time() * 1000)
            offset = server_time - system_time
            logger.info(f"Synchronized with Binance server. Clock offset: {offset}ms")
            return offset
        except Exception as e:
            logger.warning(f"Failed to synchronize time with Binance server: {e}. Using offset 0.")
            return 0

    def _sign(self, params: dict) -> str:
        # HMAC-SHA256 signature of query string using api_secret
        query_string = urlencode(params)
        return hmac.new(self.api_secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

    def _headers(self) -> dict:
        return {
            "X-MBX-APIKEY": self.api_key,
            "Content-Type": "application/x-www-form-urlencoded"
        }

    def _mask_params(self, params: dict) -> dict:
        masked = params.copy()
        if "signature" in masked:
            masked["signature"] = "******"
        return masked

    def _handle_response(self, response: requests.Response) -> dict | list:
        try:
            data = response.json()
        except ValueError:
            logger.error(f"Non-JSON response received: {response.text}")
            raise BinanceAPIError(response.status_code, response.text)

        is_error = False
        code = response.status_code
        message = "Unknown error"

        if isinstance(data, dict):
            if "code" in data:
                val = data["code"]
                if (isinstance(val, int) and val < 0) or response.status_code != 200:
                    is_error = True
                    code = val
                    message = data.get("msg", "Error response containing code")
            elif response.status_code != 200:
                is_error = True
                message = data.get("msg", response.text)
        elif isinstance(data, list):
            if response.status_code != 200:
                is_error = True
                message = f"HTTP Error {response.status_code}"

        if is_error:
            logger.error(f"API error | code={code} message={message}")
            raise BinanceAPIError(code, message)

        return data

    def _get(self, endpoint: str, params: dict = {}, signed: bool = True) -> dict | list:
        url = f"{self.base_url}{endpoint}"
        req_params = params.copy()
        if signed:
            req_params["timestamp"] = int(time.time() * 1000) + self.time_offset
            req_params["recvWindow"] = 5000
            req_params["signature"] = self._sign(req_params)

        headers = self._headers()
        for attempt in range(1, 4):
            try:
                resp = requests.get(url, params=req_params, headers=headers, timeout=10)
                return self._handle_response(resp)
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                if attempt < 3:
                    logger.warning(f"Retrying request | attempt={attempt + 1} reason={type(e).__name__}")
                    time.sleep(1)
                else:
                    logger.error(f"Network failure | url={url} error={type(e).__name__}")
                    raise

    def _post(self, endpoint: str, params: dict = {}, signed: bool = True) -> dict | list:
        url = f"{self.base_url}{endpoint}"
        req_params = params.copy()
        if signed:
            req_params["timestamp"] = int(time.time() * 1000) + self.time_offset
            req_params["recvWindow"] = 5000
            req_params["signature"] = self._sign(req_params)

        headers = self._headers()
        for attempt in range(1, 4):
            try:
                resp = requests.post(url, data=req_params, headers=headers, timeout=10)
                return self._handle_response(resp)
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                if attempt < 3:
                    logger.warning(f"Retrying request | attempt={attempt + 1} reason={type(e).__name__}")
                    time.sleep(1)
                else:
                    logger.error(f"Network failure | url={url} error={type(e).__name__}")
                    raise

    def place_order(self, symbol, side, order_type, quantity, price=None, stop_price=None, time_in_force=None) -> dict:
        if order_type == "STOP":
            endpoint = "/fapi/v1/algoOrder"
            params = {
                "symbol": symbol,
                "side": side,
                "algoType": "CONDITIONAL",
                "type": "STOP",
                "quantity": quantity
            }
            if price is not None:
                params["price"] = price
            if stop_price is not None:
                params["triggerPrice"] = stop_price
            if time_in_force is not None:
                params["timeInForce"] = time_in_force
        else:
            endpoint = "/fapi/v1/order"
            params = {
                "symbol": symbol,
                "side": side,
                "type": order_type,
                "quantity": quantity
            }
            if order_type == "LIMIT":
                params["price"] = price
                params["timeInForce"] = "GTC"

        masked_params = self._mask_params(params)
        logger.info(f"Placing order | symbol={symbol} side={side} type={order_type} qty={quantity}")
        logger.info(f"Sending order request params: {masked_params}")
        
        response = self._post(endpoint, params=params, signed=True)
        
        # log full response after receiving
        logger.info(f"Order response | {response}")
        return response

    def get_exchange_info(self) -> dict:
        return self._get("/fapi/v1/exchangeInfo", signed=False)

    def get_account_balance(self) -> list:
        return self._get("/fapi/v2/balance", signed=True)
