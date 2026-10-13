# MoveInSync Review Analysis

An end-to-end intelligence pipeline that fetches low-rated reviews (ratings: 1 - 2 stars) for the MoveInSync enterprise transport app from Google Play, audits and cleanses the data, discovers an issue taxonomy, classifies reviews chunk-by-chunk using Gemini 3.8 Flash, and generates an executive report with empirical statistics, priority-ranked issues, proof reviews, and actionable remediation strategies.

---

## Architecture & Workflow

1. **Scrape Reviews (`src/scrape_reviews.py`)**: Fetches 1,000 unique reviews rated 1 - 2 stars sorted newest-first from Google Play Store (`com.moveinsync.ets`), omitting user info for privacy, and saves to `data/raw_reviews.csv`.
2. **Audit & Cleanse (`src/audit_reviews.py`)**: Computes descriptive statistics across raw reviews and cleanses the dataset (deduplicating review IDs and duplicate content, stripping whitespace, and dropping empty reviews).
3. **Discover Taxonomy & Initial Classification (`src/discover_taxonomy.py`)**: Samples the first 200 reviews and uses Gemini (default: `gemini-3.8-flash`) to discover an issue taxonomy saved to `outputs/taxonomy.json` (including a pre-configured `NULL_REVIEWS` category), and classifies the first 200 reviews into `data/classified_reviews.csv`.
4. **Classify Remaining Reviews (`src/classify_reviews.py`)**: Resumes from the 201st review (index 200) to EOF, classifying batch-by-batch using Gemini into `data/classified_reviews.csv`. Uninformative reviews map to `NULL_REVIEWS` and unresolved genuine complaints map to `MANUAL_REVIEW`.
5. **Executive Summary & Report Generation (`src/generate_report.py`)**: Maps up to 50 highest-confidence reviews per category, computes empirical metrics, and prompts an LLM (OpenAI `gpt-4o` or Gemini `gemini-3.5-flash` / `gemini-3.1-flash-lite` fallback) to synthesize `outputs/executive_summary.md` with priority-wise rankings, deep-dive proof reviews, and an actionable product remediation plan.

---

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and configure GEMINI_API_KEY (and optionally OPENAI_API_KEY)
```

---

## Execution Guide

### Stage 1: Collect 1k Low-Rated Reviews
```bash
python src/scrape_reviews.py --target 1000 --output data/raw_reviews.csv
```

### Stage 2: Audit & Cleanse the Dataset
```bash
python src/audit_reviews.py data/raw_reviews.csv
```

### Stage 3: Discover Taxonomy & Classify First 200 Reviews
```bash
python src/discover_taxonomy.py --input data/raw_reviews.csv --sample-size 200
```
This produces:
- `outputs/taxonomy.json`
- `data/classified_reviews.csv` (first 200 reviews classified)

### Stage 4: Classify Remaining Reviews (201st to EOF)
```bash
python src/classify_reviews.py --input data/raw_reviews.csv --start-index 200
```
Appends remaining classified reviews to `data/classified_reviews.csv`. Note: `--model` defaults to `gemini-3.1-flash-lite` (or set `--model gemini-3.8-flash`).

### Stage 5: Generate Executive Report & Proof Reviews Map
```bash
python src/generate_report.py
```
> **Note on LLM Provider**: Defaults to OpenAI (`gpt-4o`) and automatically falls back to Gemini (`gemini-3.5-flash`) if `OPENAI_API_KEY` is not set or quota is exhausted. To force Gemini directly, run:
> ```bash
> python src/generate_report.py --provider gemini --model gemini-3.5-flash
> ```

This produces:
- `outputs/category_proof_reviews.json` (top 50 highest-confidence proof reviews per category)
- `outputs/executive_summary.md` (comprehensive executive summary and remediation roadmap)

