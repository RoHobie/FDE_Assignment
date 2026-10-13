#!/usr/bin/env python3
"""
Audit and cleanse scraped reviews.

Provides comprehensive descriptive analytics of raw reviews and cleanses
the dataset by removing duplicate IDs, empty or whitespace-only texts,
and identical duplicate submissions.
"""

import argparse
import shutil
import sys
from pathlib import Path
import pandas as pd


def parse_args():
    parser = argparse.ArgumentParser(
        description="Audit and cleanse MoveInSync review dataset."
    )
    parser.add_argument(
        "input_pos",
        nargs="?",
        default=None,
        help="Input CSV path (positional fallback, default: data/raw_reviews.csv)",
    )
    parser.add_argument(
        "--input",
        "-i",
        default="data/raw_reviews.csv",
        help="Input CSV path (default: data/raw_reviews.csv)",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="data/raw_reviews.csv",
        help="Output CSV path for cleansed data (default: data/raw_reviews.csv)",
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        default=True,
        help="Backup original raw reviews if overwriting input (default: True)",
    )
    parser.add_argument(
        "--no-backup",
        action="store_false",
        dest="backup",
        help="Do not backup original raw reviews before overwriting",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    input_path = Path(args.input_pos if args.input_pos else args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        sys.exit(f"Input file not found: {input_path}")

    print("=" * 60)
    print("           MOVEINSYNC REVIEW AUDIT & CLEANSE            ")
    print("=" * 60)
    print(f"Reading: {input_path.resolve()}\n")

    df_raw = pd.read_csv(input_path)
    total_raw = len(df_raw)

    print("--- 1. RAW DATASET OVERVIEW ---")
    print(f"Total raw records: {total_raw}")
    print(f"Columns present: {list(df_raw.columns)}")

    # Rating distribution
    print("\n--- 2. RATING DISTRIBUTION ---")
    if "rating" in df_raw.columns:
        print(df_raw["rating"].value_counts(dropna=False).sort_index().to_string())
    else:
        print("Warning: 'rating' column missing.")

    # Dates
    print("\n--- 3. DATE RANGE ---")
    if "review_date" in df_raw.columns:
        valid_dates = pd.to_datetime(df_raw["review_date"], errors="coerce")
        print(f"Earliest review date: {valid_dates.min()}")
        print(f"Latest review date:   {valid_dates.max()}")
    else:
        print("Warning: 'review_date' column missing.")

    # Missing & Null Analysis
    print("\n--- 4. MISSING VALUES PER COLUMN ---")
    print(df_raw.isna().sum().to_string())

    # Text length analytics
    text_col = df_raw["review_text"].fillna("").astype(str)
    empty_mask = text_col.str.strip().eq("")
    empty_count = empty_mask.sum()
    print(f"\nEmpty or whitespace-only reviews: {empty_count} ({empty_count / total_raw * 100:.1f}%)" if total_raw > 0 else 0)

    char_lengths = text_col.str.len()
    word_counts = text_col.str.split().str.len()
    if total_raw > 0:
        print(f"Character length: min={char_lengths.min()}, median={char_lengths.median():.0f}, "
              f"mean={char_lengths.mean():.1f}, max={char_lengths.max()}")
        print(f"Word count:       min={word_counts.min()}, median={word_counts.median():.0f}, "
              f"mean={word_counts.mean():.1f}, max={word_counts.max()}")

    # Duplicates Analysis
    dup_ids = df_raw["review_id"].duplicated().sum() if "review_id" in df_raw.columns else 0
    dup_texts = df_raw[~empty_mask]["review_text"].duplicated().sum() if total_raw > 0 else 0
    print(f"\nDuplicate review IDs: {dup_ids}")
    print(f"Duplicate review text contents: {dup_texts}")

    # App versions & developer reply
    if "app_version" in df_raw.columns and total_raw > 0:
        top_versions = df_raw["app_version"].value_counts(dropna=False).head(5)
        print("\n--- 5. TOP APP VERSIONS ---")
        print(top_versions.to_string())

    if "developer_response" in df_raw.columns and total_raw > 0:
        has_reply = df_raw["developer_response"].fillna("").str.strip().ne("").sum()
        print(f"\nDeveloper response count: {has_reply} ({has_reply / total_raw * 100:.1f}%)")

    # --- CLEANSING PHASE ---
    print("\n" + "=" * 60)
    print("                 CLEANSING DATASET                      ")
    print("=" * 60)

    # 1. Deduplicate by review_id
    step1 = df_raw.drop_duplicates(subset=["review_id"]).copy()
    dropped_dup_ids = total_raw - len(step1)

    # 2. Clean and filter review_text
    step1["review_text"] = step1["review_text"].fillna("").astype(str).str.strip()
    step2 = step1[step1["review_text"].ne("")].copy()
    dropped_empty = len(step1) - len(step2)

    # 3. Deduplicate exact duplicate review text submissions
    step3 = step2.drop_duplicates(subset=["review_text", "rating"]).copy()
    dropped_dup_content = len(step2) - len(step3)

    # 4. Filter ratings <= 2
    if "rating" in step3.columns:
        step4 = step3[step3["rating"].isin([1, 2])].copy()
    else:
        step4 = step3.copy()
    dropped_invalid_rating = len(step3) - len(step4)

    df_clean = step4.reset_index(drop=True)
    total_clean = len(df_clean)

    print(f"Dropped duplicate IDs:               {dropped_dup_ids}")
    print(f"Dropped empty/whitespace texts:      {dropped_empty}")
    print(f"Dropped duplicate review contents:   {dropped_dup_content}")
    print(f"Dropped non 1- or 2-star ratings:    {dropped_invalid_rating}")
    print(f"Total dropped:                       {total_raw - total_clean}")
    print(f"Final cleansed reviews count:        {total_clean}")

    # Backup if overwriting
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if args.backup and input_path.resolve() == output_path.resolve():
        backup_path = input_path.with_name(f"{input_path.stem}_raw{input_path.suffix}")
        if not backup_path.exists():
            shutil.copy2(input_path, backup_path)
            print(f"\nBacked up original raw data to: {backup_path.resolve()}")

    df_clean.to_csv(output_path, index=False)
    print(f"Saved cleansed dataset to: {output_path.resolve()}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
