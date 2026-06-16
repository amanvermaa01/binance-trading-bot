import { useState, useEffect, useRef } from 'react';
import './App.css';

const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

interface Balance {
  asset: string;
  balance: string;
  available: string;
}

interface TwapOrder {
  slice: number;
  orderId: number;
  status: string;
  executedQty: string;
  timestamp: number;
}

interface TwapTask {
  id: string;
  symbol: string;
  side: string;
  total_qty: number;
  slices: number;
  interval: number;
  current_slice: number;
  status: string;
  orders: TwapOrder[];
  error: string | null;
}

const SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "AVAXUSDT"];

function App() {
  // Connection states
  const [serverConnected, setServerConnected] = useState<boolean>(false);
  
  // Data states
  const [balances, setBalances] = useState<Balance[]>([]);
  const [twapTasks, setTwapTasks] = useState<TwapTask[]>([]);
  const [logs, setLogs] = useState<string[]>([]);
  
  // Loading states
  const [loadingBalance, setLoadingBalance] = useState<boolean>(false);
  const [isPlacingOrder, setIsPlacingOrder] = useState<boolean>(false);

  // Form states
  const [side, setSide] = useState<'BUY' | 'SELL'>('BUY');
  const [orderType, setOrderType] = useState<string>('MARKET');
  const [symbol, setSymbol] = useState<string>('BTCUSDT');
  const [quantity, setQuantity] = useState<string>('');
  const [price, setPrice] = useState<string>('');
  const [stopPrice, setStopPrice] = useState<string>('');
  const [twapSlices, setTwapSlices] = useState<number>(5);
  const [twapInterval, setTwapInterval] = useState<number>(60);

  // Response displays
  const [orderResult, setOrderResult] = useState<any | null>(null);
  const [orderError, setOrderError] = useState<string | null>(null);

  const terminalEndRef = useRef<HTMLDivElement>(null);

  // Fetch balances
  const fetchBalances = async () => {
    setLoadingBalance(true);
    try {
      const res = await fetch(`${API_BASE}/api/balance`);
      if (res.ok) {
        const data = await res.json();
        setBalances(data);
        setServerConnected(true);
      } else {
        setServerConnected(false);
      }
    } catch (err) {
      setServerConnected(false);
      console.error("Failed to fetch balances:", err);
    } finally {
      setLoadingBalance(false);
    }
  };

  // Fetch TWAP tasks
  const fetchTwapTasks = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/twap/status`);
      if (res.ok) {
        const data = await res.json();
        setTwapTasks(data);
      }
    } catch (err) {
      console.error("Failed to fetch TWAP tasks:", err);
    }
  };

  // Fetch logs
  const fetchLogs = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/logs`);
      if (res.ok) {
        const data = await res.json();
        setLogs(data.logs || []);
      }
    } catch (err) {
      console.error("Failed to fetch logs:", err);
    }
  };

  // Place order
  const handlePlaceOrder = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsPlacingOrder(true);
    setOrderResult(null);
    setOrderError(null);

    const isTwap = orderType === 'TWAP';
    const endpoint = isTwap ? '/api/twap' : '/api/order';
    
    // Construct payload
    let payload: any = {
      symbol,
      side,
    };

    if (isTwap) {
      payload.qty = parseFloat(quantity);
      payload.slices = twapSlices;
      payload.interval = twapInterval;
    } else {
      payload.type = orderType;
      payload.quantity = parseFloat(quantity);
      if (orderType === 'LIMIT' || orderType === 'STOP_LIMIT') {
        payload.price = parseFloat(price);
      }
      if (orderType === 'STOP_LIMIT') {
        payload.stopPrice = parseFloat(stopPrice);
      }
    }

    try {
      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      
      const data = await res.json();
      if (res.ok) {
        setOrderResult(data);
        // Refresh balance and twap tasks
        fetchBalances();
        if (isTwap) fetchTwapTasks();
        // Clear forms
        setQuantity('');
        setPrice('');
        setStopPrice('');
      } else {
        setOrderError(data.detail || data.error || "Order execution failed");
      }
    } catch (err: any) {
      setOrderError(err.message || "Network connection failure to API");
    } finally {
      setIsPlacingOrder(false);
    }
  };

  // Cancel TWAP
  const handleCancelTwap = async (taskId: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/twap/${taskId}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        fetchTwapTasks();
      }
    } catch (err) {
      console.error("Failed to cancel TWAP:", err);
    }
  };

  // Run polls
  useEffect(() => {
    fetchBalances();
    fetchTwapTasks();
    fetchLogs();

    const balanceInterval = setInterval(fetchBalances, 15000);
    const twapIntervalId = setInterval(fetchTwapTasks, 3000);
    const logsIntervalId = setInterval(fetchLogs, 2000);

    return () => {
      clearInterval(balanceInterval);
      clearInterval(twapIntervalId);
      clearInterval(logsIntervalId);
    };
  }, []);

  // Auto-scroll terminal
  useEffect(() => {
    if (terminalEndRef.current) {
      terminalEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);

  // Determine line style
  const getLogLineClass = (line: string) => {
    const lower = line.toLowerCase();
    if (lower.includes('| error')) return 'terminal-line error';
    if (lower.includes('| warning')) return 'terminal-line warning';
    if (lower.includes('| info')) return 'terminal-line info';
    return 'terminal-line default';
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <div className="header-title-block">
          <h1>Binance Futures Terminal</h1>
          <p>USDT-M Futures Trading Terminal — Testnet Environment</p>
        </div>
        <div className="header-status-block">
          <div className="status-indicator">
            <div className={`status-dot ${serverConnected ? 'connected' : 'disconnected'}`}></div>
            <span>{serverConnected ? 'API Connect Active' : 'Disconnected'}</span>
          </div>
          <button 
            onClick={fetchBalances} 
            className={`refresh-btn ${loadingBalance ? 'spinning' : ''}`}
            title="Refresh Account Data"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/>
            </svg>
          </button>
        </div>
      </header>

      {/* Balances Display */}
      <section className="balances-grid">
        {['USDT', 'USDC', 'BTC'].map((asset) => {
          const bal = balances.find(b => b.asset === asset);
          return (
            <div key={asset} className={`balance-card ${asset.toLowerCase()}`}>
              <div className="balance-asset">{asset} Base</div>
              <div className="balance-val">{bal ? parseFloat(bal.balance).toFixed(2) : '0.00'}</div>
              <div className="balance-available">
                Available: {bal ? parseFloat(bal.available).toFixed(4) : '0.0000'} {asset}
              </div>
            </div>
          );
        })}
      </section>

      <div className="dashboard-grid">
        {/* Left Side: Order Terminal */}
        <section className="glass-card">
          <div className="card-title">
            <span>Trading Terminal</span>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>USDT-M Futures</span>
          </div>

          <form onSubmit={handlePlaceOrder} className="glass-card" style={{ padding: 0, border: 'none', background: 'transparent', boxShadow: 'none' }}>
            {/* BUY/SELL Toggle */}
            <div className="side-selector">
              <button 
                type="button" 
                onClick={() => setSide('BUY')} 
                className={`side-btn BUY ${side === 'BUY' ? 'active' : ''}`}
              >
                BUY / LONG
              </button>
              <button 
                type="button" 
                onClick={() => setSide('SELL')} 
                className={`side-btn SELL ${side === 'SELL' ? 'active' : ''}`}
              >
                SELL / SHORT
              </button>
            </div>

            {/* Symbol Selection */}
            <div className="form-group">
              <label>Trading Symbol</label>
              <select 
                value={symbol} 
                onChange={(e) => setSymbol(e.target.value)}
                className="form-select"
              >
                {SYMBOLS.map(sym => (
                  <option key={sym} value={sym}>{sym}</option>
                ))}
              </select>
            </div>

            {/* Order Type Selection */}
            <div className="form-group">
              <label>Order Type</label>
              <div className="form-tabs">
                {['MARKET', 'LIMIT', 'STOP_LIMIT', 'TWAP'].map(type => (
                  <button
                    key={type}
                    type="button"
                    onClick={() => {
                      setOrderType(type);
                      setOrderResult(null);
                      setOrderError(null);
                    }}
                    className={`tab-btn ${orderType === type ? 'active' : ''}`}
                  >
                    {type.replace('_', ' ')}
                  </button>
                ))}
              </div>
            </div>

            {/* Quantity input */}
            <div className="form-group">
              <label>Quantity</label>
              <div className="input-wrapper">
                <input 
                  type="number" 
                  step="any"
                  value={quantity}
                  onChange={(e) => setQuantity(e.target.value)}
                  placeholder="0.00"
                  className="form-input"
                  required
                />
                <span className="input-suffix">{symbol.replace('USDT', '').replace('USDC', '')}</span>
              </div>
            </div>

            {/* Limit Price (LIMIT & STOP_LIMIT) */}
            {(orderType === 'LIMIT' || orderType === 'STOP_LIMIT') && (
              <div className="form-group">
                <label>Limit Price</label>
                <div className="input-wrapper">
                  <input 
                    type="number" 
                    step="any"
                    value={price}
                    onChange={(e) => setPrice(e.target.value)}
                    placeholder="0.00"
                    className="form-input"
                    required
                  />
                  <span className="input-suffix">USDT</span>
                </div>
              </div>
            )}

            {/* Stop Price (STOP_LIMIT) */}
            {orderType === 'STOP_LIMIT' && (
              <div className="form-group">
                <label>Stop/Trigger Price</label>
                <div className="input-wrapper">
                  <input 
                    type="number" 
                    step="any"
                    value={stopPrice}
                    onChange={(e) => setStopPrice(e.target.value)}
                    placeholder="0.00"
                    className="form-input"
                    required
                  />
                  <span className="input-suffix">USDT</span>
                </div>
              </div>
            )}

            {/* TWAP Settings */}
            {orderType === 'TWAP' && (
              <>
                <div className="form-group">
                  <label>TWAP Slices</label>
                  <input 
                    type="number" 
                    min="2"
                    max="100"
                    value={twapSlices}
                    onChange={(e) => setTwapSlices(parseInt(e.target.value))}
                    className="form-input"
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Interval (seconds)</label>
                  <input 
                    type="number" 
                    min="5"
                    value={twapInterval}
                    onChange={(e) => setTwapInterval(parseInt(e.target.value))}
                    className="form-input"
                    required
                  />
                </div>
              </>
            )}

            <button 
              type="submit" 
              disabled={isPlacingOrder || !serverConnected}
              className={`submit-btn ${side}`}
            >
              {isPlacingOrder ? (
                <>
                  <div className="spinner"></div>
                  <span>Executing Transaction...</span>
                </>
              ) : (
                <span>Execute {side} Order</span>
              )}
            </button>
          </form>

          {/* Results display */}
          {(orderResult || orderError) && (
            <div className="response-panel">
              {orderResult && (
                <>
                  <div className="response-header">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="20 6 9 17 4 12"/>
                    </svg>
                    <span>{orderResult.message || "Execution Success"}</span>
                  </div>
                  <div className="response-grid">
                    {orderResult.task_id && (
                      <div className="response-row" style={{ gridColumn: 'span 2' }}>
                        <span>TWAP Task ID</span>
                        <span>{orderResult.task_id}</span>
                      </div>
                    )}
                    {orderResult.response && (
                      <>
                        <div className="response-row">
                          <span>Order ID</span>
                          <span>{orderResult.response.orderId || orderResult.response.algoId}</span>
                        </div>
                        <div className="response-row">
                          <span>Symbol</span>
                          <span>{orderResult.response.symbol}</span>
                        </div>
                        <div className="response-row">
                          <span>Side / Type</span>
                          <span>{side} {orderType}</span>
                        </div>
                        <div className="response-row">
                          <span>Status</span>
                          <span style={{ color: 'var(--color-buy)', fontWeight: 650 }}>
                            {orderResult.response.status || "TRIGGERED"}
                          </span>
                        </div>
                      </>
                    )}
                  </div>
                </>
              )}
              {orderError && (
                <>
                  <div className="response-header error">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                      <circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>
                    </svg>
                    <span>Execution Rejected</span>
                  </div>
                  <p style={{ color: 'var(--color-sell)', fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}>
                    {orderError}
                  </p>
                </>
              )}
            </div>
          )}
        </section>

        {/* Right Side: Active TWAPs and Live Logs */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
          
          {/* TWAP Monitor */}
          <section className="glass-card">
            <div className="card-title">
              <span>TWAP Execution Monitor</span>
              <span className="twap-status-badge" style={{ background: 'rgba(255,255,255,0.03)', color: 'var(--text-secondary)' }}>
                {twapTasks.length} Active Run(s)
              </span>
            </div>

            {twapTasks.length === 0 ? (
              <div style={{ color: 'var(--text-muted)', fontSize: '0.9rem', textAlign: 'center', padding: '1.5rem 0' }}>
                No background TWAP executions active. Use the form to start.
              </div>
            ) : (
              <div className="twap-list">
                {twapTasks.map((task) => {
                  const pct = Math.round((task.current_slice / task.slices) * 100);
                  const isFinished = task.status === 'COMPLETED';
                  
                  return (
                    <div key={task.id} className="twap-task-row">
                      <div className="twap-task-header">
                        <div className="twap-task-info">
                          <span className={`badge-side ${task.side}`}>{task.side}</span>
                          <span className="twap-task-symbol">{task.symbol}</span>
                          <span className="twap-task-qty">Qty: {task.total_qty}</span>
                        </div>
                        <span className={`twap-status-badge ${task.status}`}>
                          {task.status}
                        </span>
                      </div>

                      <div className="progress-container">
                        <div className="progress-labels">
                          <span>Progress: {task.current_slice} / {task.slices} slices</span>
                          <span>{pct}%</span>
                        </div>
                        <div className="progress-track">
                          <div 
                            className={`progress-fill ${isFinished ? 'completed' : ''}`}
                            style={{ width: `${pct}%` }}
                          ></div>
                        </div>
                      </div>

                      {task.error && (
                        <div style={{ color: 'var(--color-sell)', fontSize: '0.75rem', fontFamily: 'var(--font-mono)' }}>
                          Err: {task.error}
                        </div>
                      )}

                      {task.status === 'RUNNING' && (
                        <button 
                          onClick={() => handleCancelTwap(task.id)}
                          className="twap-cancel-btn"
                        >
                          Cancel Execution
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </section>

          {/* Live Logs */}
          <section className="glass-card">
            <div className="card-title">
              <span>Real-time Operations Console</span>
              <div style={{ display: 'flex', gap: '0.25rem', alignItems: 'center' }}>
                <span className="status-dot connected" style={{ width: 6, height: 6 }}></span>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Streaming</span>
              </div>
            </div>

            <div className="terminal-block">
              {logs.length === 0 ? (
                <div style={{ color: 'var(--text-muted)' }}>Connecting to console streaming endpoint...</div>
              ) : (
                logs.map((line, idx) => (
                  <div key={idx} className={getLogLineClass(line)}>
                    {line}
                  </div>
                ))
              )}
              <div ref={terminalEndRef}></div>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}

export default App;
