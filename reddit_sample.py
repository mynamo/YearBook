#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Synthetic Reddit activity so the Social page is demoable without an export.
Matches reddit_parsers' schema (ts, subreddit, kind, text, score, permalink, source).
"""

import numpy as np
import pandas as pd

SUBS = {
    "python": ("post", 8), "dataisbeautiful": ("post", 6), "MachineLearning": ("comment", 5),
    "AskReddit": ("comment", 10), "books": ("comment", 6), "Music": ("comment", 5),
    "personalfinance": ("post", 4), "cooking": ("comment", 5), "movies": ("comment", 7),
    "learnpython": ("comment", 6), "todayilearned": ("comment", 5), "gaming": ("comment", 4),
}
SNIPPETS = [
    "Has anyone tried this approach?", "Great write-up, thanks for sharing!",
    "This helped me a lot, appreciate it.", "Could you explain the last part?",
    "I built something similar last month.", "Underrated tip right here.",
    "Source? I'd love to read more.", "Wholesome update, congrats!",
    "Here's how I solved the same issue.", "Bookmarking this for later.",
]


def generate(n=520, year=2025, seed=11):
    rng = np.random.default_rng(seed)
    subs = list(SUBS)
    weights = np.array([SUBS[s][1] for s in subs], dtype=float)
    weights /= weights.sum()

    start = pd.Timestamp(year=year, month=1, day=1)
    rows = []
    for _ in range(n):
        doy = int(np.clip(rng.normal(190, 100), 0, 364))
        # evening-heavy activity
        hour = int(np.clip(rng.normal(20, 3) if rng.random() < 0.7 else rng.normal(12, 3), 0, 23))
        ts = start + pd.Timedelta(days=doy, hours=hour, minutes=int(rng.integers(0, 60)))
        sub = rng.choice(subs, p=weights)
        base_kind = SUBS[sub][0]
        kind = base_kind if rng.random() < 0.75 else ("comment" if base_kind == "post" else "post")
        text = f"[{sub}] discussion" if kind == "post" else str(rng.choice(SNIPPETS))
        # comments usually low score, posts occasionally high
        score = int(abs(rng.normal(25, 40))) if kind == "post" else int(abs(rng.normal(8, 15)))
        rows.append((ts, sub, kind, text, score, "", "Reddit (sample)"))

    df = pd.DataFrame(rows, columns=["ts", "subreddit", "kind", "text", "score", "permalink", "source"])
    return df.sort_values("ts").reset_index(drop=True)


if __name__ == "__main__":
    d = generate()
    print(d.shape)
    print(d["kind"].value_counts())
    print(d["subreddit"].value_counts().head())
