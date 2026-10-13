# krakow-rentals

A small Streamlit app that aggregates apartment-rental listings in Kraków from
OLX and Otodom. Pick a district, set a maximum budget, and scan both platforms
at once. Results are deduplicated, filtered by price, and shown with direct
links to the original listings.

## Features

- District picker for popular Kraków areas (Stare Miasto, Grzegórzki, Prądnik Czerwony, Krowodrza, Ruczaj/Dębniki, Podgórze)
- Maximum-price slider in PLN
- Simultaneous OLX + Otodom scan with per-source error reporting
- Deduplication by canonical listing URL
- Price filtering and ascending/descending sort
- CSV download of the filtered results

## Requirements

- Python 3.10+
- A ScraperAPI key (used as the request proxy)

Pinned dependencies are listed in `requirements.txt`.

## Setup

```bash
git clone https://github.com/Anonymousakki23/krakow-rentals.git
cd krakow-rentals
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration

The app needs a `SCRAPER_API_KEY`. Provide it in **one** of these ways:

1. Streamlit secrets (recommended for Streamlit Community Cloud):
   - Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`
   - Put your key in `SCRAPER_API_KEY`
2. Environment variable:
   - Copy `.env.example` to `.env` and set `SCRAPER_API_KEY`
   - Or export it: `export SCRAPER_API_KEY="your-key-here"`

Never commit `.env` or `.streamlit/secrets.toml`; both are ignored by `.gitignore`.

## Run locally

```bash
streamlit run app.py
```

## Tests

```bash
pytest
```

The test suite covers price parsing, OLX/Otodom HTML parsing, URL
normalization, deduplication, and budget filtering. It does not make network
requests.

## Project structure

- `app.py` — Streamlit UI, filters, and result table
- `scraper.py` — proxy requests, HTML parsing, deduplication, and filtering
- `tests/test_scraper.py` — unit tests for the parsing logic
- `.env.example` — environment-variable template
- `.streamlit/secrets.toml.example` — Streamlit secrets template

## Deployment notes

On Streamlit Community Cloud, add this under **App settings → Secrets**:

```toml
SCRAPER_API_KEY = "your-key-here"
```

Then deploy from the `main` branch with `app.py` as the entry point.

## Limitations

- OLX and Otodom change their HTML layouts periodically; if parsing breaks,
  update the selectors in `scraper.py` (`parse_olx` / `parse_otodom`).
- The app depends on a third-party proxy API key and its quota/rate limits.
- Listings data belongs to OLX/Otodom; this project is not affiliated with either site.

## Security note

A proxy API key was previously committed to this repository's history. Removing
it from the current source does not remove it from Git history, so the exposed
key should be rotated/revoked in the provider dashboard.
