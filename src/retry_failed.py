"""Retry the 5 failed papers and update CSV."""

import io
import re
import time
import requests
from PyPDF2 import PdfReader

FAILED_URLS = {
    "Video Prediction Policy: A Generalist Robot Policy with Predictive Visual Representations":
        "https://raw.githubusercontent.com/mlresearch/v267/main/assets/du25c/du25c.pdf",
    "ReinboT: Amplifying Robot Visual-Language Manipulation with Reinforcement Learning":
        "https://raw.githubusercontent.com/mlresearch/v267/main/assets/wang25br/wang25br.pdf",
    "RISE: Radius of Influence based Subgraph Extraction for 3D Molecular Graph Explanation":
        "https://raw.githubusercontent.com/mlresearch/v267/main/assets/qu25a/qu25a.pdf",
    "KIND: Knowledge Integration and Diversion for Training Decomposable Models":
        "https://raw.githubusercontent.com/mlresearch/v267/main/assets/jiang25k/jiang25k.pdf",
    "StealthInk: A Multi-bit and Stealthy Watermark for Large Language Models":
        "https://raw.githubusercontent.com/mlresearch/v267/main/assets/jiang25j/jiang25j.pdf",
}

COMPUTE_KEYWORDS = [
    r"GPU[\s\-]?hours?", r"A100", r"H100", r"V100", r"A6000", r"A40(?!\d)",
    r"L40", r"RTX\s?\d{4}", r"TPU[\s\-]?v\d", r"TPU\s+pod", r"training\s+time",
    r"wall[\s\-]?clock", r"compute\s+budget", r"compute\s+cost", r"FLOPs",
    r"PFLOPs", r"petaflop", r"GPU\s+memory", r"node[\s\-]?hours?",
    r"machine\s+hours?", r"accelerator", r"cloud\s+compute", r"pretraining\s+cost",
]
ENERGY_KEYWORDS = [
    r"kWh", r"kilowatt[\s\-]?hour", r"megawatt[\s\-]?hour", r"MWh",
    r"watt[\s\-]?hour", r"power\s+consumption", r"energy\s+consumption",
    r"energy\s+usage", r"energy\s+cost", r"energy\s+footprint",
    r"energy\s+efficiency", r"power\s+usage\s+effectiveness", r"PUE",
    r"CodeCarbon", r"Carbontracker", r"carbonalyser",
    r"experiment[\s\-]?impact[\s\-]?tracker", r"ML\s+CO2\s+Impact",
    r"eco2ai", r"zeus", r"energy\s+monitor", r"power\s+draw", r"TDP",
    r"thermal\s+design\s+power", r"joule",
]
CARBON_KEYWORDS = [
    r"CO2", r"CO₂", r"carbon\s+footprint", r"carbon\s+emission",
    r"carbon\s+impact", r"carbon\s+intensity", r"carbon\s+cost",
    r"greenhouse\s+gas", r"carbon\s+offset", r"gCO2eq", r"kgCO2", r"tCO2",
    r"carbon\s+neutral", r"net[\s\-]?zero", r"carbon\s+budget",
    r"carbon\s+accounting", r"life[\s\-]?cycle\s+assessment", r"LCA",
    r"scope\s+[123]\s+emission", r"carbon\s+disclosure",
    r"environmental\s+impact", r"sustainability\s+report",
    r"green\s+AI", r"sustainable\s+AI",
]

def search(text, keywords):
    for k in keywords:
        if re.search(k, text, re.IGNORECASE):
            return True
    return False

for title, url in FAILED_URLS.items():
    print(f"Retrying: {title[:70]}...")
    try:
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        reader = PdfReader(io.BytesIO(resp.content))
        text = ""
        for page in reader.pages:
            t = page.extract_text()
            if t:
                text += t
        c = search(text, COMPUTE_KEYWORDS)
        e = search(text, ENERGY_KEYWORDS)
        co = search(text, CARBON_KEYWORDS)
        print(f"  compute={c}, energy={e}, carbon={co}")
    except Exception as ex:
        print(f"  FAILED AGAIN: {ex}")
    time.sleep(2)
