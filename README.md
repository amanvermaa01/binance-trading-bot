# Binance Futures Testnet Trading Bot & Terminal Dashboard
![Live Routing Dashboard](trading-bot-binance-frontend/public/Screenshot%(84).png)

## Overview
A production-quality trading application that places Market, Limit, and Stop Limit orders on the Binance Futures USDT-M Testnet. The project features:
1. **Interactive CLI Bot**: A Python Typer CLI with structured Rich console output.
2. **REST API Backend**: A FastAPI web server that acts as a secure intermediary for executing trades, tracking TWAP progress, and streaming operations console logs.
3. **Web Terminal Dashboard**: A modern, interactive React TypeScript frontend built with Vite, utilizing a sleek dark-mode glassmorphism design.

---

## Directory Structure
```
trading-bot-binance/
  trading-bot-binance-backend/   ← Python CLI & FastAPI REST Server
    bot/
      client.py                  ← Binance REST API & signature client
      orders.py                  ← Order wrappers & TWAP slicing logic
      validators.py              ← Client-side validations & error logger
      logging_config.py          ← Rotating log handler setup
    main.py                      ← FastAPI main entrypoint
    cli.py                       ← Typer CLI main entrypoint
    requirements.txt             ← Python dependencies
  trading-bot-binance-frontend/  ← Vite React TypeScript Web Client
    src/
      App.tsx                    ← Trading terminal & console UI
      index.css                  ← Glassmorphism & layout styles
    package.json                 ← Frontend dependencies
    vercel.json                  ← Vercel deployment routing
  README.md                      ← Project documentation
```

---

## Prerequisites
- Python 3.9+
- Node.js 18+ (with npm)
- Binance Futures Testnet Account & API Credentials

---

## Installation & Setup

### 1. Backend Setup
1. Navigate to the backend directory:
   ```bash
   cd trading-bot-binance-backend
   ```
2. Install dependencies:
   ```bash
   pip install --user -r requirements.txt
   ```
3. Create a `.env` file from the template:
   ```bash
   cp .env.example .env
   ```
4. Edit `.env` and fill in your Testnet API keys:
   ```ini
   BINANCE_API_KEY=your_testnet_api_key_here
   BINANCE_API_SECRET=your_testnet_api_secret_here
   BINANCE_BASE_URL=https://testnet.binancefuture.com
   ```

### 2. Frontend Setup
1. Navigate to the frontend directory:
   ```bash
   cd ../trading-bot-binance-frontend
   ```
2. Install npm packages:
   ```bash
   npm install
   ```

---

## Running the Applications

### 1. Launching via Web Interface (Dashboard)
To run both the backend server and frontend dashboard concurrently:

1. **Start the Backend API** (from `trading-bot-binance-backend`):
   ```bash
   uvicorn main:app --port 8000
   ```
   *The Swagger interactive documentation will be available at `http://127.0.0.1:8000/docs`.*

2. **Start the Frontend Client** (from `trading-bot-binance-frontend`):
   ```bash
   npm run dev
   ```
   *Open your browser and navigate to `http://localhost:5173/` to interact with the dashboard.*

---

### 2. Launching via command-line (CLI)
You can place orders directly using the CLI from the `trading-bot-binance-backend` directory:

#### Balance Check
```bash
python cli.py balance
```

#### MARKET BUY
```bash
python cli.py order --symbol BTCUSDT --side BUY --type MARKET --qty 0.01
```

#### LIMIT SELL
```bash
python cli.py order --symbol ETHUSDT --side SELL --type LIMIT --qty 0.1 --price 3000
```

#### STOP_LIMIT BUY
```bash
python cli.py order --symbol BTCUSDT --side SELL --type STOP_LIMIT --qty 0.01 --price 64000 --stop-price 64500
```

#### TWAP Execution
Splits total quantity into equal slices placed at regular intervals:
```bash
python cli.py twap --symbol BTCUSDT --side BUY --qty 0.05 --slices 5 --interval 30
```

---

## Log File Location
All backend interactions and orders are logged in `trading-bot-binance-backend/logs/trading_bot.log`. The logs are displayed in real-time in the web console and configured to rotate when they reach 5MB.

---

## Security & Deployment

### Vercel Deployment
The React frontend is pre-configured with `vercel.json` for SPA routes.
1. Deploy `trading-bot-binance-frontend` to Vercel.
2. In the Vercel dashboard, configure the environment variable `VITE_API_URL` pointing to your deployed FastAPI backend URL.

### Security Boundaries
- **No Client Leakage**: The frontend does not handle or store API secrets. It forwards request parameters to the backend REST API.
- **Server-Side Signatures**: Signature computations using HMAC-SHA256 and API keys are executed safely inside the local backend process.
- **Key Safety Guidelines**: Keep withdrawals **disabled** on your Binance API Key settings, restrict key usage to whitelisted IP addresses, and ensure your backend `.env` files are excluded from Git.

---

## Assumptions
- Designed exclusively for the Binance Futures USDT-M Testnet.
- Quantities are entered in base asset units (e.g. BTC, ETH).
- STOP_LIMIT orders are mapped to the Binance Futures `STOP` order type with `GTC` time in force, requiring routing to the Algo Order endpoint `/fapi/v1/algoOrder`.

---

## Error Handling
- **Local Input Validation**: Boundary and parameter checks are evaluated before execution to prevent rate limit consumption.
- **API Exceptions**: Automatically parses negative Binance API codes and displays structured error status fields.
- **Network Failures**: Auto-retries requests on timeout or network disruptions up to 3 times.
