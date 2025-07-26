# Startup Scoring Tool

A lightweight Streamlit app for evaluating and ranking startups based on public data like industry, employee size, and email confidence — designed for use in early-stage venture workflows.

## Features

- Analyze a single domain and generate a structured startup score
- Upload a CSV file to batch-score multiple domains
- View interactive bar charts with color-coded score tiers
- Download the full scoring report as CSV or PDF

## Why This Tool?

VC firms are increasingly data-driven. This app mimics a simplified version of internal VC tooling — useful for:

- Discovering hidden gems in deal sourcing
- Prioritizing inbound startups
- Conducting quick due diligence

## Tech Stack

- **Streamlit** (frontend)
- **Altair** (charting)
- **Pandas** (data processing)
- **Hunter.io API** (for real-time domain lookups)
- **ReportLab** (PDF export)

## Run Locally

1. Clone this repo
2. Install dependencies:

```bash
pip install -r requirements.txt

