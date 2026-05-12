# How to Run the Carbon Reporting Survey

## Setup

```bash
uv pip install openreview-py requests PyPDF2
```

## Run

```bash
python survey_carbon_reporting.py
```

## What It Does

1. Fetches ICML 2025 accepted papers via OpenReview API
2. Randomly samples 30 papers
3. Downloads each PDF and searches for three categories of keywords:
   - **Compute metadata**: GPU type, GPU-hours, training time, wall-clock
   - **Energy data**: kWh, power consumption, CodeCarbon, Carbontracker
   - **Carbon data**: CO2, carbon footprint, carbon emissions, greenhouse gas
4. Outputs a CSV with per-paper results and a summary

## Expected Output

Something like:

```
SUMMARY (n=30 sampled ICML 2025 papers)
Compute metadata (GPU type/hours): 22/30 (73%)
Energy data (kWh):                  1/30 (3%)
Carbon data (CO2):                  0/30 (0%)
```

## How to Use in Rebuttal

Plug the numbers into this template:

> We sampled N accepted ICML 2025 papers: X% reported compute metadata (GPU type or training time), but only Y% reported energy consumption (kWh) and Z% reported carbon emissions. This confirms that the gap we identify is specifically between compute metadata (now common) and energy/carbon data (still rare).

## Notes

- Change `SAMPLE_SIZE` in the script to sample more papers (50 is also fine)
- Change seed for different random samples
- Carbon keyword matches may include false positives from papers *about* carbon (e.g., climate ML papers). Manually check the CSV for these.
- If you want NeurIPS 2025 instead, change the invitation to `NeurIPS.cc/2025/Conference/-/Submission` and venueid to `NeurIPS.cc/2025/Conference`