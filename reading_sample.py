#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Synthetic reading history so the Reading page is demoable without an export.
Produces a DataFrame in reading_parsers' schema
(title, author, rating, pages, date_read, date_added, shelf, platform).
"""

import numpy as np
import pandas as pd

# (title, author, genre, pages)
BOOKS = [
    ("Project Hail Mary", "Andy Weir", "Sci-Fi", 496),
    ("The Fifth Season", "N.K. Jemisin", "Fantasy", 512),
    ("Klara and the Sun", "Kazuo Ishiguro", "Literary", 320),
    ("Educated", "Tara Westover", "Memoir", 334),
    ("Circe", "Madeline Miller", "Fantasy", 393),
    ("Dune", "Frank Herbert", "Sci-Fi", 688),
    ("The Song of Achilles", "Madeline Miller", "Fantasy", 378),
    ("Atomic Habits", "James Clear", "Nonfiction", 320),
    ("The Midnight Library", "Matt Haig", "Literary", 304),
    ("Piranesi", "Susanna Clarke", "Fantasy", 245),
    ("A Little Life", "Hanya Yanagihara", "Literary", 720),
    ("The Name of the Wind", "Patrick Rothfuss", "Fantasy", 662),
    ("Sapiens", "Yuval Noah Harari", "Nonfiction", 443),
    ("Normal People", "Sally Rooney", "Literary", 273),
    ("The Priory of the Orange Tree", "Samantha Shannon", "Fantasy", 848),
    ("Recursion", "Blake Crouch", "Sci-Fi", 336),
    ("Braiding Sweetgrass", "Robin Wall Kimmerer", "Nonfiction", 391),
    ("The Vanishing Half", "Brit Bennett", "Literary", 352),
    ("Babel", "R.F. Kuang", "Fantasy", 546),
    ("Tomorrow, and Tomorrow, and Tomorrow", "Gabrielle Zevin", "Literary", 401),
    ("Exhalation", "Ted Chiang", "Sci-Fi", 350),
    ("The Overstory", "Richard Powers", "Literary", 502),
    ("Mexican Gothic", "Silvia Moreno-Garcia", "Horror", 301),
    ("The Way of Kings", "Brandon Sanderson", "Fantasy", 1007),
    ("Crying in H Mart", "Michelle Zauner", "Memoir", 256),
    ("Hyperion", "Dan Simmons", "Sci-Fi", 482),
    ("The Secret History", "Donna Tartt", "Literary", 559),
    ("Uprooted", "Naomi Novik", "Fantasy", 435),
]


def generate(years=(2024, 2025), seed=7):
    rng = np.random.default_rng(seed)
    catalog = list(BOOKS)
    rng.shuffle(catalog)

    rows = []
    # Finished books, spread across the given years with a summer reading bump.
    n_read = 46
    for i in range(n_read):
        title, author, genre, pages = catalog[i % len(catalog)]
        year = rng.choice(years, p=[0.45, 0.55] if len(years) == 2 else None)
        month = int(np.clip(rng.normal(7, 3), 1, 12))  # summer-heavy
        day = int(rng.integers(1, 28))
        date_read = pd.Timestamp(year=int(year), month=month, day=day)
        date_added = date_read - pd.Timedelta(days=int(rng.integers(5, 200)))
        # Ratings skew positive; occasionally unrated.
        if rng.random() < 0.1:
            rating = np.nan
        else:
            rating = int(np.clip(round(rng.normal(4.0, 0.8)), 1, 5))
        rows.append((title, author, rating, pages, date_read, date_added, "read",
                     rng.choice(["Goodreads", "StoryGraph"], p=[0.7, 0.3])))

    # A couple currently-reading and a to-read backlog.
    for j in range(2):
        title, author, genre, pages = catalog[(n_read + j) % len(catalog)]
        rows.append((title, author, np.nan, pages, pd.NaT,
                     pd.Timestamp(year=max(years), month=int(rng.integers(1, 12)), day=5),
                     "currently-reading", "Goodreads"))
    for k in range(14):
        title, author, genre, pages = catalog[(n_read + 2 + k) % len(catalog)]
        rows.append((title, author, np.nan, pages, pd.NaT,
                     pd.Timestamp(year=max(years), month=int(rng.integers(1, 12)), day=12),
                     "to-read", "Goodreads"))

    df = pd.DataFrame(rows, columns=["title", "author", "rating", "pages",
                                     "date_read", "date_added", "shelf", "platform"])
    # attach genre for demo insights
    genre_map = {t: g for t, a, g, p in BOOKS}
    df["genre"] = df["title"].map(genre_map)
    return df


if __name__ == "__main__":
    d = generate()
    print(d.shape)
    print(d[d["shelf"] == "read"].head())
    print(d["shelf"].value_counts())
