#!/usr/bin/env python3
"""
main.py

Single-page ALDI UK data scraper and shopping planner.
"""
import os
import subprocess
import re
import json

import pandas as pd
import gradio as gr

# RAG & LLM imports
from sentence_transformers import SentenceTransformer
import faiss
from llama_cpp import Llama

# Constants
CSV_PATH = "aldi_uk_groceries.csv"
MODEL_ENV = "LLAMA_MODEL_PATH"
DEFAULT_MODEL = (
    r"C:/Users/Colin/.lmstudio/models/tiiuae/"
    "Falcon3-3B-Instruct-GGUF/Falcon3-3B-Instruct-q4_0.gguf"
)
EMBED_MODEL_NAME = "all-MiniLM-L6-v2"

# Globals for FAISS index
embed_model = SentenceTransformer(EMBED_MODEL_NAME)
index = None
product_names = []


def load_catalog(path=CSV_PATH):
    """Load the product CSV and parse prices."""
    df = pd.read_csv(path)
    df["price_value"] = (
        df["price"]
          .str.replace(r"[^\d\.]", "", regex=True)
          .astype(float)
    )
    return df


def rebuild_index(df):
    """Build or rebuild the FAISS index from the DataFrame."""
    global index, product_names
    product_names = df["name"].tolist()
    embeddings = embed_model.encode(product_names, show_progress_bar=False)
    embeddings = embeddings.astype("float32")
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)


def initialize_llm():
    """Initialize and return the local LLM client."""
    model_path = os.environ.get(MODEL_ENV, DEFAULT_MODEL)
    return Llama(model_path=model_path, n_ctx=2048, n_threads=4)


def scrape_data():
    """
    Run the ALDI scraper script and rebuild the FAISS index.
    Returns a status message.
    """
    if not os.path.exists("scrape_aldi.py"):
        return "Error: scrape_aldi.py not found."

    result = subprocess.run(
        ["python", "scrape_aldi.py"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        return f"❌ Scrape failed:\n{result.stderr.strip()}"

    try:
        df = load_catalog()
        rebuild_index(df)
        return f"✅ Scrape successful: {len(df)} products loaded."
    except Exception as e:
        return f"❌ Indexing error: {e}"


def plan_shopping(shopping_list: str, budget: float, llm):
    """
    Generate a shopping plan using RAG + LLM.
    Returns a DataFrame and a summary message.
    """
    df = load_catalog()
    selection = []
    total = 0.0

    for item in [i.strip() for i in shopping_list.split(",") if i.strip()]:
        # Retrieve top-5 semantically similar products
        q_emb = embed_model.encode([item])[0].astype("float32")
        _, indices = index.search(q_emb.reshape(1, -1), 5)
        raw_cands = [
            {"name": product_names[idx], "price": df.loc[idx, "price_value"]}
            for idx in indices[0]
        ]
        # Keyword filter
        tokens = set(re.findall(r"\w+", item.lower()))
        filtered = [
            c for c in raw_cands
            if tokens & set(re.findall(r"\w+", c["name"].lower()))
        ]
        cands = filtered or raw_cands

        # Prompt the LLM
        remaining = budget - total
        prompt = (
            f"Budget remaining: £{remaining:.2f}\n"
            f"User wants: {item}\n"
            "Select best match from:\n"
        )
        for c in cands:
            prompt += f"- {c['name']} (£{c['price']:.2f})\n"
        prompt += (
            "Reply with JSON {\"selected\":<name>,\"price\":<price>} or OMIT."
        )

        resp = llm(prompt=prompt, max_tokens=200)["choices"][0]["text"]
        # Extract JSON
        try:
            js = resp[resp.index("{"):resp.rindex("}")+1]
            data = json.loads(js)
        except Exception:
            data = {}

        if data.get("selected") and data["selected"] != "OMIT":
            sel_name = data["selected"]
            sel_price = float(
                re.sub(r"[^\d\.]", "", str(data.get("price", "0")))
            )
        else:
            best = min(cands, key=lambda x: x["price"])
            sel_name, sel_price = best["name"], best["price"]

        selection.append({
            "requested": item,
            "selected": sel_name,
            "price": round(sel_price, 2)
        })
        total += sel_price

    # Final budget message
    if total <= budget:
        msg = f"✅ Total £{total:.2f} within £{budget:.2f}."
    elif total - budget <= 5:
        msg = f"⚠️ Total £{total:.2f} slightly over £{budget:.2f}."
    else:
        msg = f"❌ Total £{total:.2f} exceeds £{budget:.2f}."

    return pd.DataFrame(selection), msg


def build_ui():
    """Construct and return the Gradio interface."""
    llm = initialize_llm()
    with gr.Blocks() as app:
        gr.Markdown("# ALDI Scraper & Shopping Planner")

        with gr.Row():
            scrape_btn = gr.Button("Run Scraper")
            scrape_status = gr.Textbox(label="Status", interactive=False)
        scrape_btn.click(scrape_data, outputs=[scrape_status])

        gr.Markdown("---")
        gr.Markdown("## Plan Shopping")

        shop_in = gr.Textbox(
            label="Shopping List",
            placeholder="e.g. sem-skimmed milk, houmous, fries"
        )
        budget_in = gr.Number(label="Budget (£)", value=20.0)
        plan_btn = gr.Button("Plan Shopping")

        out_tbl = gr.Dataframe(headers=["requested", "selected", "price"])
        out_msg = gr.Textbox(label="Message", lines=3)

        plan_btn.click(
            lambda s, b: plan_shopping(s, b, llm),
            inputs=[shop_in, budget_in],
            outputs=[out_tbl, out_msg]
        )

    return app


def main():
    # Build FAISS index if CSV exists
    if os.path.exists(CSV_PATH):
        df = load_catalog()
        rebuild_index(df)

    app = build_ui()
    app.launch()


if __name__ == "__main__":
    main()

