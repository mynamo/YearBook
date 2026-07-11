#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Synthetic order history so the Shopping page is demoable without an export.
Matches shopping_parsers' schema (date, item, category, quantity, price, platform).
"""

import numpy as np
import pandas as pd

CATALOG = {
    "Electronics": [("USB-C Cable", 12), ("Wireless Mouse", 28), ("Phone Case", 18),
                    ("Bluetooth Speaker", 45), ("Laptop Stand", 35)],
    "Books": [("Paperback Novel", 15), ("Cookbook", 25), ("Notebook", 9),
              ("Tech Reference", 42)],
    "Home": [("Coffee Mug", 14), ("Throw Pillow", 22), ("LED Bulbs (4pk)", 19),
             ("Storage Bins", 30), ("Desk Lamp", 33)],
    "Groceries": [("Coffee Beans", 16), ("Olive Oil", 13), ("Snack Box", 24),
                  ("Tea Sampler", 20)],
    "Clothing": [("T-Shirt", 20), ("Socks (6pk)", 18), ("Running Shorts", 28),
                 ("Beanie", 22)],
    "Beauty": [("Face Cream", 26), ("Shampoo", 12), ("Sunscreen", 15)],
}
CAT_WEIGHT = {"Electronics": 5, "Books": 4, "Home": 6, "Groceries": 7,
              "Clothing": 4, "Beauty": 3}


def generate(n=180, year=2025, seed=23):
    rng = np.random.default_rng(seed)
    cats = list(CATALOG)
    w = np.array([CAT_WEIGHT[c] for c in cats], dtype=float)
    w /= w.sum()

    start = pd.Timestamp(year=year, month=1, day=1)
    rows = []
    for _ in range(n):
        # spending bumps around Nov/Dec (holidays)
        month = int(np.clip(rng.normal(7, 3.2), 1, 12))
        if rng.random() < 0.22:
            month = rng.choice([11, 12])
        day = int(rng.integers(1, 28))
        date = pd.Timestamp(year=year, month=month, day=day)

        cat = rng.choice(cats, p=w)
        item, base = CATALOG[cat][rng.integers(0, len(CATALOG[cat]))]
        qty = int(rng.choice([1, 1, 1, 2, 3], p=[0.6, 0.15, 0.1, 0.1, 0.05]))
        unit = round(base * rng.uniform(0.85, 1.25), 2)
        price = round(unit * qty, 2)
        platform = rng.choice(["Amazon", "Walmart"], p=[0.7, 0.3])
        rows.append((date, item, cat, qty, price, platform))

    df = pd.DataFrame(rows, columns=["date", "item", "category", "quantity", "price", "platform"])
    return df.sort_values("date").reset_index(drop=True)


if __name__ == "__main__":
    d = generate()
    print(d.shape, "| total spend:", round(d["price"].sum(), 2))
    print(d.groupby("category")["price"].sum().round(2))
