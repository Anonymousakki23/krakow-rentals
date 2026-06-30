import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import urllib.parse

st.set_page_config(page_title="Kraków Aggregator", page_icon="🏢", layout="wide")
st.title("🏙️ Kraków Multi-Site Rental Aggregator (OLX & Otodom)")

# Insert your ScraperAPI key here
API_KEY = "8fb5f8c3835d5e75147bc44c0e3da364b00c1dc9"

DISTRICTS = {
    "Stare Miasto": {"olx": "stare-miasto", "otodom": "stare-miasto"},
    "Grzegórzki": {"olx": "grzegorzki", "otodom": "grzegorzki"},
    "Prądnik Czerwony": {"olx": "pradnik-czerwony", "otodom": "pradnik-czerwony"},
    "Krowodrza": {"olx": "krowodrza", "otodom": "krowodrza"},
    "Ruczaj / Dębniki": {"olx": "debniki", "otodom": "debniki"},
    "Podgórze": {"olx": "podgorze", "otodom": "podgorze"}
}

selected_district = st.selectbox("Select Kraków Locality:", list(DISTRICTS.keys()))
max_budget = st.slider("Maximum Price Budget (PLN):", 1200, 6000, 3000, step=100)

def proxy_request(target_url):
    """Routes the request through a proxy to bypass blocks"""
    payload = {'api_key': API_KEY, 'url': target_url}
    proxy_url = 'https://api.scraperapi.com/?' + urllib.parse.urlencode(payload)
    try:
        r = requests.get(proxy_url, timeout=15)
        return r.text if r.status_code == 200 else None
    except:
        return None

def fetch_olx(slug):
    url = f"https://www.olx.pl/nieruchomosci/mieszkania/wynajem/krakow/q-{slug}/?search%5Bsort_by%5D=price%3Aasc"
    html = proxy_request(url)
    if not html: return []
    
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.find_all("div", {"data-cy": "l-card"})
    results = []
    for c in cards:
        try:
            title = c.find("h6").text.strip()
            price_str = c.find("p", {"data-testid": "ad-price"}).text.strip()
            price = int(''.join(filter(str.isdigit, price_str)))
            link = "https://www.olx.pl" + c.find("a")["href"]
            results.append({"Source": "OLX", "Title": title, "Price (PLN)": price, "Link": link})
        except: continue
    return results

def fetch_otodom(slug):
    url = f"https://www.otodom.pl/pl/wyniki/wynajem/mieszkanie/malopolskie/krakow/{slug}"
    html = proxy_request(url)
    if not html: return []
    
    soup = BeautifulSoup(html, "html.parser")
    # Otodom structural selector for 2026 rendering layouts
    listings = soup.find_all("article", {"data-testid": "listing-item"})
    results = []
    for item in listings:
        try:
            title = item.find("p", {"data-testid": "title"}).text.strip()
            price_str = item.find("span", {"data-testid": "price"}).text.strip()
            price = int(''.join(filter(str.isdigit, price_str)))
            link = "https://www.otodom.pl" + item.find("a")["href"]
            results.append({"Source": "Otodom", "Title": title, "Price (PLN)": price, "Link": link})
        except: continue
    return results

if st.button("🔥 Scan All Platforms Simultaneosly"):
    with st.spinner("Bypassing anti-bot checks and scanning aggregations..."):
        slugs = DISTRICTS[selected_district]
        
        # Scrape and bundle data arrays together
        all_listings = fetch_olx(slugs["olx"]) + fetch_otodom(slugs["otodom"])
        
        if all_listings:
            df = pd.DataFrame(all_listings)
            # Filter results based on selected budget
            filtered_df = df[df["Price (PLN)"] <= max_budget].sort_values("Price (PLN)")
            
            if not filtered_df.empty:
                st.success(f"Successfully processed {len(filtered_df)} real-time matches!")
                st.data_editor(
                    filtered_df,
                    column_config={"Link": st.column_config.LinkColumn("Open Listing Detail")},
                    hide_index=True,
                    use_container_width=True
                )
            else:
                st.error("No properties located on OLX or Otodom within your budget slider criteria.")
        else:
            st.warning("⚠️ High host traffic limits hit. Please retry or adjust target proxy parameters.")
