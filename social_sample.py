#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Synthetic multi-platform social activity (Reddit + Twitter + Instagram) so the
Social page demos without any export. Matches social_parsers' schema
(ts, platform, kind, channel, text, engagement, permalink, source).
"""

import numpy as np
import pandas as pd

SUBS = ["python", "dataisbeautiful", "AskReddit", "books", "movies", "MachineLearning",
        "cooking", "personalfinance", "learnpython", "gaming"]
TWEETS = [
    "shipping a new side project today #python #buildinpublic",
    "hot take: notebooks are underrated #datascience",
    "the coffee-to-code ratio is off the charts today ☕",
    "reading more this year is paying off #books",
    "anyone else obsessed with clean charts? #dataviz",
    "weekend project incoming #coding",
]
IG_CAPS = ["golden hour 🌅", "weekend hike views", "homemade ramen night 🍜",
           "new plant, who dis 🌱", "sunday reset ✨", "concert lights 🎶"]


def generate(year=2025, seed=17):
    rng = np.random.default_rng(seed)
    start = pd.Timestamp(year=year, month=1, day=1)
    rows = []

    def ts():
        doy = int(np.clip(rng.normal(190, 100), 0, 364))
        hour = int(np.clip(rng.normal(20, 3) if rng.random() < 0.7 else rng.normal(12, 3), 0, 23))
        return start + pd.Timedelta(days=doy, hours=hour, minutes=int(rng.integers(0, 60)))

    # Reddit
    for _ in range(320):
        sub = str(rng.choice(SUBS))
        kind = "post" if rng.random() < 0.3 else "comment"
        eng = int(abs(rng.normal(30, 45))) if kind == "post" else int(abs(rng.normal(9, 15)))
        rows.append((ts(), "Reddit", kind, sub,
                     f"[{sub}] discussion" if kind == "post" else "great point, agreed",
                     eng, "", "Reddit (sample)"))
    # Twitter
    for _ in range(150):
        kind = str(rng.choice(["tweet", "reply", "retweet"], p=[0.6, 0.25, 0.15]))
        rows.append((ts(), "Twitter", kind, "", str(rng.choice(TWEETS)),
                     int(abs(rng.normal(12, 25))), "", "Twitter (sample)"))
    # Instagram
    for _ in range(60):
        rows.append((ts(), "Instagram", "post", "", str(rng.choice(IG_CAPS)),
                     int(abs(rng.normal(80, 60))), "", "Instagram (sample)"))

    df = pd.DataFrame(rows, columns=["ts", "platform", "kind", "channel", "text",
                                     "engagement", "permalink", "source"])
    return df.sort_values("ts").reset_index(drop=True)


if __name__ == "__main__":
    d = generate()
    print(d.shape)
    print(d["platform"].value_counts())
