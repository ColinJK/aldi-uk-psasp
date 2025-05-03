#!/usr/bin/env python3
"""
main.py

ALDI UK Data Scraper & Shopping Planner
"""
import os
import subprocess
import re
import json

import pandas as pd
import gradio as gr
from sentence_transformers import SentenceTransformer
import faiss
from llama_cpp import Llama

# --- Constants & Configurations ---
CSV_PATH = "aldi_uk_groceries.csv"
MODEL_ENV = "LLAMA_MODEL_PATH"
DEFAULT_MODEL = (
    r"C:/Users/Colin/.lmstudio/models/tiiuae/"
    "Falcon3-3B-Instruct-GGUF/Falcon3-3B-Instruct-q4_0.gguf"
)
EMBED_MODEL_NAME = "all-MiniLM-L6-v2"
PAGE_TIMEOUT = 10
SCRAPER_SCRIPT = "scrape_aldi.py"

# --- Globals for RAG ---
embed_model = SentenceTransformer(EMBED_MODEL_NAME)
index = None
product_names = []

# --- Utility Functions ---
def load_catalog(path=CSV_PATH):
    """Load the product CSV and parse prices."""
    df = pd.read_csv(path)
    df["price_value"] = (
        df["price"].str.replace(r"[^\d\.]", "", regex=True)
        .astype(float)
    )
    return df


def rebuild_index(df):
    """Construct the FAISS index for semantic retrieval."""
    global index, product_names
    product_names = df["name"].tolist()
    embeddings = embed_model.encode(product_names, show_progress_bar=False)
    embeddings = embeddings.astype("float32")
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)


def initialize_llm():
    """Initialize the LLM client from environment or default path."""
    model_path = os.environ.get(MODEL_ENV, DEFAULT_MODEL)
    return Llama(model_path=model_path, n_ctx=2048, n_threads=4)

# --- Scraper Integration ---
def scrape_data():
    """
    Execute the external scraper script and rebuild the index.
    """
    if not os.path.exists(SCRAPER_SCRIPT):
        return "❌ `scrape_aldi.py` not found."
    proc = subprocess.run(
        ["python", SCRAPER_SCRIPT], capture_output=True, text=True
    )
    if proc.returncode != 0:
        return f"❌ Scrape failed:\n{proc.stderr.strip()}"
    try:
        df = load_catalog()
        rebuild_index(df)
        return f"✅ Scrape complete: {len(df)} products loaded."
    except Exception as e:
        return f"❌ Index rebuild error: {e}"

# --- Shopping Planner Logic ---
def plan_shopping(shopping_list: str, budget: float, llm):
    """
    Use RAG + LLM to select items within budget.
    """
    df = load_catalog()
    results = []
    total = 0.0

    for item in filter(None, map(str.strip, shopping_list.split(','))):
        # Retrieve top-5 semantically similar products
        emb = embed_model.encode([item])[0].astype("float32")
        _, idxs = index.search(emb.reshape(1, -1), 5)
        candidates = [
            {"name": product_names[i], "price": df.loc[i, "price_value"]}
            for i in idxs[0]
        ]
        # Filter by keyword match
        tokens = set(re.findall(r"\w+", item.lower()))
        filtered = [c for c in candidates if tokens & set(re.findall(r"\w+", c["name"].lower()))]
        cands = filtered or candidates
        # Prompt LLM
        remaining = budget - total
        prompt = (
            f"Budget remaining: £{remaining:.2f}\n"
            f"Item: {item}\n"
            "Choose the best match from the list below (name + price):\n"
        )
        prompt += "\n".join(f"- {c['name']} (£{c['price']:.2f})" for c in cands)
        prompt += (
            "\nReturn JSON:{ 'selected':'<name>', 'price':<price> } or OMIT."
        )
        resp = llm(prompt=prompt, max_tokens=200)["choices"][0]["text"]
        # Parse JSON
        try:
            js = resp[resp.index('{'):resp.rindex('}')+1]
            sel = json.loads(js)
        except Exception:
            sel = {}
        if sel.get('selected') and sel['selected'] != 'OMIT':
            name = sel['selected']
            price = float(re.sub(r"[^\d\.]", "", str(sel.get('price', 0))))
        else:
            best = min(cands, key=lambda x: x['price'])
            name, price = best['name'], best['price']
        results.append({"requested": item, "selected": name, "price": round(price, 2)})
        total += price
    # Budget summary
    if total <= budget:
        summary = f"✅ Total £{total:.2f} within £{budget:.2f}."
    elif total - budget <= 5:
        summary = f"⚠️ Total £{total:.2f} slightly over £{budget:.2f}."
    else:
        summary = f"❌ Total £{total:.2f} exceeds £{budget:.2f}."
    return pd.DataFrame(results), summary

# --- UI Construction ---
def create_ui():
    llm = initialize_llm()
    with gr.Blocks(title="ALDI UK Scraper & Planner", theme="default") as app:
        gr.Markdown("# 🛒 ALDI UK Scraper & Shopping Planner")

        with gr.Tab("Scrape Data"):
            with gr.Row():
                scrape_btn = gr.Button("Run Scraper", variant="primary")
                scrape_out = gr.Textbox(label="Status", interactive=False)
            scrape_btn.click(scrape_data, outputs=[scrape_out])

        with gr.Tab("Plan Shopping"):
            gr.Markdown("#### Enter your shopping list and budget below:")
            with gr.Row():
                list_in = gr.Textbox(label="Shopping List (comma-separated)")
                budget_in = gr.Number(label="Budget (£)", value=20.0)
            plan_btn = gr.Button("Plan Shopping", variant="primary")
            table = gr.Dataframe(headers=["requested", "selected", "price"], label="Your Basket")
            summary = gr.Markdown()
            plan_btn.click(lambda l,b: plan_shopping(l,b,llm), inputs=[list_in,budget_in], outputs=[table,summary])

    return app


def main():
    if os.path.exists(CSV_PATH):
        df = load_catalog()
        rebuild_index(df)
    ui = create_ui()
    ui.launch()


if __name__ == "__main__":
    main()
