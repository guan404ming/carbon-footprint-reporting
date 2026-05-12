"""Generate a clean per-paper report with false-positive filtering."""

import json
import re
import csv
from collections import Counter

INPUT_JSON = "detailed_analysis.json"
OUTPUT_REPORT = "detailed_report.md"
OUTPUT_CLEAN_CSV = "detailed_analysis_clean.csv"

# Words that commonly contain "LCA" as substring (false positives)
LCA_FALSE_POSITIVES = re.compile(
    r"(?:loca|local|clca|vocal|focal|calcu|escal|classi|clinical|tropical|"
    r"topological|logical|radical|medical|lexical|numerical|typical|optical|"
    r"practical|empirical|theoretical|canonical|vertical|identical|"
    r"statistical|dynamical|lyrical|critical|electrical|symmetrical|"
    r"grammatical|hierarchical|biological|physical|historical|etical|"
    r"analytica|mechanical|genetical|periodical|categorical|classical|"
    r"musical|technical|logica|clerical|radical|nautical|biblical|"
    r"skeptical|fantastical|whimsical|magical|comical|ironical|botanical|"
    r"pharmaceutical|theatrical|alphabetical|methodological|chronological|"
    r"meteorological|anthropological|pedagogical|oracle|place|replace|"
    r"calcar|calcul|scalab|percola|blocal)",
    re.IGNORECASE
)

# Check if "Joule" is used as energy-reporting (not physics unit in formulas)
JOULE_ENERGY_CONTEXT = re.compile(
    r"(?:energy|power|consumption|carbon|emission|footprint|train|inference|"
    r"compute|gpu|hardware|electricity|watt|kwh)",
    re.IGNORECASE
)

# Check if TDP is "Thermal Design Power" in energy-reporting context
TDP_ENERGY_CONTEXT = re.compile(
    r"(?:watt|power|energy|thermal\s+design|gpu|consumption|hardware|electricity)",
    re.IGNORECASE
)

# PUE should be about "Power Usage Effectiveness"
PUE_CONTEXT = re.compile(
    r"(?:power\s+usage|data\s+center|energy|electricity|cooling|infrastructure)",
    re.IGNORECASE
)

# MWh context
MWH_FALSE_POSITIVES = re.compile(
    r"(?:framework|network|method|algorithm|module|function|class|layer|batch|"
    r"samwh|newh|showh|growth)",
    re.IGNORECASE
)


def is_genuine_lca(match_text, context):
    """Check if LCA match is actually Life Cycle Assessment."""
    # If the matched text is exactly "LCA" (all caps), more likely genuine
    if match_text == "LCA":
        # Check context for LCA-related terms
        lca_context = re.compile(
            r"(?:life[\s\-]?cycle|assessment|environmental|emission|carbon|"
            r"footprint|impact|sustainab|manufacturing|embodied)",
            re.IGNORECASE
        )
        if lca_context.search(context):
            return True
        # Check if it's part of a longer word
        if LCA_FALSE_POSITIVES.search(context[max(0, context.find("LCA")-5):context.find("LCA")+8]):
            return False
        return True  # Standalone "LCA" is likely genuine

    # Mixed case like "lca", "Lca", "lCa" - almost certainly substring
    lower = match_text.lower()
    if lower == "lca" and match_text != "LCA":
        # Check if it appears as a standalone word
        # Look for word boundary around match in context
        pattern = re.compile(r'\bLCA\b')
        if pattern.search(context):
            return True
        return False

    return False


def is_genuine_tdp(match_text, context):
    """Check if TDP is about thermal design power / energy."""
    return bool(TDP_ENERGY_CONTEXT.search(context))


def is_genuine_joule(match_text, context):
    """Check if Joule reference is about energy reporting."""
    return bool(JOULE_ENERGY_CONTEXT.search(context))


def is_genuine_pue(match_text, context):
    """Check if PUE is about Power Usage Effectiveness."""
    if match_text == "PUE":
        return True
    return bool(PUE_CONTEXT.search(context))


def is_genuine_mwh(match_text, context):
    """Check if MWh match is a real energy unit."""
    if match_text in ("MWh", "mWh", "Mwh"):
        # Check it's actually about megawatt-hours
        energy_ctx = re.compile(r"(?:energy|power|electric|megawatt|consumption|carbon|emission)", re.IGNORECASE)
        return bool(energy_ctx.search(context))
    return False


def filter_match(match):
    """Return True if the match is genuine, False if likely a false positive."""
    keyword = match["keyword_pattern"]
    matched = match["matched_text"]
    context = match["context"]

    # LCA filtering
    if keyword == "LCA":
        return is_genuine_lca(matched, context)

    # TDP filtering
    if keyword == "TDP":
        return is_genuine_tdp(matched, context)

    # Joule filtering
    if keyword.lower() == "joule":
        return is_genuine_joule(matched, context)

    # PUE filtering
    if keyword == "PUE":
        return is_genuine_pue(matched, context)

    # MWh filtering
    if "MWh" in keyword or "megawatt" in keyword:
        return is_genuine_mwh(matched, context)

    # "zeus" - check it's the energy toolkit, not Zeus the mythological figure or model name
    if keyword == "zeus":
        zeus_ctx = re.compile(r"(?:energy|power|gpu|optimization|carbon|monitor|profil)", re.IGNORECASE)
        return bool(zeus_ctx.search(context))

    # "accelerator" - very common in ML context (hardware accelerator), keep only if about specific hardware
    if keyword == "accelerator":
        accel_ctx = re.compile(r"(?:GPU|TPU|NVIDIA|AMD|hardware|chip|device|compute\s+accelerator)", re.IGNORECASE)
        return bool(accel_ctx.search(context))

    return True


def truncate_context(context, max_len=200):
    """Shorten context for display while keeping the match visible."""
    if len(context) <= max_len:
        return context
    return context[:max_len] + "..."


def main():
    with open(INPUT_JSON) as f:
        data = json.load(f)

    print(f"Loaded {len(data)} papers. Filtering false positives...\n")

    # Filter and build clean results
    clean_papers = []
    csv_rows = []
    total_removed = Counter()
    total_kept = Counter()

    for paper in data:
        clean_cats = {"compute": [], "energy": [], "carbon": []}
        for cat in ["compute", "energy", "carbon"]:
            for m in paper["categories"][cat]:
                if filter_match(m):
                    clean_cats[cat].append(m)
                    total_kept[m["keyword_pattern"]] += 1
                else:
                    total_removed[m["keyword_pattern"]] += 1

        # Only include paper if it still has matches
        if any(clean_cats[c] for c in clean_cats):
            clean_papers.append({
                "title": paper["title"],
                "file": paper["file"],
                "categories": clean_cats,
            })
            for cat in ["compute", "energy", "carbon"]:
                for m in clean_cats[cat]:
                    csv_rows.append({
                        "title": paper["title"],
                        "category": cat,
                        "keyword_pattern": m["keyword_pattern"],
                        "matched_text": m["matched_text"],
                        "page": m["page"],
                        "section": m["section"],
                        "context": m["context"],
                    })

    print(f"After filtering: {len(clean_papers)} papers remain")
    print("\nRemoved false positives:")
    for kw, cnt in total_removed.most_common():
        print(f"  {kw}: {cnt} removed")

    # Write clean CSV
    fieldnames = ["title", "category", "keyword_pattern", "matched_text", "page", "section", "context"]
    with open(OUTPUT_CLEAN_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)
    print(f"\nClean CSV saved to {OUTPUT_CLEAN_CSV}")

    # Generate markdown report
    with open(OUTPUT_REPORT, "w", encoding="utf-8") as f:
        f.write("# ICML 2025 Carbon/Energy Reporting Survey - Detailed Report\n\n")
        f.write(f"Total papers with matches: {len(clean_papers)} (from 1000 sampled)\n\n")

        # Overall stats
        compute_papers = [p for p in clean_papers if p["categories"]["compute"]]
        energy_papers = [p for p in clean_papers if p["categories"]["energy"]]
        carbon_papers = [p for p in clean_papers if p["categories"]["carbon"]]

        f.write("## Summary\n\n")
        f.write("| Category | Papers | % of 995 valid |\n")
        f.write("|----------|--------|----------------|\n")
        f.write(f"| Compute metadata | {len(compute_papers)} | {100*len(compute_papers)//995}% |\n")
        f.write(f"| Energy data | {len(energy_papers)} | {100*len(energy_papers)//995}% |\n")
        f.write(f"| Carbon data | {len(carbon_papers)} | {100*len(carbon_papers)//995}% |\n\n")

        f.write("---\n\n")
        f.write("## Per-Paper Details\n\n")

        for i, paper in enumerate(clean_papers):
            f.write(f"### Paper {i+1}: {paper['title']}\n\n")

            for cat in ["compute", "energy", "carbon"]:
                matches = paper["categories"][cat]
                if not matches:
                    continue

                cat_label = {"compute": "Compute", "energy": "Energy", "carbon": "Carbon"}[cat]
                f.write(f"**{cat_label} mentions:**\n\n")

                # Group by page/section
                seen_contexts = set()
                for m in matches:
                    ctx_key = m["context"][:100]
                    if ctx_key in seen_contexts:
                        continue
                    seen_contexts.add(ctx_key)

                    section = m["section"] if m["section"] != "Unknown" else "N/A"
                    ctx_short = truncate_context(m["context"], 300)
                    f.write(f"- **Keyword**: `{m['matched_text']}` | **Page**: {m['page']} | **Section**: {section}\n")
                    f.write(f"  > {ctx_short}\n\n")

            f.write("---\n\n")

    print(f"Report saved to {OUTPUT_REPORT}")

    # Final clean stats
    print("\nFINAL CLEAN SUMMARY (n=995 valid papers)")
    print(f"Compute metadata: {len(compute_papers)}/995 ({100*len(compute_papers)//995}%)")
    print(f"Energy data:      {len(energy_papers)}/995 ({100*len(energy_papers)//995}%)")
    print(f"Carbon data:      {len(carbon_papers)}/995 ({100*len(carbon_papers)//995}%)")


if __name__ == "__main__":
    main()
