import json
import time

import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; GPU-Benchmark-Scraper/1.0)"}

URLS = {
    "speedway": "https://www.topcpu.net/en/gpu-r/3dmark-speed-way",
    "timespy_extreme": "https://www.topcpu.net/en/gpu-r/3dmark-time-spy-extreme",
}


def scrape_gpu_scores(url, score_type):
    print(f"Scraping {score_type} from {url}")
    res = requests.get(url, headers=HEADERS, timeout=10)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")

    # GPU names are in input[type="checkbox"] value attributes
    gpu_tags = soup.select('input[type="checkbox"]')
    score_tags = soup.select(".mx-2.text-slate-900.text-sm.font-bold")

    print(f"  Found {len(gpu_tags)} GPU elements and {len(score_tags)} score elements")

    data = {}
    for gpu_tag, score_tag in zip(gpu_tags, score_tags):
        gpu_name = gpu_tag.get("value", "").strip()
        score_text = score_tag.get_text(strip=True).replace(",", "")
        if not gpu_name or not score_text.isdigit():
            continue
        data[gpu_name] = int(score_text)

    return data


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
    gpu_data = {}

    for score_type, url in URLS.items():
        scores = scrape_gpu_scores(url, score_type)
        for gpu, score in scores.items():
            if gpu not in gpu_data:
                gpu_data[gpu] = {}
            gpu_data[gpu][score_type] = score
        time.sleep(2)

    # Validate before writing
    old_data = load_previous_data("gpu.json")
    validate_data(gpu_data, old_data)

    with open("gpu.json", "w", encoding="utf-8") as f:
        json.dump(gpu_data, f, indent=4)

    print("✅ Scraping complete. Data saved to 'gpu.json'.")


if __name__ == "__main__":
    main()
