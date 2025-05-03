# ALDI UK Price Scraper & Shopping Planner

A single‐page application to:

1. **Scrape** ALDI UK grocery data into a CSV (`aldi_uk_groceries.csv`).
2. **Plan** a budget‐aware shopping basket using Retrieval‐Augmented Generation (RAG) with a local LLM.

---

## Prerequisites

- **Python 3.8+** (tested on 3.10, 3.11, 3.13)
- **Google Chrome** browser and matching **ChromeDriver** in your PATH
- A **GGUF**-formatted LLM under **1 GB**, e.g. a quantized Mistral-1.1 B model (see below)

---

## Installation

1. **Clone** this repository:
   ```bash
   git clone https://github.com/yourusername/aldi-shop-planner.git
   cd aldi-shop-planner
   ```

2. **Create** and **activate** a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate    # macOS/Linux
   .\.venv\Scripts\activate   # Windows PowerShell
   ```

3. **Install** Python dependencies:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Download** a compact GGUF model (<1 GB). Recommended:

   | Model                                     | Size   | Format       | URL                                                                                  |
   |-------------------------------------------|--------|--------------|--------------------------------------------------------------------------------------|
   | tensorblock/mistral-1.1b-testing-GGUF     | 0.62 GB| Q4_K_M (4-bit)| https://huggingface.co/tensorblock/mistral-1.1b-testing-GGUF                          |
   | afrideva/malaysian-mistral-1.1B-4096-GGUF| 0.68 GB| Q4_K_M (4-bit)| https://huggingface.co/afrideva/malaysian-mistral-1.1B-4096-GGUF                     |

5. **Set** the model path environment variable (replace with your path):
   ```bash
   export LLAMA_MODEL_PATH="/home/user/models/mistral-1.1b-testing-Q4_K_M.gguf"  # Linux/macOS
   setx LLAMA_MODEL_PATH "C:\Models\mistral-1.1b-testing-Q4_K_M.gguf"        # Windows
   ```

---

## Usage

Run the main application:
```bash
python main.py
```

This will open a web UI at `http://127.0.0.1:7860`:

1. **Run Scraper**: Click the button to execute `scrape_aldi.py`. A status message shows scrape success and product count.
2. **Plan Shopping**:
   - Enter your shopping list as comma‑separated items (e.g. `sem-skimmed milk, irish sausages, houmous`).
   - Specify your budget (e.g. `20.00`).
   - Click **Plan Shopping**. The planner uses RAG + LLM to match items, then displays your basket and a summary.

---

## File Structure

```text
aldi-shop-planner/
├── main.py               # App combining scraper button + planner UI
├── scrape_aldi.py        # Headless Chrome scraper for ALDI UK groceries
├── requirements.txt      # Python dependencies
└── README.md             # This documentation
```

---

## Troubleshooting

- **ChromeDriver errors**: Make sure your ChromeDriver version matches your installed Chrome.
- **Model load failures**: Verify `LLAMA_MODEL_PATH` points to a valid `.gguf` file.
- **Missing packages**: Re-run `pip install -r requirements.txt`.

---

## License

MIT © Colin Kidwell
