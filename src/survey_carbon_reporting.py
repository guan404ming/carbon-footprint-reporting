"""Survey carbon/energy reporting in ICML 2025 accepted papers.

Fetches paper list from proceedings.mlr.press, samples N papers,
downloads PDFs, and searches for compute/energy/carbon keywords.
Saves matched PDFs to a local directory.
"""

import csv
import io
import os
import random
import re
import sys
import time

import requests
from bs4 import BeautifulSoup
from PyPDF2 import PdfReader

SAMPLE_SIZE = 1000
SEED = 42
OUTPUT_CSV = "carbon_survey_results.csv"
PDF_DIR = "matched_pdfs"
PROCEEDINGS_URL = "https://proceedings.mlr.press/v267/"

COMPUTE_KEYWORDS = [
    r"GPU[\s\-]?hours?",
    r"A100",
    r"H100",
    r"V100",
    r"A6000",
    r"A40",
    r"L40",
    r"RTX\s?\d{4}",
    r"TPU[\s\-]?v\d",
    r"TPU\s+pod",
    r"training\s+time",
    r"wall[\s\-]?clock",
    r"compute\s+budget",
    r"compute\s+cost",
    r"FLOPs",
    r"PFLOPs",
    r"petaflop",
    r"GPU\s+memory",
    r"node[\s\-]?hours?",
    r"machine\s+hours?",
    r"accelerator",
    r"cloud\s+compute",
    r"pretraining\s+cost",
]

ENERGY_KEYWORDS = [
    r"kWh",
    r"kilowatt[\s\-]?hour",
    r"megawatt[\s\-]?hour",
    r"MWh",
    r"watt[\s\-]?hour",
    r"power\s+consumption",
    r"energy\s+consumption",
    r"energy\s+usage",
    r"energy\s+cost",
    r"energy\s+footprint",
    r"energy\s+efficiency",
    r"power\s+usage\s+effectiveness",
    r"PUE",
    r"CodeCarbon",
    r"Carbontracker",
    r"carbonalyser",
    r"experiment[\s\-]?impact[\s\-]?tracker",
    r"ML\s+CO2\s+Impact",
    r"eco2ai",
    r"zeus",
    r"energy\s+monitor",
    r"power\s+draw",
    r"TDP",
    r"thermal\s+design\s+power",
    r"joule",
]

CARBON_KEYWORDS = [
    r"CO2",
    r"CO₂",
    r"carbon\s+footprint",
    r"carbon\s+emission",
    r"carbon\s+impact",
    r"carbon\s+intensity",
    r"carbon\s+cost",
    r"greenhouse\s+gas",
    r"carbon\s+offset",
    r"gCO2eq",
    r"kgCO2",
    r"tCO2",
    r"carbon\s+neutral",
    r"net[\s\-]?zero",
    r"carbon\s+budget",
    r"carbon\s+accounting",
    r"life[\s\-]?cycle\s+assessment",
    r"LCA",
    r"scope\s+[123]\s+emission",
    r"carbon\s+disclosure",
    r"environmental\s+impact",
    r"sustainability\s+report",
    r"green\s+AI",
    r"sustainable\s+AI",
]


def compile_patterns(keywords):
    return [re.compile(k, re.IGNORECASE) for k in keywords]


def search_text(text, patterns):
    matched = []
    for p in patterns:
        if p.search(text):
            matched.append(p.pattern)
    return matched


def extract_text_from_pdf(pdf_bytes):
    reader = PdfReader(io.BytesIO(pdf_bytes))
    text = ""
    for page in reader.pages:
        t = page.extract_text()
        if t:
            text += t + "\n"
    return text


def fetch_paper_list():
    """Scrape paper titles and PDF links from proceedings.mlr.press."""
    print(f"Fetching paper list from {PROCEEDINGS_URL}...")
    resp = requests.get(PROCEEDINGS_URL, timeout=60)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    papers = []
    for item in soup.select("div.paper"):
        title_tag = item.select_one("p.title")
        if not title_tag:
            continue
        title = title_tag.get_text(strip=True)

        pdf_link = None
        for a in item.select("p.links a"):
            if a.get_text(strip=True).lower() == "download pdf":
                href = a.get("href", "")
                if href:
                    if not href.startswith("http"):
                        href = "https://proceedings.mlr.press" + href
                    pdf_link = href
                    break

        if pdf_link:
            papers.append({"title": title, "pdf_url": pdf_link})

    return papers


def save_pdf(pdf_bytes, filename):
    """Save PDF to the matched_pdfs directory."""
    os.makedirs(PDF_DIR, exist_ok=True)
    safe_name = re.sub(r'[^\w\-.]', '_', filename)[:150] + ".pdf"
    path = os.path.join(PDF_DIR, safe_name)
    with open(path, "wb") as f:
        f.write(pdf_bytes)
    return path


def main():
    papers = fetch_paper_list()
    print(f"Found {len(papers)} papers with PDF links.")

    if len(papers) == 0:
        print("No papers found.")
        sys.exit(1)

    random.seed(SEED)
    sampled = random.sample(papers, min(SAMPLE_SIZE, len(papers)))
    print(f"Sampled {len(sampled)} papers.\n")

    compute_pats = compile_patterns(COMPUTE_KEYWORDS)
    energy_pats = compile_patterns(ENERGY_KEYWORDS)
    carbon_pats = compile_patterns(CARBON_KEYWORDS)

    results = []
    errors = 0
    for i, paper in enumerate(sampled):
        title = paper["title"]
        pdf_url = paper["pdf_url"]
        print(f"[{i+1}/{len(sampled)}] {title[:80]}...")

        has_compute = []
        has_energy = []
        has_carbon = []

        try:
            resp = requests.get(pdf_url, timeout=30)
            resp.raise_for_status()
            pdf_bytes = resp.content
            text = extract_text_from_pdf(pdf_bytes)
            has_compute = search_text(text, compute_pats)
            has_energy = search_text(text, energy_pats)
            has_carbon = search_text(text, carbon_pats)

            # Save PDF if any keyword matched
            if has_compute or has_energy or has_carbon:
                save_pdf(pdf_bytes, title)

        except Exception as e:
            print(f"  Warning: {e}")
            errors += 1

        results.append({
            "title": title,
            "pdf_url": pdf_url,
            "has_compute": bool(has_compute),
            "has_energy": bool(has_energy),
            "has_carbon": bool(has_carbon),
            "compute_matches": "; ".join(has_compute),
            "energy_matches": "; ".join(has_energy),
            "carbon_matches": "; ".join(has_carbon),
        })

        # Brief pause to avoid hammering the server
        if (i + 1) % 50 == 0:
            time.sleep(1)

    # Write CSV
    fieldnames = ["title", "pdf_url", "has_compute", "has_energy", "has_carbon",
                  "compute_matches", "energy_matches", "carbon_matches"]
    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    print(f"\nResults saved to {OUTPUT_CSV}")

    # Summary
    n = len(results)
    valid = n - errors
    c_count = sum(1 for r in results if r["has_compute"])
    e_count = sum(1 for r in results if r["has_energy"])
    co2_count = sum(1 for r in results if r["has_carbon"])

    print(f"\nSUMMARY (n={n} sampled, {valid} successfully processed)")
    print(f"Compute metadata (GPU type/hours/FLOPs): {c_count}/{valid} ({100*c_count//valid}%)")
    print(f"Energy data (kWh/power/trackers):         {e_count}/{valid} ({100*e_count//valid}%)")
    print(f"Carbon data (CO2/footprint/LCA):          {co2_count}/{valid} ({100*co2_count//valid}%)")
    print(f"\nMatched PDFs saved to: {PDF_DIR}/")
    if errors:
        print(f"Errors: {errors} papers could not be processed")


if __name__ == "__main__":
    main()
