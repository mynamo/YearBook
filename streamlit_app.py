#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interactive Topic Modeling — Streamlit app
Based on the LDA topic modeling project by Aditi Kulkarni
https://github.com/mynamo/TopicModeling

This app reproduces the original gensim LDA workflow (tokenize -> filter ->
lemmatize -> build corpus -> train LDA -> show topics) but lets a visitor run
it live: paste text, upload a file, or load the bundled sample, then tune the
number of topics and words and see results and a chart.

Preprocessing note: the original script used spaCy + NLTK. spaCy language-model
downloads are the most common cause of failed Streamlit Community Cloud builds,
so this version does the same job (tokenize + WordNet lemmatization + stopword
removal) with NLTK only. Results are equivalent for demo purposes and the app
deploys reliably on the free tier.
"""

import re
import json
import io

import pandas as pd
import streamlit as st
import gensim
from gensim import corpora
import nltk
from nltk.corpus import wordnet as wn
from nltk.corpus import stopwords


# ----------------------------------------------------------------------------
# One-time NLTK data setup (cached so it only runs once per session)
# ----------------------------------------------------------------------------
@st.cache_resource
def setup_nltk():
    for pkg in ("stopwords", "wordnet", "omw-1.4"):
        try:
            nltk.download(pkg, quiet=True)
        except Exception:
            pass
    return set(stopwords.words("english"))


EN_STOP = setup_nltk()


# ----------------------------------------------------------------------------
# Preprocessing (mirrors prepare_text_for_lda from the original source_code.py)
# ----------------------------------------------------------------------------
TOKEN_RE = re.compile(r"[A-Za-z']+")


def get_lemma(word):
    """Group different forms of the same word — same as the original."""
    lemma = wn.morphy(word)
    return word if lemma is None else lemma


def tokenize(text):
    tokens = []
    for match in TOKEN_RE.findall(text.lower()):
        if match.startswith("@"):
            tokens.append("SCREEN_NAME")
        else:
            tokens.append(match)
    return tokens


def prepare_text_for_lda(text):
    tokens = tokenize(text)
    tokens = [t for t in tokens if len(t) > 4]          # drop short tokens
    tokens = [t for t in tokens if t not in EN_STOP]    # drop stopwords
    tokens = [get_lemma(t) for t in tokens]             # lemmatize
    return tokens


# ----------------------------------------------------------------------------
# LDA over a set of documents
# ----------------------------------------------------------------------------
def run_lda(documents, num_topics, num_words, passes=15):
    processed = [prepare_text_for_lda(doc) for doc in documents]
    processed = [p for p in processed if p]
    if not processed:
        return None, None, None, None

    dictionary = corpora.Dictionary(processed)
    corpus = [dictionary.doc2bow(text) for text in processed]

    lda = gensim.models.ldamodel.LdaModel(
        corpus,
        num_topics=num_topics,
        id2word=dictionary,
        passes=passes,
        random_state=42,
    )
    topics = lda.print_topics(num_topics=num_topics, num_words=num_words)
    return lda, dictionary, corpus, topics


def parse_topic_terms(topic_str):
    """Turn gensim's '0.045*"data" + 0.03*"model"' into [(term, weight), ...]."""
    pairs = []
    for chunk in topic_str.split("+"):
        chunk = chunk.strip()
        if "*" not in chunk:
            continue
        weight, term = chunk.split("*", 1)
        term = term.strip().strip('"')
        try:
            pairs.append((term, float(weight)))
        except ValueError:
            continue
    return pairs


# ----------------------------------------------------------------------------
# Input helpers
# ----------------------------------------------------------------------------
def documents_from_upload(uploaded):
    """Accept .txt (one doc per line), .csv (last text column), or .json (jsonl)."""
    name = uploaded.name.lower()
    raw = uploaded.read()
    text = raw.decode("utf-8", errors="ignore")

    if name.endswith(".json"):
        docs = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if isinstance(obj, dict):
                    docs.append(" ".join(str(v) for v in obj.values()))
                else:
                    docs.append(str(obj))
            except json.JSONDecodeError:
                docs.append(line)
        return docs

    if name.endswith(".csv"):
        df = pd.read_csv(io.StringIO(text))
        text_col = df.columns[-1]
        return df[text_col].astype(str).tolist()

    # default: treat as plain text, one document per non-empty line
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


SAMPLE_DOCS = [
    "The central bank raised interest rates again as inflation pressures the economy and markets react to tighter monetary policy.",
    "Investors watched quarterly earnings closely while stock prices swung on news about corporate revenue and profit margins.",
    "Researchers trained a deep neural network on large datasets to improve image recognition accuracy using GPUs.",
    "The machine learning model achieved better performance after tuning hyperparameters and adding more labeled training data.",
    "The national team secured victory in the championship final after a dramatic penalty shootout in front of thousands of fans.",
    "The striker scored twice and the coach praised the defensive lineup following the decisive league match on Saturday.",
    "Doctors reported that the new vaccine reduced infection rates and hospitalizations during the clinical trial across regions.",
    "Public health officials encouraged screening programs to detect disease early and improve long-term patient treatment outcomes.",
]


# ----------------------------------------------------------------------------
# UI
# ----------------------------------------------------------------------------
st.set_page_config(page_title="Topic Modeling Demo", page_icon="📊", layout="wide")

st.title("📊 Interactive Topic Modeling")
st.markdown(
    "Assign topics to a set of documents using **NLTK** and **gensim LDA** in Python. "
    "Based on my [TopicModeling project](https://github.com/mynamo/TopicModeling) — "
    "now runnable live. Load the sample, paste your own text, or upload a file."
)

with st.sidebar:
    st.header("Settings")
    num_topics = st.slider("Number of topics", 2, 10, 4)
    num_words = st.slider("Words per topic", 3, 12, 6)
    passes = st.slider("Training passes", 5, 50, 15,
                       help="More passes = more stable topics, slower.")
    st.markdown("---")
    st.caption("Built with gensim LDA. Preprocessing: NLTK tokenize + "
               "WordNet lemmatize + stopword removal.")

tab_sample, tab_paste, tab_upload = st.tabs(["Sample data", "Paste text", "Upload file"])

documents = None
source_label = ""

with tab_sample:
    st.write("Eight short documents spanning finance, machine learning, sports, and health.")
    if st.button("Run on sample data", type="primary"):
        documents = SAMPLE_DOCS
        source_label = "sample data"

with tab_paste:
    pasted = st.text_area(
        "One document per line",
        height=200,
        placeholder="Paste one document per line...",
    )
    if st.button("Run on pasted text"):
        documents = [ln.strip() for ln in pasted.splitlines() if ln.strip()]
        source_label = "pasted text"

with tab_upload:
    uploaded = st.file_uploader("Upload .txt, .csv, or .json", type=["txt", "csv", "json"])
    if uploaded is not None and st.button("Run on uploaded file"):
        documents = documents_from_upload(uploaded)
        source_label = uploaded.name


# ----------------------------------------------------------------------------
# Run + render
# ----------------------------------------------------------------------------
if documents is not None:
    if len(documents) < 2:
        st.warning("Please provide at least 2 documents (2 non-empty lines).")
    else:
        with st.spinner(f"Modeling {len(documents)} documents from {source_label}..."):
            lda, dictionary, corpus, topics = run_lda(
                documents, num_topics, num_words, passes
            )

        if lda is None:
            st.error(
                "No usable text after preprocessing. Try longer documents — "
                "the model keeps only words longer than 4 characters."
            )
        else:
            st.success(f"Found {num_topics} topics across {len(documents)} documents.")

            st.subheader("Discovered topics")
            cols = st.columns(2)
            for i, (topic_id, topic_str) in enumerate(topics):
                terms = parse_topic_terms(topic_str)
                with cols[i % 2]:
                    st.markdown(f"**Topic {topic_id + 1}**")
                    if terms:
                        chart_df = pd.DataFrame(terms, columns=["term", "weight"]).set_index("term")
                        st.bar_chart(chart_df)
                        st.caption(", ".join(t for t, _ in terms))

            st.subheader("Dominant topic per document")
            rows = []
            for doc, bow in zip(documents, corpus):
                if not bow:
                    continue
                dist = sorted(lda.get_document_topics(bow), key=lambda x: x[1], reverse=True)
                top_id, top_prob = dist[0]
                preview = doc if len(doc) <= 90 else doc[:87] + "..."
                rows.append({
                    "Document": preview,
                    "Top topic": f"Topic {top_id + 1}",
                    "Confidence": f"{top_prob:.0%}",
                })
            if rows:
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
else:
    st.info("Pick a tab above and click a run button to see topics.")
