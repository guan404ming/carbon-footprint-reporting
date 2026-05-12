"""Detailed per-paper analysis: extract exact paragraphs containing keyword matches."""

import csv
import io
import json
import os
import re
import sys

from PyPDF2 import PdfReader

PDF_DIR = "matched_pdfs"
OUTPUT_JSON = "detailed_analysis.json"
OUTPUT_CSV = "detailed_analysis.csv"

COMPUTE_KEYWORDS = [
    r"GPU[\s\-]?hours?",
    r"A100",
    r"H100",
    r"V100",
    r"A6000",
    r"A40(?!\d)",
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


def extract_pages(pdf_path):
    """Extract text per page from a PDF."""
    try:
        reader = PdfReader(pdf_path)
        pages = []
        for i, page in enumerate(reader.pages):
            t = page.extract_text()
            if t:
                pages.append({"page": i + 1, "text": t})
        return pages
    except Exception as e:
        return []


def find_matches_in_text(text, patterns, category):
    """Find all keyword matches with surrounding context (the paragraph)."""
    matches = []
    for pat in patterns:
        for m in pat.finditer(text):
            start = m.start()
            end = m.end()
            # Extract surrounding context: ~300 chars before and after
            ctx_start = max(0, start - 300)
            ctx_end = min(len(text), end + 300)
            # Try to align to sentence boundaries
            context = text[ctx_start:ctx_end].strip()
            # Clean up whitespace
            context = re.sub(r'\s+', ' ', context)
            matches.append({
                "category": category,
                "keyword": pat.pattern,
                "matched_text": m.group(),
                "context": context,
            })
    return matches


def guess_section(text, match_pos, full_text):
    """Try to guess which section a match is in based on common headings."""
    section_patterns = [
        r"(?:^|\n)\s*(\d+\.?\s+[A-Z][^\n]{3,60})\s*\n",
        r"(?:^|\n)\s*(Abstract)\s*\n",
        r"(?:^|\n)\s*(Introduction)\s*\n",
        r"(?:^|\n)\s*(Related\s+Work)\s*\n",
        r"(?:^|\n)\s*(Method(?:s|ology)?)\s*\n",
        r"(?:^|\n)\s*(Experiment(?:s|al)?(?:\s+(?:Setup|Results|Details))?)\s*\n",
        r"(?:^|\n)\s*(Results?(?:\s+and\s+Discussion)?)\s*\n",
        r"(?:^|\n)\s*(Discussion)\s*\n",
        r"(?:^|\n)\s*(Conclusion(?:s)?)\s*\n",
        r"(?:^|\n)\s*(Appendix(?:\s+[A-Z])?)\s*\n",
        r"(?:^|\n)\s*(Broader\s+Impact)\s*\n",
        r"(?:^|\n)\s*(Limitations?)\s*\n",
        r"(?:^|\n)\s*(Ethics(?:\s+Statement)?)\s*\n",
        r"(?:^|\n)\s*(Reproducibility)\s*\n",
        r"(?:^|\n)\s*(Implementation\s+Details?)\s*\n",
        r"(?:^|\n)\s*(Training\s+Details?)\s*\n",
        r"(?:^|\n)\s*(Societal\s+Impact)\s*\n",
        r"(?:^|\n)\s*(Environmental\s+Impact)\s*\n",
    ]

    # Find all section headers before the match position
    best_section = "Unknown"
    best_pos = -1
    text_before = full_text[:match_pos]
    for sp in section_patterns:
        for sm in re.finditer(sp, text_before, re.IGNORECASE):
            if sm.start() > best_pos:
                best_pos = sm.start()
                best_section = sm.group(1).strip()

    return best_section


def analyze_pdf(pdf_path):
    """Analyze a single PDF for all keyword matches with full context."""
    pages = extract_pages(pdf_path)
    if not pages:
        return []

    # Build full text with page markers
    full_text = ""
    page_offsets = []
    for p in pages:
        page_offsets.append({"page": p["page"], "offset": len(full_text)})
        full_text += p["text"] + "\n\n"

    compute_pats = [re.compile(k, re.IGNORECASE) for k in COMPUTE_KEYWORDS]
    energy_pats = [re.compile(k, re.IGNORECASE) for k in ENERGY_KEYWORDS]
    carbon_pats = [re.compile(k, re.IGNORECASE) for k in CARBON_KEYWORDS]

    all_matches = []

    for category, pats in [("compute", compute_pats), ("energy", energy_pats), ("carbon", carbon_pats)]:
        for pat in pats:
            for m in pat.finditer(full_text):
                pos = m.start()
                # Determine page
                page_num = 1
                for po in page_offsets:
                    if po["offset"] <= pos:
                        page_num = po["page"]
                    else:
                        break

                # Get section
                section = guess_section(full_text, pos, full_text)

                # Get context: ~300 chars around match
                ctx_start = max(0, pos - 300)
                ctx_end = min(len(full_text), m.end() + 300)
                context = full_text[ctx_start:ctx_end].strip()
                context = re.sub(r'\s+', ' ', context)

                all_matches.append({
                    "category": category,
                    "keyword_pattern": pat.pattern,
                    "matched_text": m.group(),
                    "page": page_num,
                    "section": section,
                    "context": context,
                })

    # Deduplicate: if same keyword matched multiple times in same paragraph, keep unique contexts
    seen = set()
    deduped = []
    for match in all_matches:
        key = (match["category"], match["keyword_pattern"], match["page"], match["context"][:100])
        if key not in seen:
            seen.add(key)
            deduped.append(match)

    return deduped


def main():
    pdfs = sorted(os.listdir(PDF_DIR))
    pdfs = [f for f in pdfs if f.endswith(".pdf")]
    print(f"Analyzing {len(pdfs)} matched PDFs in detail...\n")

    all_results = []
    csv_rows = []

    for i, pdf_file in enumerate(pdfs):
        pdf_path = os.path.join(PDF_DIR, pdf_file)
        title = pdf_file.replace("_", " ").rsplit(".pdf", 1)[0].strip()

        print(f"[{i+1}/{len(pdfs)}] {title[:80]}...")

        matches = analyze_pdf(pdf_path)

        paper_result = {
            "title": title,
            "file": pdf_file,
            "num_matches": len(matches),
            "categories": {
                "compute": [m for m in matches if m["category"] == "compute"],
                "energy": [m for m in matches if m["category"] == "energy"],
                "carbon": [m for m in matches if m["category"] == "carbon"],
            },
        }
        all_results.append(paper_result)

        for m in matches:
            csv_rows.append({
                "title": title,
                "category": m["category"],
                "keyword_pattern": m["keyword_pattern"],
                "matched_text": m["matched_text"],
                "page": m["page"],
                "section": m["section"],
                "context": m["context"],
            })

    # Write JSON
    with open(OUTPUT_JSON, "w") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"\nJSON results saved to {OUTPUT_JSON}")

    # Write CSV
    fieldnames = ["title", "category", "keyword_pattern", "matched_text", "page", "section", "context"]
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)
    print(f"CSV results saved to {OUTPUT_CSV}")

    # Summary per category
    compute_papers = set()
    energy_papers = set()
    carbon_papers = set()
    for r in all_results:
        if r["categories"]["compute"]:
            compute_papers.add(r["title"])
        if r["categories"]["energy"]:
            energy_papers.add(r["title"])
        if r["categories"]["carbon"]:
            carbon_papers.add(r["title"])

    n = len(pdfs)
    print(f"\nDETAILED SUMMARY ({n} papers with matches)")
    print(f"Compute: {len(compute_papers)} papers")
    print(f"Energy:  {len(energy_papers)} papers")
    print(f"Carbon:  {len(carbon_papers)} papers")
    print(f"Total match rows in CSV: {len(csv_rows)}")


if __name__ == "__main__":
    main()
