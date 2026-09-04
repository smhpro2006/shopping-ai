# Canonical product seed data.
# Products are deduplicated — one row per physical product.
# Retailer listings are in OFFERS, referencing RETAILERS by name.
# The collector (python -m collector) fills live offers from eBay;
# seed offers below are kept for tests and cold-start demo only.

RETAILERS = [
    {"name": "Amazon",   "url": "https://amazon.com"},
    {"name": "Walmart",  "url": "https://walmart.com"},
    {"name": "Best Buy", "url": "https://bestbuy.com"},
]

# 20 canonical products: Headphones×7, Earbuds×7, Speakers×6
PRODUCTS = [
    # ── Headphones (7) ──────────────────────────────────────────────────────
    {
        "brand": "Sony",
        "model": "WH-1000XM5",
        "name": "Sony WH-1000XM5 Wireless Noise Cancelling Headphones",
        "category": "Headphones",
        "image_url": None,
    },
    {
        "brand": "Bose",
        "model": "QuietComfort 45",
        "name": "Bose QuietComfort 45 Wireless Noise Cancelling Headphones",
        "category": "Headphones",
        "image_url": None,
    },
    {
        "brand": "Apple",
        "model": "AirPods Max",
        "name": "Apple AirPods Max Wireless Over-Ear Headphones",
        "category": "Headphones",
        "image_url": None,
    },
    {
        "brand": "Sony",
        "model": "WH-1000XM4",
        "name": "Sony WH-1000XM4 Wireless Noise Cancelling Headphones",
        "category": "Headphones",
        "image_url": None,
    },
    {
        "brand": "Jabra",
        "model": "Evolve2 85",
        "name": "Jabra Evolve2 85 Wireless Headset",
        "category": "Headphones",
        "image_url": None,
    },
    {
        "brand": "Bose",
        "model": "QuietComfort Ultra",
        "name": "Bose QuietComfort Ultra Headphones",
        "category": "Headphones",
        "image_url": None,
    },
    {
        "brand": "Sennheiser",
        "model": "Momentum 4",
        "name": "Sennheiser Momentum 4 Wireless Headphones",
        "category": "Headphones",
        "image_url": None,
    },

    # ── Earbuds (7) ─────────────────────────────────────────────────────────
    {
        "brand": "Apple",
        "model": "AirPods Pro 2",
        "name": "Apple AirPods Pro 2nd Generation",
        "category": "Earbuds",
        "image_url": None,
    },
    {
        "brand": "Samsung",
        "model": "Galaxy Buds3 Pro",
        "name": "Samsung Galaxy Buds3 Pro Wireless Earbuds",
        "category": "Earbuds",
        "image_url": None,
    },
    {
        "brand": "Sony",
        "model": "WF-1000XM5",
        "name": "Sony WF-1000XM5 Wireless Noise Cancelling Earbuds",
        "category": "Earbuds",
        "image_url": None,
    },
    {
        "brand": "Bose",
        "model": "QuietComfort Earbuds 2",
        "name": "Bose QuietComfort Earbuds 2 True Wireless Earbuds",
        "category": "Earbuds",
        "image_url": None,
    },
    {
        "brand": "Jabra",
        "model": "Elite 10",
        "name": "Jabra Elite 10 True Wireless Earbuds",
        "category": "Earbuds",
        "image_url": None,
    },
    {
        "brand": "Google",
        "model": "Pixel Buds Pro",
        "name": "Google Pixel Buds Pro Wireless Earbuds",
        "category": "Earbuds",
        "image_url": None,
    },
    {
        "brand": "Samsung",
        "model": "Galaxy Buds2 Pro",
        "name": "Samsung Galaxy Buds2 Pro True Wireless Earbuds",
        "category": "Earbuds",
        "image_url": None,
    },

    # ── Speakers (6) ────────────────────────────────────────────────────────
    {
        "brand": "Sonos",
        "model": "Era 300",
        "name": "Sonos Era 300 Wireless Speaker",
        "category": "Speakers",
        "image_url": None,
    },
    {
        "brand": "Bose",
        "model": "SoundLink Max",
        "name": "Bose SoundLink Max Portable Bluetooth Speaker",
        "category": "Speakers",
        "image_url": None,
    },
    {
        "brand": "JBL",
        "model": "Charge 5",
        "name": "JBL Charge 5 Portable Waterproof Bluetooth Speaker",
        "category": "Speakers",
        "image_url": None,
    },
    {
        "brand": "Sonos",
        "model": "Era 100",
        "name": "Sonos Era 100 Wireless Speaker",
        "category": "Speakers",
        "image_url": None,
    },
    {
        "brand": "Ultimate Ears",
        "model": "Hyperboom",
        "name": "Ultimate Ears Hyperboom Portable Bluetooth Speaker",
        "category": "Speakers",
        "image_url": None,
    },
    {
        "brand": "JBL",
        "model": "Flip 6",
        "name": "JBL Flip 6 Portable Waterproof Bluetooth Speaker",
        "category": "Speakers",
        "image_url": None,
    },
]

# Seed offers for the original 3 products (index 0, 7, 8).
# The collector fills live offers for all products.
# Each offer: (product index into PRODUCTS, retailer name, price)
OFFERS = [
    (0,  "Amazon",   349.99),   # Sony WH-1000XM5
    (0,  "Walmart",  329.99),   # Sony WH-1000XM5
    (7,  "Best Buy", 249.00),   # Apple AirPods Pro 2
    (8,  "Amazon",   199.99),   # Samsung Galaxy Buds3 Pro
]
