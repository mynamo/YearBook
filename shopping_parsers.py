#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Parsers for shopping / order-history exports.

Amazon: "Request My Data" → Retail.OrderHistory CSV.
Walmart: account/order-history CSV (format varies, so matched fuzzily).
Also a generic CSV fallback for any other retailer (Target, etc.).

Normalized schema:

    date      : datetime
    item      : str
    category  : str  (may be "")
    quantity  : float
    price     : float  (line/order total in the export's currency)
    platform  : str  ("Amazon" | "Walmart" | "Other")

`parse_orders(filename, raw)` sniffs the source; `load_shopping_files` combines.
"""

import io
import re

import pandas as pd

COLUMNS = ["date", "item", "category", "quantity", "price", "platform"]


def _empty():
    return pd.DataFrame(columns=COLUMNS)


def _find_col(cols, *cands):
    norm = {re.sub(r"[^a-z0-9]", "", c.lower()): c for c in cols}
    for cand in cands:
        key = re.sub(r"[^a-z0-9]", "", cand.lower())
        if key in norm:
            return norm[key]
    for cand in cands:
        key = re.sub(r"[^a-z0-9]", "", cand.lower())
        for nk, orig in norm.items():
            if key and key in nk:
                return orig
    return None


def _money(series):
    """Coerce '$12.34', '12,34', '1,234.56' → float."""
    s = series.astype(str).str.replace(r"[^0-9.\-]", "", regex=True)
    return pd.to_numeric(s, errors="coerce")


def _build(df, c_date, c_item, c_qty, c_price, c_cat, platform):
    out = pd.DataFrame({
        "date": pd.to_datetime(df[c_date], errors="coerce", utc=True).dt.tz_localize(None),
        "item": df[c_item].astype(str) if c_item else "",
        "category": df[c_cat].astype(str) if c_cat else "",
        "quantity": pd.to_numeric(df[c_qty], errors="coerce").fillna(1) if c_qty else 1.0,
        "price": _money(df[c_price]) if c_price else float("nan"),
        "platform": platform,
    })
    out = out[out["date"].notna()]
    out = out[out["item"].astype(str).str.strip().replace("nan", "") != ""]
    return out[COLUMNS]


def parse_amazon(df):
    cols = list(df.columns)
    c_date = _find_col(cols, "Order Date", "Ship Date", "Shipment Date")
    c_item = _find_col(cols, "Product Name", "Title", "Item Name")
    c_qty = _find_col(cols, "Quantity")
    c_price = _find_col(cols, "Total Owed", "Item Total", "Item Subtotal",
                        "Purchase Price Per Unit", "Unit Price")
    c_cat = _find_col(cols, "Category", "Product Category")
    if c_date is None or c_item is None:
        return _empty()
    return _build(df, c_date, c_item, c_qty, c_price, c_cat, "Amazon")


def parse_walmart(df):
    cols = list(df.columns)
    c_date = _find_col(cols, "Order Date", "Purchase Date", "Date")
    c_item = _find_col(cols, "Product Name", "Item", "Description", "Title")
    c_qty = _find_col(cols, "Quantity", "Qty")
    c_price = _find_col(cols, "Total", "Item Price", "Price", "Amount")
    c_cat = _find_col(cols, "Category", "Department")
    if c_date is None or c_item is None:
        return _empty()
    return _build(df, c_date, c_item, c_qty, c_price, c_cat, "Walmart")


def parse_generic(df):
    cols = list(df.columns)
    c_date = _find_col(cols, "Order Date", "Purchase Date", "Date", "Transaction Date")
    c_item = _find_col(cols, "Product Name", "Item", "Description", "Title", "Product")
    if c_date is None or c_item is None:
        return _empty()
    c_qty = _find_col(cols, "Quantity", "Qty")
    c_price = _find_col(cols, "Total", "Price", "Amount", "Cost", "Item Total")
    c_cat = _find_col(cols, "Category", "Department", "Type")
    return _build(df, c_date, c_item, c_qty, c_price, c_cat, "Other")


def parse_orders(filename, raw):
    name = (filename or "").lower()
    text = raw.decode("utf-8-sig", errors="ignore")
    try:
        df = pd.read_csv(io.StringIO(text))
    except Exception:
        return _empty()
    if df.empty:
        return _empty()

    cols_lower = {c.lower() for c in df.columns}
    if "amazon" in name or "orderhistory" in name.replace(".", "") or "total owed" in cols_lower:
        parsed = parse_amazon(df)
    elif "walmart" in name:
        parsed = parse_walmart(df)
    else:
        parsed = parse_generic(df)
    if parsed.empty:  # last-ditch: try the others
        parsed = parse_amazon(df)
        if parsed.empty:
            parsed = parse_generic(df)
    return parsed.reset_index(drop=True)


def load_shopping_files(uploads):
    frames, report = [], []
    for up in uploads:
        raw = up.read()
        df = parse_orders(up.name, raw)
        report.append((up.name, len(df),
                       df["platform"].iloc[0] if len(df) else "unrecognized"))
        if len(df):
            frames.append(df)
    if not frames:
        return _empty(), report
    combined = pd.concat(frames, ignore_index=True).sort_values("date").reset_index(drop=True)
    return combined, report
