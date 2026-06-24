"""
kairon/engine/cost_engine.py
All 7 cost types from Document 07. Every recommendation passes through this
before showing a net profit figure. Negative net profit = move rejected.
"""
import math
import logging
from dataclasses import dataclass
from typing import Optional

from kairon.config import cfg

logger = logging.getLogger("kairon.costs")

# ── Broker commission rates (per-side) ────────────────────────────────────────
BROKER_COMMISSIONS = {
    "stocks":      0.0005,
    "crypto":      0.0010,
    "forex":       0.0002,
    "commodities": 0.0008,
    "bonds":       0.0003,
    "real_estate": 0.0005,
}

# ── Base spread rates ─────────────────────────────────────────────────────────
BASE_SPREAD = {
    "stocks":      0.0001,
    "crypto":      0.0015,
    "forex":       0.00015,
    "commodities": 0.0012,
    "bonds":       0.0008,
    "real_estate": 0.0010,
}

BASE_SLIPPAGE = {
    "stocks":      0.0005,
    "crypto":      0.0020,
    "forex":       0.0001,
    "commodities": 0.0010,
    "bonds":       0.0005,
    "real_estate": 0.0010,
}

# ── Crypto gas fees (flat USD) ────────────────────────────────────────────────
CRYPTO_GAS_FEES = {
    "BTC-USD": 2.50,
    "ETH-USD": 3.80,
    "SOL-USD": 0.001,
    "BNB-USD": 0.10,
    "XRP-USD": 0.0002,
    "default":  2.00,
}

# ── Wire fees ─────────────────────────────────────────────────────────────────
WIRE_FEES = {
    ("stocks",      "crypto"):       25.00,
    ("crypto",      "stocks"):       25.00,
    ("stocks",      "forex"):        15.00,
    ("forex",       "stocks"):       15.00,
    ("crypto",      "forex"):        30.00,
    ("forex",       "crypto"):       30.00,
    ("stocks",      "bonds"):         0.00,
    ("bonds",       "stocks"):        0.00,
    ("stocks",      "real_estate"):   0.00,
    ("real_estate", "stocks"):        0.00,
    ("stocks",      "commodities"):   0.00,
    ("commodities", "stocks"):        0.00,
    ("bonds",       "commodities"):   0.00,
    ("commodities", "bonds"):         0.00,
}

# ── FX conversion ─────────────────────────────────────────────────────────────
FX_CONVERSION_NEEDED = {
    ("stocks", "forex"),
    ("forex",  "stocks"),
    ("forex",  "crypto"),
    ("crypto", "forex"),
    ("bonds",  "forex"),
    ("forex",  "bonds"),
}
FX_CONVERSION_RATE = 0.0025

# ── Tax region rates (Document 21) ────────────────────────────────────────────
TAX_REGIONS = {
    "US":          {"short": 0.37, "long": 0.20, "year_days": 365},
    "UK":          {"short": 0.20, "long": 0.10, "year_days": 365},
    "Germany":     {"short": 0.26, "long": 0.26, "year_days": 0},   # flat regardless of holding
    "Australia":   {"short": 0.45, "long": 0.225, "year_days": 365},
    "Canada":      {"short": 0.27, "long": 0.27, "year_days": 0},   # 50% inclusion
    "Singapore":   {"short": 0.00, "long": 0.00,  "year_days": 0},
    "UAE":         {"short": 0.00, "long": 0.00,  "year_days": 0},
    "Custom":      {"short": cfg.short_term_tax_rate, "long": cfg.long_term_tax_rate,
                    "year_days": cfg.tax_year_days},
}


@dataclass
class CostBreakdown:
    amount_usd:           float
    broker_cost:          float
    spread_cost:          float
    slippage_cost:        float
    fx_conversion_cost:   float
    crypto_gas_cost:      float
    wire_cost:            float
    tax_cost:             float
    tax_type:             str
    total_cost_usd:       float
    total_cost_pct:       float
    break_even_return_pct: float
    tax_optimization:     Optional[dict]

    def to_dict(self) -> dict:
        return {
            "amount_usd":            round(self.amount_usd, 2),
            "broker_cost":           round(self.broker_cost, 2),
            "spread_cost":           round(self.spread_cost, 2),
            "slippage_cost":         round(self.slippage_cost, 2),
            "fx_conversion_cost":    round(self.fx_conversion_cost, 2),
            "crypto_gas_cost":       round(self.crypto_gas_cost, 2),
            "wire_cost":             round(self.wire_cost, 2),
            "tax_cost":              round(self.tax_cost, 2),
            "tax_type":              self.tax_type,
            "total_cost_usd":        round(self.total_cost_usd, 2),
            "total_cost_pct":        round(self.total_cost_pct, 4),
            "break_even_return_pct": round(self.break_even_return_pct, 4),
            "tax_optimization":      self.tax_optimization,
        }

    @property
    def waterfall_items(self) -> list[dict]:
        """Ordered list for the cost waterfall display."""
        return [
            {"label": "Broker fees (×2)",    "amount": -self.broker_cost,
             "applies": self.broker_cost > 0},
            {"label": "Spread + slippage",    "amount": -(self.spread_cost + self.slippage_cost),
             "applies": (self.spread_cost + self.slippage_cost) > 0},
            {"label": "FX conversion",         "amount": -self.fx_conversion_cost,
             "applies": self.fx_conversion_cost > 0},
            {"label": "Crypto gas fee",        "amount": -self.crypto_gas_cost,
             "applies": self.crypto_gas_cost > 0},
            {"label": "Wire/transfer fee",     "amount": -self.wire_cost,
             "applies": self.wire_cost > 0},
            {"label": "Capital gains tax",     "amount": -self.tax_cost,
             "applies": self.tax_cost > 0},
        ]


def calc_broker(amount: float, from_market: str, to_market: str) -> float:
    sell = amount * BROKER_COMMISSIONS.get(from_market, 0.001)
    buy  = amount * BROKER_COMMISSIONS.get(to_market,   0.001)
    return round(sell + buy, 2)


def calc_spread_slippage(amount: float, from_m: str, to_m: str,
                          vix: float = 14.2, is_news_event: bool = False) -> tuple[float, float]:
    if vix > 35:      vm = 5.0
    elif vix > 25:    vm = 2.5
    elif vix > 18:    vm = 1.5
    else:             vm = 1.0
    nm = 3.0 if is_news_event else 1.0
    mult = max(vm, nm)

    spread   = amount * mult * (BASE_SPREAD.get(from_m, 0.001)   + BASE_SPREAD.get(to_m, 0.001))
    slippage = amount * mult * (BASE_SLIPPAGE.get(from_m, 0.001) + BASE_SLIPPAGE.get(to_m, 0.001))
    return round(spread, 2), round(slippage, 2)


def calc_fx(amount: float, from_m: str, to_m: str) -> float:
    if (from_m, to_m) in FX_CONVERSION_NEEDED:
        return round(amount * FX_CONVERSION_RATE, 2)
    return 0.0


def calc_gas(to_asset: str, to_market: str, is_on_chain: bool = False) -> float:
    if to_market != "crypto":
        return 0.0
    gas = CRYPTO_GAS_FEES.get(to_asset, CRYPTO_GAS_FEES["default"])
    return round(gas, 2)


def calc_wire(from_m: str, to_m: str) -> float:
    return WIRE_FEES.get((from_m, to_m), 0.0)


def calc_tax(amount_usd: float, unrealized_gain_pct: float,
             holding_days: int, tax_region: str = "US",
             tax_loss_carryforward: float = 0.0) -> dict:
    gain = amount_usd * unrealized_gain_pct
    if gain <= 0:
        return {"tax_usd": 0.0, "tax_type": "No gain — no tax",
                "rate": 0.0, "optimization": None}

    taxable = max(0.0, gain - tax_loss_carryforward)
    if taxable == 0:
        return {"tax_usd": 0.0, "tax_type": f"Offset by carryforward",
                "rate": 0.0, "optimization": None}

    region = TAX_REGIONS.get(tax_region, TAX_REGIONS["US"])
    year_days = region["year_days"]
    is_long = (year_days > 0 and holding_days >= year_days)
    rate = region["long"] if is_long else region["short"]
    state_rate = cfg.state_tax_rate if tax_region == "US" else 0.0
    total_rate = rate + state_rate
    tax_usd = taxable * total_rate

    # Tax optimization alert
    opt = None
    if year_days > 0 and not is_long:
        days_to_long = year_days - holding_days
        if 0 < days_to_long <= 30:
            long_tax = taxable * (region["long"] + state_rate)
            short_tax = taxable * total_rate
            saving = short_tax - long_tax
            if saving > 100:
                opt = {
                    "action":  f"Wait {days_to_long} more days",
                    "saving":  round(saving, 2),
                    "message": (f"Waiting {days_to_long} days qualifies for long-term rate "
                                f"({region['long']:.0%} vs {region['short']:.0%}). "
                                f"Tax saving: ${saving:,.2f}"),
                }

    term = "Long-term" if is_long else "Short-term"
    return {
        "tax_usd":   round(tax_usd, 2),
        "tax_type":  f"{term} ({total_rate:.0%} combined rate)",
        "rate":      total_rate,
        "optimization": opt,
    }


def calculate_all_costs(
    amount_usd:           float,
    from_market:          str,
    to_market:            str,
    to_asset:             str    = "",
    holding_days:         int    = 0,
    unrealized_gain_pct:  float  = 0.0,
    vix:                  float  = 14.2,
    is_news_event:        bool   = False,
    is_on_chain:          bool   = False,
    tax_region:           str    = "US",
    tax_loss_carryforward: float = 0.0,
) -> CostBreakdown:
    broker  = calc_broker(amount_usd, from_market, to_market)
    spread, slippage = calc_spread_slippage(amount_usd, from_market, to_market, vix, is_news_event)
    fx      = calc_fx(amount_usd, from_market, to_market)
    gas     = calc_gas(to_asset, to_market, is_on_chain)
    wire    = calc_wire(from_market, to_market)
    tax_res = calc_tax(amount_usd, unrealized_gain_pct, holding_days, tax_region, tax_loss_carryforward)

    total = broker + spread + slippage + fx + gas + wire + tax_res["tax_usd"]
    total_pct = (total / amount_usd * 100) if amount_usd > 0 else 0.0

    return CostBreakdown(
        amount_usd=amount_usd,
        broker_cost=broker,
        spread_cost=spread,
        slippage_cost=slippage,
        fx_conversion_cost=fx,
        crypto_gas_cost=gas,
        wire_cost=wire,
        tax_cost=tax_res["tax_usd"],
        tax_type=tax_res["tax_type"],
        total_cost_usd=round(total, 2),
        total_cost_pct=round(total_pct, 4),
        break_even_return_pct=round(total_pct, 4),
        tax_optimization=tax_res.get("optimization"),
    )


def passes_minimum_profit(gross_return_pct: float, costs: CostBreakdown) -> tuple[bool, str]:
    net_pct = gross_return_pct - (costs.total_cost_pct / 100)
    min_pct = cfg.min_net_profit_pct
    if net_pct < 0:
        return False, f"Net profit negative ({net_pct:.3%}) after costs. Move rejected."
    if net_pct < min_pct:
        return False, f"Net profit {net_pct:.3%} below minimum {min_pct:.3%}. Wait for stronger signal."
    return True, f"Net profit {net_pct:.3%} exceeds minimum threshold. Proceed."
