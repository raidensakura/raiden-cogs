import requests
from bs4 import BeautifulSoup
import json
import time

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; benchmark-scraper/1.0)"}

URLS = {
    "singlethread": "https://www.cpubenchmark.net/single-thread/desktop",
    "multithread": "https://www.cpubenchmark.net/multithread/desktop",
    "gaming": "https://www.cpubenchmark.net/top-gaming-cpus.html",
}


def scrape_page(url, score_type):
    print(f"Scraping {score_type} from {url}")
    res = requests.get(url, headers=HEADERS, timeout=10)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")

    names = soup.select(".prdname")
    scores = soup.select(".count")

    if not names or not scores:
        raise ValueError("Failed to locate .prdname or .count elements")

    cpu_scores = {}
    for name_tag, score_tag in zip(names, scores):
        name = name_tag.get_text(strip=True)
        try:
            score = int(score_tag.get_text(strip=True).replace(",", ""))
        except ValueError:
            continue  # skip malformed scores
        cpu_scores[name] = score
    return cpu_scores


def main():
    results = {}

    for score_type, url in URLS.items():
        page_data = scrape_page(url, score_type)
        for cpu_name, score in page_data.items():
            if cpu_name not in results:
                results[cpu_name] = {}
            results[cpu_name][score_type] = score
        time.sleep(2)  # be polite

    with open("cpu.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("✅ Scraping complete. Data saved to 'cpu_benchmarks.json'.")


if __name__ == "__main__":
    main()
