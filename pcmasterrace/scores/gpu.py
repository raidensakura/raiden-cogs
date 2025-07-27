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

    gpu_tags = soup.select(".rank-check")
    score_tags = soup.select(".mx-2.text-slate-900.text-sm.font-bold")

    if not gpu_tags or not score_tags or len(gpu_tags) != len(score_tags):
        raise ValueError(f"Mismatch in GPU and score count at {url}")

    data = {}
    for gpu_tag, score_tag in zip(gpu_tags, score_tags):
        gpu_name = gpu_tag.get("value", "").strip()
        score_text = score_tag.get_text(strip=True).replace(",", "")
        if not gpu_name or not score_text.isdigit():
            continue
        data[gpu_name] = int(score_text)

    return data


def main():
    gpu_data = {}

    for score_type, url in URLS.items():
        scores = scrape_gpu_scores(url, score_type)
        for gpu, score in scores.items():
            if gpu not in gpu_data:
                gpu_data[gpu] = {}
            gpu_data[gpu][score_type] = score
        time.sleep(2)

    with open("gpu.json", "w", encoding="utf-8") as f:
        json.dump(gpu_data, f, indent=2)

    print("✅ Scraping complete. Data saved to 'gpu_benchmarks.json'.")


if __name__ == "__main__":
    main()
