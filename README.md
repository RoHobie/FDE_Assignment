# MoveInSync Review Analysis

An intelligence pipeline to collect, audit, categorize, and synthesize low-rated reviews (ratings ≤ 2★) for the MoveInSync enterprise transport app from Google Play into actionable product remediation roadmaps.

---

## Pipeline Architecture

1. **Scrape (`src/scrape_reviews.py`)**: Ingests recent 1–2★ reviews from Google Play Store (`com.moveinsync.ets`) into `data/raw_reviews.csv` (omits PII).
2. **Audit & Cleanse (`src/audit_reviews.py`)**: Deduplicates IDs/text, removes empty reviews, validates distributions, and audits prompt injection risks.
3. **Discover Taxonomy (`src/discover_taxonomy.py`)**: Analyzes sample reviews via Gemini to derive an issue taxonomy in `outputs/taxonomy.json` and classifies initial batch.
4. **Classify Batch (`src/classify_reviews.py`)**: Classifies remaining reviews against the taxonomy into `data/classified_reviews.csv` with confidence scoring and injection neutralization.
5. **Report Generation (`src/generate_report.py`)**: Extracts top proof reviews to `outputs/category_proof_reviews.json` and synthesizes an executive analysis in `outputs/executive_summary.md`.

---

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Set GEMINI_API_KEY (and optionally OPENAI_API_KEY) in .env
```

---

## Execution Guide

### 1. Ingest Reviews
```bash
python src/scrape_reviews.py --target 1000 --output data/raw_reviews.csv
```

### 2. Audit & Cleanse Dataset
```bash
python src/audit_reviews.py data/raw_reviews.csv
```

### 3. Discover Taxonomy & Classify First Batch
```bash
python src/discover_taxonomy.py --input data/raw_reviews.csv --sample-size 200
```
Generates `outputs/taxonomy.json` and initial `data/classified_reviews.csv`.

### 4. Classify Remaining Reviews
```bash
python src/classify_reviews.py --input data/raw_reviews.csv --start-index 200
```
Appends remaining classified reviews to `data/classified_reviews.csv`.

### 5. Generate Executive Summary & Proof Map
```bash
python src/generate_report.py
```
*Falls back from OpenAI (`gpt-4o`) to Gemini (`gemini-3.5-flash`) if `OPENAI_API_KEY` is unavailable.* Direct Gemini usage:
```bash
python src/generate_report.py --provider gemini --model gemini-3.5-flash
```
Outputs:
- `outputs/category_proof_reviews.json`
- `outputs/executive_summary.md`

