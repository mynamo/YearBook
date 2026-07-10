# Interactive Topic Modeling — Streamlit app

A live web version of my [TopicModeling project](https://github.com/mynamo/TopicModeling).
Paste text, upload a file, or use the bundled sample, and the app assigns topics to
your documents using **gensim LDA** with **NLTK** preprocessing.

## Run locally

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

The app opens at http://localhost:8501.

## Deploy free on Streamlit Community Cloud

1. Put `streamlit_app.py` and `requirements.txt` in a GitHub repo (see steps below).
2. Go to https://share.streamlit.io and sign in with GitHub.
3. Click **New app**, choose your repo, branch `main`, and main file `streamlit_app.py`.
4. Click **Deploy**. First build takes a few minutes while it installs dependencies
   and downloads the NLTK data. After that you get a public URL you can share.

## Files

- `streamlit_app.py` — the app (preprocessing + LDA + UI).
- `requirements.txt` — pinned dependencies that build cleanly on the free tier.

## Note on preprocessing

The original script used spaCy + NLTK. This version does the equivalent work
(tokenize → keep words longer than 4 chars → remove stopwords → WordNet
lemmatize) with **NLTK only**, because spaCy language-model downloads are the
most common cause of failed Streamlit Cloud builds. The LDA modeling is
unchanged from the original.
