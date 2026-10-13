"""Streamlit UI for the Kraków rental aggregator.

Secrets: set SCRAPER_API_KEY in `.streamlit/secrets.toml` (local/Streamlit
Cloud) or as an environment variable. Never commit the real key.
"""

import logging
import os

import pandas as pd
import streamlit as st

from scraper import (
    DISTRICTS,
    dedupe_listings,
    fetch_html,
    filter_by_budget,
    olx_search_url,
    otodom_search_url,
    parse_olx,
    parse_otodom,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(page_title="Kraków Rental Aggregator", page_icon="🏢", layout="wide")
st.title("🏙️ Kraków Rental Aggregator")
st.caption(
    "Compare OLX and Otodom apartment-rental listings across Kraków districts. "
    "Results are fetched on demand through your configured proxy key."
)


def get_api_key() -> str | None:
    """Return the ScraperAPI key from Streamlit secrets or the environment."""
    try:
        secret_key = st.secrets.get("SCRAPER_API_KEY")
    except Exception:  # Streamlit secrets may be unavailable in some contexts
        secret_key = None
    return secret_key or os.environ.get("SCRAPER_API_KEY")


with st.sidebar:
    st.header("Search filters")
    selected_district = st.selectbox("Kraków district", list(DISTRICTS.keys()))
    max_budget = st.slider("Maximum price (PLN)", 1200, 6000, 3000, step=100)
    sort_order = st.radio("Sort by price", ["Lowest first", "Highest first"], horizontal=True)

api_key = get_api_key()
if not api_key:
    st.error(
        "Missing ScraperAPI key. Add `SCRAPER_API_KEY` to `.streamlit/secrets.toml` "
        "or set the `SCRAPER_API_KEY` environment variable. See README.md."
    )
    st.stop()

if st.button("🔥 Scan OLX and Otodom simultaneously"):
    slugs = DISTRICTS[selected_district]
    errors: list[str] = []

    with st.spinner("Requesting listings from OLX and Otodom..."):
        olx_html = fetch_html(olx_search_url(slugs["olx"]), api_key)
        otodom_html = fetch_html(otodom_search_url(slugs["otodom"]), api_key)

    listings = []
    if olx_html is None:
        errors.append("OLX")
    else:
        listings.extend(parse_olx(olx_html))
    if otodom_html is None:
        errors.append("Otodom")
    else:
        listings.extend(parse_otodom(otodom_html))

    listings = filter_by_budget(dedupe_listings(listings), max_budget)
    if sort_order == "Highest first":
        listings = list(reversed(listings))

    if errors:
        st.warning(
            "Some sources did not respond: "
            + ", ".join(errors)
            + ". Showing results from the sources that worked."
        )

    if not listings:
        st.info("No listings found within your budget. Try another district or raise the budget.")
    else:
        st.success(f"Found {len(listings)} matching listings in {selected_district}.")
        df = pd.DataFrame(
            [
                {
                    "Source": item.source,
                    "Title": item.title,
                    "Price (PLN)": item.price_pln,
                    "Link": item.url,
                }
                for item in listings
            ]
        )
        st.dataframe(
            df,
            column_config={"Link": st.column_config.LinkColumn("Open listing")},
            hide_index=True,
            use_container_width=True,
        )
        st.download_button(
            "Download results as CSV",
            df.to_csv(index=False).encode("utf-8"),
            file_name=f"krakow-rentals-{slugs['olx']}.csv",
            mime="text/csv",
        )
