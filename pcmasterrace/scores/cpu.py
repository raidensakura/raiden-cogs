import json
import time

import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; benchmark-scraper/1.0)"}

URLS = {
    "singlethread": "https://www.cpubenchmark.net/single-thread",
    "multithread": "https://www.cpubenchmark.net/multithread",
    "gaming": "https://www.cpubenchmark.net/top-gaming-cpus.html",
}


def scrape_page(url, score_type):
    print(f"Scraping {score_type} from {url}")
    all_cpu_scores = {}

    pages = [1] if score_type == "gaming" else [1, 2]

    for page in pages:
        page_url = url if page == 1 else f"{url}/page{page}"
        print(f"  Scraping page {page_url}")
        res = requests.get(page_url, headers=HEADERS, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")

        names = soup.select(".prdname")
        scores = soup.select(".count")

        if not names or not scores:
            print(
                f"  Warning: Failed to locate .prdname or .count elements on {page_url}"
            )
            continue

        for name_tag, score_tag in zip(names, scores):
            name = name_tag.get_text(strip=True)
            try:
                score = int(score_tag.get_text(strip=True).replace(",", ""))
            except ValueError:
                continue  # skip malformed scores
            all_cpu_scores[name] = score

        time.sleep(1)  # be polite between pages

    return all_cpu_scores


def load_previous_data(filename):
    """Load previous JSON data to validate new scrape."""
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def validate_data(new_data, old_data, threshold=0.8):
    """Validate that new data is not empty and hasn't dropped drastically."""
    if not new_data:
        raise ValueError(
            "❌ Scraping produced empty data. Aborting to prevent data loss."
        )
    new_count = len(new_data)
    old_count = len(old_data)
    if old_count > 0 and new_count < old_count * threshold:
        raise ValueError(
            f"❌ Data count dropped from {old_count} to {new_count} "
            f"({100*new_count/old_count:.1f}% of previous). "
            f"This suggests a scraping failure. Aborting to prevent data loss."
        )
    return True


def main():
    results = {}

    for score_type, url in URLS.items():
        page_data = scrape_page(url, score_type)
        for cpu_name, score in page_data.items():
            if cpu_name not in results:
                results[cpu_name] = {}
            results[cpu_name][score_type] = score
        time.sleep(2)  # be polite

    # Validate before writing
    old_data = load_previous_data("cpu.json")
    validate_data(results, old_data)

    with open("cpu.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("✅ Scraping complete. Data saved to 'cpu.json'.")


if __name__ == "__main__":
    main()
