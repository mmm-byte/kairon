"""
kairon/engine/portfolio.py
Portfolio loading and analysis (Document 13).
Browser-only model: only ticker symbols reach the server.
Quantities, prices, and gains are computed client-side.
"""
import csv
import io
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("kairon.portfolio")


BROKER_CSV_FORMATS = {
    "robinhood":    {"symbol": "Symbol", "qty": "Quantity",    "price": "Average Cost"},
    "coinbase":     {"symbol": "Asset",  "qty": "Quantity",    "price": "Cost Basis"},
    "fidelity":     {"symbol": "Symbol", "qty": "Quantity",    "price": "Cost Basis/Share"},
    "schwab":       {"symbol": "Symbol", "qty": "Quantity",    "price": "Price"},
    "ibkr":         {"symbol": "Symbol", "qty": "Quantity",    "price": "Cost"},
    "binance":      {"symbol": "Symbol", "qty": "Amount",      "price": "Average Price"},
    "generic":      {"symbol": None,     "qty": None,          "price": None},
}

DEMO_PORTFOLIOS = {
    "Conservative Investor": [
        {"ticker": "TLT",  "name": "20Y Treasury ETF", "quantity": 100, "avg_price": 92.00,  "days_held": 180},
        {"ticker": "GC=F", "name": "Gold",             "quantity": 5,   "avg_price": 2650.0, "days_held": 90},
        {"ticker": "LQD",  "name": "IG Corp Bond ETF", "quantity": 80,  "avg_price": 105.0,  "days_held": 120},
    ],
    "Balanced (Default)": [
        {"ticker": "SPY",  "name": "S&P 500 ETF",   "quantity": 50,  "avg_price": 520.0,  "days_held": 365},
        {"ticker": "TLT",  "name": "20Y Bonds ETF", "quantity": 60,  "avg_price": 94.0,   "days_held": 180},
        {"ticker": "GC=F", "name": "Gold",          "quantity": 8,   "avg_price": 2720.0, "days_held": 200},
    ],
    "Aggressive Growth": [
        {"ticker": "QQQ",     "name": "NASDAQ ETF", "quantity": 80,   "avg_price": 440.0, "days_held": 240},
        {"ticker": "BTC-USD", "name": "Bitcoin",    "quantity": 0.5,  "avg_price": 72000, "days_held": 60},
        {"ticker": "NVDA",    "name": "NVIDIA",     "quantity": 30,   "avg_price": 750.0, "days_held": 400},
    ],
    "Crypto Focus": [
        {"ticker": "BTC-USD", "name": "Bitcoin",  "quantity": 0.75, "avg_price": 68000, "days_held": 120},
        {"ticker": "ETH-USD", "name": "Ethereum", "quantity": 5.0,  "avg_price": 2800,  "days_held": 90},
        {"ticker": "SOL-USD", "name": "Solana",   "quantity": 50,   "avg_price": 130,   "days_held": 45},
    ],
    "All Equities": [
        {"ticker": "SPY",  "name": "S&P 500 ETF", "quantity": 60,  "avg_price": 510.0, "days_held": 500},
        {"ticker": "AAPL", "name": "Apple",        "quantity": 25,  "avg_price": 178.0, "days_held": 380},
        {"ticker": "NVDA", "name": "NVIDIA",       "quantity": 20,  "avg_price": 680.0, "days_held": 200},
        {"ticker": "TSLA", "name": "Tesla",        "quantity": 30,  "avg_price": 220.0, "days_held": 150},
        {"ticker": "AMZN", "name": "Amazon",       "quantity": 15,  "avg_price": 180.0, "days_held": 310},
    ],
}


@dataclass
class Holding:
    ticker:      str
    name:        str
    market:      str
    quantity:    float
    avg_price:   float
    days_held:   int
    # Computed fields
    current_price:   float = 0.0
    current_value:   float = 0.0
    cost_basis:      float = 0.0
    unrealized_gain: float = 0.0
    unrealized_pct:  float = 0.0
    pct_of_portfolio:float = 0.0
    is_long_term:    bool  = False
    tax_rate:        float = 0.37
    tax_label:       str   = "Short-term"
    errors:          list  = field(default_factory=list)

    def enrich(self, current_price: float, total_portfolio_value: float,
                tax_year_days: int = 365,
                short_rate: float = 0.37, long_rate: float = 0.20):
        """Fill in computed fields once current price is known."""
        self.current_price    = current_price
        self.current_value    = current_price * self.quantity
        self.cost_basis       = self.avg_price * self.quantity
        self.unrealized_gain  = self.current_value - self.cost_basis
        self.unrealized_pct   = (self.unrealized_gain / self.cost_basis
                                  if self.cost_basis > 0 else 0.0)
        self.pct_of_portfolio = (self.current_value / total_portfolio_value
                                  if total_portfolio_value > 0 else 0.0)
        self.is_long_term     = self.days_held >= tax_year_days
        self.tax_rate         = long_rate if self.is_long_term else short_rate
        self.tax_label        = "Long-term" if self.is_long_term else "Short-term"

    def to_dict(self) -> dict:
        return {
            "ticker":          self.ticker,
            "name":            self.name,
            "market":          self.market,
            "quantity":        self.quantity,
            "avg_price":       round(self.avg_price, 4),
            "current_price":   round(self.current_price, 4),
            "current_value":   round(self.current_value, 2),
            "cost_basis":      round(self.cost_basis, 2),
            "unrealized_gain": round(self.unrealized_gain, 2),
            "unrealized_pct":  round(self.unrealized_pct, 4),
            "pct_of_portfolio":round(self.pct_of_portfolio, 4),
            "days_held":       self.days_held,
            "is_long_term":    self.is_long_term,
            "tax_rate":        self.tax_rate,
            "tax_label":       self.tax_label,
            "errors":          self.errors,
        }


@dataclass
class Portfolio:
    holdings:       list[Holding] = field(default_factory=list)
    total_value:    float = 0.0
    total_cost:     float = 0.0
    total_gain:     float = 0.0
    total_gain_pct: float = 0.0
    cash:           float = 0.0

    def add_holding(self, h: Holding):
        self.holdings.append(h)

    def compute_totals(self):
        self.total_value = sum(h.current_value for h in self.holdings) + self.cash
        self.total_cost  = sum(h.cost_basis for h in self.holdings)
        self.total_gain  = self.total_value - self.total_cost - self.cash
        self.total_gain_pct = (self.total_gain / self.total_cost
                                if self.total_cost > 0 else 0.0)
        # Recompute pct_of_portfolio
        for h in self.holdings:
            h.pct_of_portfolio = (h.current_value / self.total_value
                                   if self.total_value > 0 else 0.0)

    def to_dict(self) -> dict:
        return {
            "holdings":        [h.to_dict() for h in self.holdings],
            "total_value":     round(self.total_value, 2),
            "total_cost":      round(self.total_cost, 2),
            "total_gain":      round(self.total_gain, 2),
            "total_gain_pct":  round(self.total_gain_pct, 4),
            "cash":            round(self.cash, 2),
            "n_holdings":      len(self.holdings),
        }


def parse_csv(content: str, broker: str = "generic") -> list[dict]:
    """
    Parse a broker CSV export into a list of raw holding dicts.
    Auto-detects column mapping where possible.
    """
    reader   = csv.DictReader(io.StringIO(content.strip()))
    headers  = reader.fieldnames or []
    fmt      = BROKER_CSV_FORMATS.get(broker.lower(), BROKER_CSV_FORMATS["generic"])

    # Auto-detect columns if generic
    sym_col  = fmt["symbol"]
    qty_col  = fmt["qty"]
    price_col = fmt["price"]

    if sym_col is None:
        for h in headers:
            hl = h.lower()
            if any(k in hl for k in ("symbol","ticker","asset","coin","name")):
                sym_col = h; break
    if qty_col is None:
        for h in headers:
            hl = h.lower()
            if any(k in hl for k in ("qty","quantity","amount","units","shares")):
                qty_col = h; break
    if price_col is None:
        for h in headers:
            hl = h.lower()
            if any(k in hl for k in ("cost","price","avg","average","basis")):
                price_col = h; break

    if not sym_col or not qty_col or not price_col:
        raise ValueError(
            f"Could not auto-detect columns. Found: {headers}. "
            f"Need: symbol, quantity, avg_price columns."
        )

    holdings = []
    for row in reader:
        try:
            sym = str(row.get(sym_col, "")).strip().upper()
            if not sym or sym in ("-", "TOTAL", "CASH", ""):
                continue
            qty   = float(str(row.get(qty_col, 0)).replace(",","").replace("$",""))
            price = float(str(row.get(price_col, 0)).replace(",","").replace("$",""))
            if qty <= 0 or price <= 0:
                continue
            holdings.append({"ticker": sym, "quantity": qty, "avg_price": price,
                              "days_held": 0})
        except (ValueError, KeyError):
            continue

    return holdings


def load_portfolio_from_holdings(
    raw_holdings: list[dict],
    cash: float = 0.0,
) -> Portfolio:
    """
    Given a list of {ticker, quantity, avg_price, days_held} dicts,
    fetch current prices and build a full Portfolio.
    Only ticker symbols go to the price fetch — no quantities or costs.
    """
    from kairon.data.market_data import fetch_ohlcv, ASSETS
    from kairon.config import cfg

    portfolio = Portfolio(cash=cash)

    # Pass 1: fetch prices (only tickers sent to server)
    tickers_needed = [h["ticker"] for h in raw_holdings]
    prices = {}
    for ticker in tickers_needed:
        data = fetch_ohlcv(ticker, period="5d")
        df   = data.get("df")
        if df is not None and not df.empty:
            prices[ticker] = float(df["close"].iloc[-1])
        else:
            prices[ticker] = raw_holdings[[h["ticker"] for h in raw_holdings].index(ticker)]["avg_price"]

    # Pass 2: build holdings with computed fields
    # Approximate total for pct calculations
    approx_total = sum(
        prices.get(h["ticker"], h["avg_price"]) * h["quantity"]
        for h in raw_holdings
    ) + cash

    for raw in raw_holdings:
        ticker = raw["ticker"]
        info   = ASSETS.get(ticker, {"name": ticker, "market": "stocks"})
        h = Holding(
            ticker=ticker,
            name=raw.get("name") or info["name"],
            market=info["market"],
            quantity=raw["quantity"],
            avg_price=raw["avg_price"],
            days_held=raw.get("days_held", 0),
        )
        price = prices.get(ticker, raw["avg_price"])
        h.enrich(price, approx_total,
                  tax_year_days=cfg.tax_year_days,
                  short_rate=cfg.short_term_tax_rate,
                  long_rate=cfg.long_term_tax_rate)
        portfolio.add_holding(h)

    portfolio.compute_totals()
    return portfolio


def load_demo_portfolio(name: str = "Balanced (Default)") -> Portfolio:
    holdings_raw = DEMO_PORTFOLIOS.get(name, DEMO_PORTFOLIOS["Balanced (Default)"])
    return load_portfolio_from_holdings(holdings_raw)


def detect_tax_optimisations(portfolio: Portfolio) -> list[dict]:
    """Find holdings approaching long-term threshold."""
    from kairon.config import cfg
    alerts = []
    for h in portfolio.holdings:
        days_to_lt = cfg.tax_year_days - h.days_held
        if 0 < days_to_lt <= 30 and h.unrealized_gain > 500:
            short_tax = h.unrealized_gain * (cfg.short_term_tax_rate + cfg.state_tax_rate)
            long_tax  = h.unrealized_gain * (cfg.long_term_tax_rate  + cfg.state_tax_rate)
            saving    = short_tax - long_tax
            if saving > 100:
                alerts.append({
                    "ticker":     h.ticker,
                    "name":       h.name,
                    "days_held":  h.days_held,
                    "days_to_lt": days_to_lt,
                    "gain":       round(h.unrealized_gain, 2),
                    "tax_saving": round(saving, 2),
                    "message": (f"Wait {days_to_lt} more days for long-term rate "
                                f"on {h.name} — save ${saving:,.0f} in tax"),
                })
    return alerts
