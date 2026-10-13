from scraper import (
    Listing,
    dedupe_listings,
    filter_by_budget,
    normalize_url,
    parse_olx,
    parse_otodom,
    parse_price,
)

OLX_HTML = """
<div data-cy="l-card">
  <a href="/d/oferta/mieszkanie-stare-miasto-ID1.html"><h6>Cozy flat, Stare Miasto</h6></a>
  <p data-testid="ad-price">3 200 zł</p>
</div>
<div data-cy="l-card">
  <a href="/d/oferta/broken.html"><h6>Broken card</h6></a>
</div>
"""

OTODOM_HTML = """
<article data-testid="listing-item">
  <a href="/pl/oferta/mieszkanie-grzegorzki-ID2"><p data-testid="title">Bright flat, Grzegórzki</p></a>
  <span data-testid="price">2 850 zł</span>
</article>
"""


def test_parse_price():
    assert parse_price("3 200 zł") == 3200
    assert parse_price("2850zl") == 2850
    assert parse_price("no price") is None
    assert parse_price("") is None


def test_parse_olx_skips_malformed_cards():
    listings = parse_olx(OLX_HTML)
    assert len(listings) == 1
    assert listings[0].source == "OLX"
    assert listings[0].price_pln == 3200
    assert listings[0].url.startswith("https://www.olx.pl/d/oferta/")


def test_parse_otodom():
    listings = parse_otodom(OTODOM_HTML)
    assert len(listings) == 1
    assert listings[0].source == "Otodom"
    assert listings[0].price_pln == 2850


def test_normalize_url_ignores_query_and_case():
    assert normalize_url("HTTPS://WWW.OLX.PL/x/?a=1#frag") == "https://www.olx.pl/x"


def test_dedupe_listings():
    a = Listing("OLX", "Flat", 3000, "https://www.olx.pl/x/?a=1")
    b = Listing("OLX", "Flat", 3000, "https://www.olx.pl/x/")
    c = Listing("Otodom", "Other", 3100, "https://www.otodom.pl/y")
    assert dedupe_listings([a, b, c]) == [a, c]


def test_filter_by_budget_sorts_ascending():
    items = [
        Listing("OLX", "Expensive", 5000, "https://www.olx.pl/a"),
        Listing("OLX", "Cheap", 2500, "https://www.olx.pl/b"),
    ]
    filtered = filter_by_budget(items, 3000)
    assert [item.title for item in filtered] == ["Cheap"]
