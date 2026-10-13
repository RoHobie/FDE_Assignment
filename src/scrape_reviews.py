#!/usr/bin/env python3
"""
Optional:
    python src/scrape_reviews.py --target 1000 --output data/raw_reviews.csv
    python src/scrape_reviews.py --country in --lang en --max-pages 300

Notes:
- Uses the unofficial google-play-scraper package.
- Reviews are fetched newest-first, then filtered locally to ratings <= 2.
- The script stops when it reaches the target, runs out of pages, or reaches
  --max-pages. It reports the actual number collected.
"""

import argparse
import csv
import sys
import time
import random
from datetime import datetime, timezone
from pathlib import Path

from google_play_scraper import Sort, reviews


APP_ID = "com.moveinsync.ets"
CSV_COLUMNS = [
    "review_id",
    "rating",
    "review_text",
    "review_date",
    "developer_response",
    "developer_response_date",
    "app_version",
    "thumbs_up_count",
    "language",
    "country",
    "source_app_id",
    "collected_at_utc",
]


def to_iso(value):
    """Convert a datetime to ISO 8601 text; preserve blanks for missing values."""
    if not value:
        return ""
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    return str(value)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Collect recent MoveInSync Google Play reviews rated 1 or 2 stars."
    )
    parser.add_argument("--target", type=int, default=1000,
                        help="Number of unique low-rated reviews to collect (default: 1000).")
    parser.add_argument("--output", default="data/raw_reviews.csv",
                        help="Output CSV path (default: data/raw_reviews.csv).")
    parser.add_argument("--country", default="in",
                        help="Google Play country code (default: in).")
    parser.add_argument("--lang", default="en",
                        help="Review language code (default: en).")
    parser.add_argument("--max-pages", type=int, default=300,
                        help="Maximum pagination requests (default: 300).")
    parser.add_argument("--delay", type=float, default=2.0,
                        help="Base seconds to wait between requests (default: 2.0).")
    parser.add_argument("--jitter", type=float, default=1.0,
                        help="Add a random delay of 0 to this many seconds after each request (default: 1.0).")
    parser.add_argument("--backoff", type=float, default=15.0,
                        help="Seconds to wait after a request error before stopping (default: 15.0).")
    return parser.parse_args()


def main():
    args = parse_args()

    if args.target < 1:
        raise SystemExit("--target must be at least 1.")
    if args.max_pages < 1:
        raise SystemExit("--max-pages must be at least 1.")
    if args.delay < 0:
        raise SystemExit("--delay cannot be negative.")
    if args.jitter < 0:
        raise SystemExit("--jitter cannot be negative.")
    if args.backoff < 0:
        raise SystemExit("--backoff cannot be negative.")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    collected_at = datetime.now(timezone.utc).isoformat()
    seen_ids = set()
    low_rated = []
    continuation_token = None
    pages_fetched = 0
    raw_reviews_seen = 0

    print(f"App ID: {APP_ID}")
    print(f"Target: {args.target} unique reviews rated 1 or 2 stars")
    print(f"Store locale: country={args.country}, language={args.lang}")
    print("Fetching newest reviews; filtering ratings locally...\n")

    try:
        while len(low_rated) < args.target and pages_fetched < args.max_pages:
            try:
                batch, next_token = reviews(
                    APP_ID,
                    lang=args.lang,
                    country=args.country,
                    sort=Sort.NEWEST,
                    count=200,
                    continuation_token=continuation_token,
                )
            except Exception:
                # Back off on errors instead of retrying aggressively.
                if args.backoff:
                    print(f"Request failed; waiting {args.backoff:.1f}s before stopping.")
                    time.sleep(args.backoff)
                raise

            pages_fetched += 1
            raw_reviews_seen += len(batch)

            if not batch:
                print("No more reviews returned by Google Play.")
                break

            for item in batch:
                review_id = item.get("reviewId")
                if not review_id or review_id in seen_ids:
                    continue
                seen_ids.add(review_id)

                score = item.get("score")
                if score not in (1, 2):
                    continue

                low_rated.append({
                    "review_id": review_id,
                    "rating": score,
                    "review_text": item.get("content", "") or "",
                    "review_date": to_iso(item.get("at")),
                    "developer_response": item.get("replyContent", "") or "",
                    "developer_response_date": to_iso(item.get("repliedAt")),
                    "app_version": item.get("appVersion", "") or "",
                    "thumbs_up_count": item.get("thumbsUpCount", 0),
                    "language": args.lang,
                    "country": args.country,
                    "source_app_id": APP_ID,
                    "collected_at_utc": collected_at,
                })

                if len(low_rated) >= args.target:
                    break

            print(
                f"Page {pages_fetched}: fetched {len(batch)} reviews; "
                f"{len(low_rated)}/{args.target} eligible unique reviews collected."
            )

            if len(low_rated) >= args.target:
                break
            if not next_token or next_token == continuation_token:
                print("No further pagination token available.")
                break

            continuation_token = next_token
            wait_seconds = args.delay + random.uniform(0, args.jitter)
            if wait_seconds:
                print(f"Waiting {wait_seconds:.1f}s before the next request...")
                time.sleep(wait_seconds)

    except KeyboardInterrupt:
        print("\nInterrupted. Saving reviews collected so far...")
    except Exception as exc:
        print(f"\nCollection failed: {exc}", file=sys.stderr)
        if not low_rated:
            raise SystemExit(1) from exc
        print("Saving the reviews collected before the error.")

    # Write even if fewer than the target were available.
    with output_path.open("w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(low_rated)

    print("\nCollection complete.")
    print(f"Raw reviews examined: {raw_reviews_seen}")
    print(f"Unique 1- or 2-star reviews saved: {len(low_rated)}")
    print(f"Pages fetched: {pages_fetched}")
    print(f"CSV path: {output_path.resolve()}")

    if len(low_rated) < args.target:
        print(
            f"Note: target was {args.target}, but only {len(low_rated)} were collected. "
            "Try increasing --max-pages or review the country/language settings."
        )


if __name__ == "__main__":
    main()
