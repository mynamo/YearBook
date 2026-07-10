#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Synthetic listening-history generator so the Wrapped app is fully demoable
without a real export. Produces a normalized DataFrame in the same schema
parsers.py emits (ts, artist, track, album, ms_played, platform), with
realistic patterns: evening/commute peaks, weekend shifts, a handful of
favorite artists, and new artists appearing as the year goes on.
"""

import random
import numpy as np
import pandas as pd

CATALOG = {
    "Phoebe Bridgers": (["Motion Sickness", "Kyoto", "Punisher", "Scott Street", "Savior Complex"], "Punisher"),
    "Tame Impala": (["The Less I Know The Better", "Let It Happen", "Borderline", "Lost in Yesterday"], "Currents"),
    "SZA": (["Kill Bill", "Snooze", "Good Days", "Nobody Gets Me", "Low"], "SOS"),
    "Bad Bunny": (["Tití Me Preguntó", "Moscow Mule", "Me Porto Bonito", "Ojitos Lindos"], "Un Verano Sin Ti"),
    "Fleetwood Mac": (["Dreams", "The Chain", "Go Your Own Way", "Landslide"], "Rumours"),
    "Kendrick Lamar": (["HUMBLE.", "Money Trees", "N95", "Alright", "DNA."], "DAMN."),
    "Taylor Swift": (["Anti-Hero", "Cruel Summer", "August", "Cardigan", "Blank Space"], "Midnights"),
    "Radiohead": (["Weird Fishes", "Karma Police", "Reckoner", "No Surprises"], "In Rainbows"),
    "Frank Ocean": (["Ivy", "Pink + White", "Nights", "Thinkin Bout You"], "Blonde"),
    "Bonobo": (["Kerala", "Cirrus", "Kong", "Break Apart"], "Migration"),
    "Men I Trust": (["Show Me How", "Numb", "Tailwhip"], "Oncle Jazz"),
    "Khruangbin": (["White Gloves", "Maria También", "Time (You and I)"], "Con Todo El Mundo"),
    "Little Simz": (["Introvert", "Woman", "Gorilla"], "Sometimes I Might Be Introvert"),
    "Sufjan Stevens": (["Mystery of Love", "Should Have Known Better", "Chicago"], "Carrie & Lowell"),
}

# Popularity weights (some artists dominate the year)
WEIGHTS = np.array([9, 8, 8, 6, 5, 6, 7, 4, 5, 3, 4, 3, 3, 2], dtype=float)


def generate(n_plays=4200, year=2025, seed=42):
    random.seed(seed)
    rng = np.random.default_rng(seed)

    artists = list(CATALOG.keys())
    weights = WEIGHTS / WEIGHTS.sum()

    # Some artists are "discovered" partway through the year.
    debut_month = {a: 1 for a in artists}
    debut_month["Little Simz"] = 5
    debut_month["Khruangbin"] = 7
    debut_month["Men I Trust"] = 9

    start = pd.Timestamp(year=year, month=1, day=1)
    rows = []
    for _ in range(n_plays):
        # Day of year, slightly more listening in autumn/winter.
        doy = int(np.clip(rng.normal(210, 100), 0, 364))
        day = start + pd.Timedelta(days=doy)

        # Hour: bimodal — morning commute + strong evening peak.
        if rng.random() < 0.35:
            hour = int(np.clip(rng.normal(8.5, 1.5), 0, 23))
        else:
            hour = int(np.clip(rng.normal(20, 2.5), 0, 23))
        minute = rng.integers(0, 60)
        ts = day + pd.Timedelta(hours=hour, minutes=int(minute))

        # Pick an artist that has already "debuted" by this month.
        while True:
            artist = rng.choice(artists, p=weights)
            if debut_month[artist] <= ts.month:
                break

        tracks, album = CATALOG[artist]
        track = random.choice(tracks)

        # Duration: ~3.5 min average, with some skips (short plays).
        if rng.random() < 0.12:
            ms = int(rng.uniform(5_000, 40_000))       # skipped
        else:
            ms = int(rng.normal(210_000, 35_000))       # full-ish play
        ms = max(1000, ms)

        platform = rng.choice(
            ["Spotify", "Apple Music", "YouTube Music"], p=[0.6, 0.25, 0.15]
        )
        rows.append((ts, artist, track, album, ms, platform))

    df = pd.DataFrame(rows, columns=["ts", "artist", "track", "album", "ms_played", "platform"])
    return df.sort_values("ts").reset_index(drop=True)


if __name__ == "__main__":
    d = generate()
    print(d.shape)
    print(d.head())
    print(d["platform"].value_counts())
