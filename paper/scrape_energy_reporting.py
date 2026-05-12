#!/usr/bin/env python3
"""
Scrape ML conference papers to measure energy/carbon reporting rates.
"""

import requests
from bs4 import BeautifulSoup
import re
import time
import json
from collections import defaultdict
import random

# Keywords indicating energy/carbon reporting (in abstract/title)
ENERGY_KEYWORDS = [
    r'\bkwh\b', r'kilowatt', r'watt[\s-]?hour',
    r'\bco2\b', r'co₂', r'carbon[\s-]?emission', r'carbon[\s-]?footprint',
    r'energy[\s-]?consumption', r'power[\s-]?consumption',
    r'electricity[\s-]?usage', r'electricity[\s-]?consumption',
    r'codecarbon', r'carbontracker', r'experiment[\s-]?impact[\s-]?tracker',
    r'gco2', r'gram[s]?[\s]?of[\s]?co2', r'ton[s]?[\s]?of[\s]?co2', r'kg[\s-]?co2',
    r'carbon[\s-]?intensity', r'grid[\s-]?intensity',
    r'environmental[\s-]?impact',
    r'power[\s-]?usage[\s-]?effectiveness', r'\bpue\b',
    r'green[\s-]?ai', r'sustainable[\s-]?ai', r'sustainable[\s-]?ml',
    r'gpu[\s-]?energy', r'training[\s-]?energy', r'inference[\s-]?energy',
    r'compute[\s-]?carbon', r'ml[\s-]?carbon', r'ai[\s-]?carbon',
    r'energy[\s-]?efficient', r'carbon[\s-]?neutral', r'carbon[\s-]?aware',
]

def check_energy_keywords(text):
    """Check if text contains energy/carbon reporting keywords."""
    if not text:
        return False, []
    text_lower = text.lower()
    found = []
    for pattern in ENERGY_KEYWORDS:
        if re.search(pattern, text_lower):
            found.append(pattern)
    return len(found) > 0, found

def analyze_icml_pmlr(year, sample_size=200):
    """Analyze ICML papers from PMLR by fetching individual paper pages."""
    print(f"\nAnalyzing ICML {year}...")

    volume_map = {
        2024: 235, 2023: 202, 2022: 162, 2021: 139, 2020: 119,
    }

    if year not in volume_map:
        return None

    url = f"https://proceedings.mlr.press/v{volume_map[year]}/"

    try:
        response = requests.get(url, timeout=60)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Each paper is in a div with class 'paper'
        papers = []
        for paper_div in soup.find_all('div', class_='paper'):
            title_p = paper_div.find('p', class_='title')
            if not title_p:
                continue

            title = title_p.get_text().strip()

            # Get abstract link
            links_p = paper_div.find('p', class_='links')
            paper_url = None
            if links_p:
                for a in links_p.find_all('a'):
                    href = a.get('href', '')
                    if '.html' in href:
                        if href.startswith('/'):
                            paper_url = f"https://proceedings.mlr.press{href}"
                        elif href.startswith('http'):
                            paper_url = href
                        else:
                            paper_url = f"https://proceedings.mlr.press/v{volume_map[year]}/{href}"
                        break

            if paper_url:
                papers.append({'title': title, 'url': paper_url})

        print(f"  Found {len(papers)} papers with links")

        if len(papers) == 0:
            return None

        # Sample
        sample = papers if len(papers) <= sample_size else random.sample(papers, sample_size)

        energy_count = 0
        energy_papers = []

        for i, paper in enumerate(sample):
            print(f"  Checking {i+1}/{len(sample)}...", end='\r')
            try:
                resp = requests.get(paper['url'], timeout=15)
                soup2 = BeautifulSoup(resp.text, 'html.parser')

                # Get abstract
                abstract = ""
                abs_div = soup2.find('div', id='abstract')
                if not abs_div:
                    abs_div = soup2.find('div', class_='abstract')
                if abs_div:
                    abstract = abs_div.get_text()

                text = f"{paper['title']} {abstract}"
                has_energy, keywords = check_energy_keywords(text)

                if has_energy:
                    energy_count += 1
                    energy_papers.append({'title': paper['title'][:60], 'keywords': keywords})

            except Exception as e:
                pass

            time.sleep(0.25)

        rate = (energy_count / len(sample)) * 100
        print(f"  ICML {year}: {energy_count}/{len(sample)} = {rate:.1f}%           ")
        for ep in energy_papers[:3]:
            print(f"    - {ep['title']}...")

        return {
            'venue': f'ICML {year}',
            'total': len(papers),
            'sampled': len(sample),
            'energy_papers': energy_count,
            'rate': rate,
            'examples': [ep['title'] for ep in energy_papers]
        }

    except Exception as e:
        print(f"  Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def analyze_openreview_venue(venue_name, year, sample_size=200):
    """Analyze papers from OpenReview using search."""
    print(f"\nAnalyzing {venue_name} {year}...")

    try:
        import openreview
        client = openreview.api.OpenReviewClient(baseurl='https://api2.openreview.net')

        venue_id = f'{venue_name}.cc/{year}/Conference'

        # Use get_all_notes without limit
        notes = list(client.get_all_notes(content={'venueid': venue_id}))

        print(f"  Found {len(notes)} papers")

        if len(notes) == 0:
            return None

        sample = notes if len(notes) <= sample_size else random.sample(notes, sample_size)

        energy_count = 0
        energy_papers = []

        for note in sample:
            content = note.content if hasattr(note, 'content') else {}

            title = ""
            abstract = ""

            if isinstance(content, dict):
                # Handle both old and new API formats
                title_field = content.get('title', '')
                if isinstance(title_field, dict):
                    title = title_field.get('value', '')
                else:
                    title = str(title_field)

                abstract_field = content.get('abstract', '')
                if isinstance(abstract_field, dict):
                    abstract = abstract_field.get('value', '')
                else:
                    abstract = str(abstract_field)

            text = f"{title} {abstract}"
            has_energy, keywords = check_energy_keywords(text)

            if has_energy:
                energy_count += 1
                energy_papers.append({'title': title[:60], 'keywords': keywords})

        rate = (energy_count / len(sample)) * 100
        short_name = venue_name.split('.')[0]
        print(f"  {short_name} {year}: {energy_count}/{len(sample)} = {rate:.1f}%")
        for ep in energy_papers[:3]:
            print(f"    - {ep['title']}...")

        return {
            'venue': f'{short_name} {year}',
            'total': len(notes),
            'sampled': len(sample),
            'energy_papers': energy_count,
            'rate': rate,
            'examples': [ep['title'] for ep in energy_papers]
        }

    except Exception as e:
        print(f"  Error: {e}")
        return None

def analyze_neurips_html(year, sample_size=200):
    """Analyze NeurIPS papers by scraping the proceedings website."""
    print(f"\nAnalyzing NeurIPS {year}...")

    base_url = f"https://papers.neurips.cc/paper_files/paper/{year}"

    try:
        response = requests.get(base_url, timeout=60)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find all paper links
        papers = []
        for li in soup.find_all('li'):
            a = li.find('a')
            if a and a.get('href', '').startswith('/paper_files/paper/'):
                href = a['href']
                title = a.get_text().strip()
                paper_url = f"https://papers.neurips.cc{href}"
                papers.append({'title': title, 'url': paper_url})

        print(f"  Found {len(papers)} papers")

        if len(papers) == 0:
            return None

        sample = papers if len(papers) <= sample_size else random.sample(papers, sample_size)

        energy_count = 0
        energy_papers = []

        for i, paper in enumerate(sample):
            print(f"  Checking {i+1}/{len(sample)}...", end='\r')
            try:
                resp = requests.get(paper['url'], timeout=15)
                soup2 = BeautifulSoup(resp.text, 'html.parser')

                # Get abstract
                abstract = ""
                abs_h4 = soup2.find('h4', string='Abstract')
                if abs_h4:
                    abs_p = abs_h4.find_next('p')
                    if abs_p:
                        abstract = abs_p.get_text()

                text = f"{paper['title']} {abstract}"
                has_energy, keywords = check_energy_keywords(text)

                if has_energy:
                    energy_count += 1
                    energy_papers.append({'title': paper['title'][:60], 'keywords': keywords})

            except:
                pass

            time.sleep(0.25)

        rate = (energy_count / len(sample)) * 100
        print(f"  NeurIPS {year}: {energy_count}/{len(sample)} = {rate:.1f}%           ")
        for ep in energy_papers[:3]:
            print(f"    - {ep['title']}...")

        return {
            'venue': f'NeurIPS {year}',
            'total': len(papers),
            'sampled': len(sample),
            'energy_papers': energy_count,
            'rate': rate,
            'examples': [ep['title'] for ep in energy_papers]
        }

    except Exception as e:
        print(f"  Error: {e}")
        return None

def analyze_iclr_html(year, sample_size=200):
    """Analyze ICLR papers by scraping OpenReview directly."""
    print(f"\nAnalyzing ICLR {year}...")

    # ICLR uses OpenReview
    url = f"https://iclr.cc/virtual/{year}/papers.html"

    try:
        response = requests.get(url, timeout=60)

        if response.status_code != 200:
            # Try alternative: OpenReview search
            url2 = f"https://openreview.net/group?id=ICLR.cc/{year}/Conference"
            response = requests.get(url2, timeout=60)

        soup = BeautifulSoup(response.text, 'html.parser')

        papers = []
        # Find paper titles/links
        for a in soup.find_all('a', href=True):
            href = a['href']
            if 'forum?id=' in href:
                title = a.get_text().strip()
                if len(title) > 10:  # Filter out short links
                    if href.startswith('/'):
                        paper_url = f"https://openreview.net{href}"
                    else:
                        paper_url = href
                    papers.append({'title': title, 'url': paper_url})

        # Deduplicate
        seen = set()
        unique_papers = []
        for p in papers:
            if p['title'] not in seen:
                seen.add(p['title'])
                unique_papers.append(p)
        papers = unique_papers

        print(f"  Found {len(papers)} papers")

        if len(papers) == 0:
            return None

        sample = papers if len(papers) <= sample_size else random.sample(papers, sample_size)

        energy_count = 0
        energy_papers = []

        for i, paper in enumerate(sample):
            print(f"  Checking {i+1}/{len(sample)}...", end='\r')
            try:
                resp = requests.get(paper['url'], timeout=15)
                soup2 = BeautifulSoup(resp.text, 'html.parser')

                # Get abstract from OpenReview page
                abstract = ""
                for div in soup2.find_all('div'):
                    text = div.get_text()
                    if 'Abstract:' in text or len(text) > 300:
                        abstract = text
                        break

                text = f"{paper['title']} {abstract}"
                has_energy, keywords = check_energy_keywords(text)

                if has_energy:
                    energy_count += 1
                    energy_papers.append({'title': paper['title'][:60], 'keywords': keywords})

            except:
                pass

            time.sleep(0.3)

        rate = (energy_count / len(sample)) * 100
        print(f"  ICLR {year}: {energy_count}/{len(sample)} = {rate:.1f}%           ")
        for ep in energy_papers[:3]:
            print(f"    - {ep['title']}...")

        return {
            'venue': f'ICLR {year}',
            'total': len(papers),
            'sampled': len(sample),
            'energy_papers': energy_count,
            'rate': rate,
            'examples': [ep['title'] for ep in energy_papers]
        }

    except Exception as e:
        print(f"  Error: {e}")
        return None

def main():
    results = []
    random.seed(42)  # For reproducibility

    # Analyze ICML from PMLR (most reliable source)
    for year in [2020, 2021, 2022, 2023, 2024]:
        result = analyze_icml_pmlr(year, sample_size=150)
        if result:
            results.append(result)
        time.sleep(2)

    # Analyze NeurIPS
    for year in [2020, 2021, 2022, 2023, 2024]:
        result = analyze_neurips_html(year, sample_size=150)
        if result:
            results.append(result)
        time.sleep(2)

    # Summary
    print("\n" + "="*60)
    print("SUMMARY: Energy/Carbon Reporting Rates")
    print("="*60)

    by_year = defaultdict(list)
    for r in results:
        year = int(r['venue'].split()[-1])
        by_year[year].append(r)

    yearly_rates = {}
    for year in sorted(by_year.keys()):
        print(f"\n{year}:")
        total_sampled = 0
        total_energy = 0
        for r in by_year[year]:
            print(f"  {r['venue']}: {r['energy_papers']}/{r['sampled']} = {r['rate']:.1f}%")
            total_sampled += r['sampled']
            total_energy += r['energy_papers']

        if total_sampled > 0:
            avg_rate = (total_energy / total_sampled) * 100
            yearly_rates[year] = {
                'rate': avg_rate,
                'energy_papers': total_energy,
                'sampled': total_sampled
            }
            print(f"  Combined: {total_energy}/{total_sampled} = {avg_rate:.1f}%")

    # Save results
    output = {
        'detailed_results': results,
        'yearly_combined': yearly_rates,
        'methodology': 'Sampled accepted papers from ICML (PMLR) and NeurIPS proceedings. Searched title and abstract for energy/carbon keywords including: kWh, CO2, carbon footprint, energy consumption, CodeCarbon, etc.'
    }

    with open('energy_reporting_data.json', 'w') as f:
        json.dump(output, f, indent=2)

    print("\n" + "="*60)
    print("Data for figure (copy to generate_figures.py):")
    print("="*60)
    print("venues = [", end="")
    for i, year in enumerate(sorted(yearly_rates.keys())):
        if i > 0:
            print(", ", end="")
        print(f"'{year}'", end="")
    print("]")

    print("reporting_rates = [", end="")
    for i, year in enumerate(sorted(yearly_rates.keys())):
        if i > 0:
            print(", ", end="")
        print(f"{yearly_rates[year]['rate']:.1f}", end="")
    print("]")

    print(f"\nTotal papers sampled: {sum(r['rate'] for r in yearly_rates.values())}")
    print("\nResults saved to energy_reporting_data.json")

if __name__ == "__main__":
    main()
