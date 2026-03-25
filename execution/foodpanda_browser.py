"""
Foodpanda Pakistan API Client (Layer 3 - Execution)
Uses Foodpanda's public API for search, menus, and cart building.
Opens your real browser only for final checkout.
"""

import asyncio
import json
import os
import random
import re
import webbrowser
from pathlib import Path
from urllib.parse import quote, urlencode

import httpx

from dotenv import load_dotenv
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
TMP_DIR = BASE_DIR / ".tmp"
TMP_DIR.mkdir(exist_ok=True)

FOODPANDA_URL = "https://www.foodpanda.pk"

# API endpoints
DISCO_API = "https://disco.deliveryhero.io/listing/api/v1/pandora/vendors"
VENDOR_API = "https://pk.fd-api.com/api/v5/vendors"
NOMINATIM_SEARCH = "https://nominatim.openstreetmap.org/search"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
}

DISCO_HEADERS = {
    **HEADERS,
    "x-disco-client-id": "web",
}

VENDOR_HEADERS = {
    **HEADERS,
    "perseus-client-id": "web",
    "x-country-code": "pk",
}

# Cuisine keyword → Foodpanda cuisine names for filtering
CUISINE_MAP = {
    "desi": ["Pakistani", "Karahi & Handi", "Nihari", "Biryani", "Chapli Kabab"],
    "pakistani": ["Pakistani", "Karahi & Handi", "Nihari", "Biryani"],
    "biryani": ["Biryani", "Pakistani"],
    "chinese": ["Chinese", "Asian"],
    "pizza": ["Pizza", "Italian"],
    "italian": ["Pizza", "Italian", "Pasta"],
    "burger": ["Burgers", "Fast Food"],
    "burgers": ["Burgers", "Fast Food"],
    "fast food": ["Fast Food", "Burgers", "Pizza"],
    "bbq": ["BBQ", "Grill", "Tikka"],
    "grill": ["BBQ", "Grill"],
    "thai": ["Thai", "Asian"],
    "continental": ["Continental", "Western"],
    "dessert": ["Desserts", "Ice Cream", "Sweets"],
    "desserts": ["Desserts", "Ice Cream", "Sweets"],
    "healthy": ["Healthy", "Salads"],
    "sandwiches": ["Sandwiches", "Wraps"],
    "wraps": ["Wraps", "Sandwiches"],
    "soup": ["Soup"],
}


class FoodpandaBrowser:
    """Foodpanda API client + browser checkout.
    Uses the public API for search/menus (instant, no CAPTCHA).
    Opens your real browser for final checkout."""

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=15)
        self.latitude = None
        self.longitude = None
        self.location_name = None
        self.current_cuisine = None
        self.current_vendor_code = None
        self.session_id = None
        self.location_set = False

    async def start(self, headless: bool = False):
        """Initialize - generate session ID."""
        import uuid
        self.session_id = str(uuid.uuid4())
        print("[api] Foodpanda API client ready (no browser needed for search/menus)")

    async def close(self):
        await self.client.aclose()

    # ── Location ───────────────────────────────────────────────────────

    async def set_location(self, area: str) -> bool:
        """Geocode a location name to lat/lng."""
        try:
            print(f"[api] Geocoding: {area}")
            resp = await self.client.get(
                NOMINATIM_SEARCH,
                params={"q": f"{area} Pakistan", "format": "json", "limit": 1,
                        "accept-language": "en", "countrycodes": "pk"},
                headers={"User-Agent": "DOE-FoodpandaAgent/1.0"},
            )
            data = resp.json()
            if data:
                self.latitude = float(data[0]["lat"])
                self.longitude = float(data[0]["lon"])
                self.location_name = area
                self.location_set = True
                print(f"[api] Location: {area} → ({self.latitude}, {self.longitude})")
                return True
            print(f"[api] Could not geocode: {area}")
            return False
        except Exception as e:
            print(f"[api] Geocoding error: {e}")
            return False

    # ── Restaurant Search ──────────────────────────────────────────────

    async def search_cuisine(self, cuisine: str) -> bool:
        self.current_cuisine = cuisine
        return True

    async def browse_cuisine_category(self, cuisine: str) -> bool:
        return True

    async def scrape_restaurants(self, max_results: int = 20) -> list[dict]:
        """Fetch restaurants from Foodpanda API."""
        if not self.latitude or not self.longitude:
            print("[api] No location set")
            return []
        try:
            print(f"[api] Searching restaurants near ({self.latitude}, {self.longitude})")
            resp = await self.client.get(
                DISCO_API,
                params={
                    "latitude": self.latitude, "longitude": self.longitude,
                    "language_id": 1, "include": "characteristics",
                    "country": "pk", "vertical": "restaurants",
                    "limit": 50, "offset": 0, "customer_type": "regular",
                },
                headers=DISCO_HEADERS,
            )
            items = resp.json().get("data", {}).get("items", [])
            print(f"[api] Got {len(items)} total restaurants")

            # Filter by cuisine
            if self.current_cuisine:
                items = self._filter_by_cuisine(items, self.current_cuisine)
                print(f"[api] {len(items)} match cuisine '{self.current_cuisine}'")

            restaurants = []
            for item in items[:max_results]:
                r = self._parse_vendor(item)
                if r:
                    restaurants.append(r)
            return restaurants
        except Exception as e:
            print(f"[api] Error: {e}")
            return []

    def _filter_by_cuisine(self, items, cuisine):
        targets = [t.lower() for t in CUISINE_MAP.get(cuisine.lower(), [cuisine])]
        filtered = []
        for item in items:
            vendor_cuisines = [c.get("name", "").lower() for c in item.get("cuisines", [])]
            name = item.get("name", "").lower()
            if (any(t in vc for t in targets for vc in vendor_cuisines) or
                any(t in name for t in targets) or cuisine.lower() in name):
                filtered.append(item)
        return filtered

    def _parse_vendor(self, item):
        name = item.get("name")
        if not name:
            return None
        rating = item.get("rating")
        if isinstance(rating, dict):
            rating_val = rating.get("average")
            review_count = rating.get("vote_count", 0)
        else:
            rating_val = rating
            review_count = item.get("review_number", 0)
        delivery_time = item.get("minimum_delivery_time")
        delivery_fee = item.get("minimum_delivery_fee")
        min_order = item.get("minimum_order_amount")
        cuisines = [c.get("name", "") for c in item.get("cuisines", []) if c.get("name")]
        discounts = item.get("discounts", []) or []
        deal = discounts[0].get("name", "") if discounts else None
        code = item.get("code", "")
        url = item.get("redirection_url") or f"{FOODPANDA_URL}/restaurant/{code}"
        return {
            "name": name, "rating": rating_val, "review_count": review_count,
            "delivery_time": f"{int(delivery_time)} min" if delivery_time else None,
            "delivery_fee": f"Rs. {int(delivery_fee)}" if delivery_fee else None,
            "min_order": f"Rs. {int(min_order)}" if min_order else None,
            "cuisines": cuisines[:4], "deal": deal, "url": url, "code": code,
        }

    # ── Menu ───────────────────────────────────────────────────────────

    async def scrape_restaurant_menu(self, url: str, budget_per_person: int = None) -> list[dict]:
        """Fetch full menu with product IDs and prices via API."""
        code = None
        match = re.search(r'/restaurant/([^/]+)', url)
        if match:
            code = match.group(1)
        if not code:
            print(f"[api] Can't extract vendor code from: {url}")
            return []

        self.current_vendor_code = code

        try:
            print(f"[api] Fetching menu for vendor: {code}")
            headers = {**VENDOR_HEADERS, "perseus-session-id": self.session_id}
            resp = await self.client.get(
                f"{VENDOR_API}/{code}",
                params={"include": "menus", "language_id": 1},
                headers=headers,
            )
            data = resp.json().get("data", {})
            menus = data.get("menus", [])

            items = []
            for menu in menus:
                for category in menu.get("menu_categories", []):
                    cat_name = category.get("name", "")
                    for product in category.get("products", []):
                        name = product.get("name", "")
                        if not name:
                            continue
                        variations = product.get("product_variations", [])
                        price = variations[0].get("price", 0) if variations else 0
                        variation_id = variations[0].get("id", 0) if variations else 0
                        product_id = product.get("id", 0)
                        description = product.get("description", "")

                        items.append({
                            "name": name,
                            "price": int(price) if price else None,
                            "price_display": f"Rs. {int(price)}" if price else "",
                            "description": description[:100] if description else "",
                            "category": cat_name,
                            "product_id": product_id,
                            "variation_id": variation_id,
                        })

            print(f"[api] Found {len(items)} menu items")
            return items
        except Exception as e:
            print(f"[api] Menu error: {e}")
            return []

    # ── Cart & Ordering (client-side + browser checkout) ───────────────

    async def add_item_to_cart(self, item_name: str, quantity: int = 1) -> bool:
        """No-op for API mode - cart is managed in the agent."""
        print(f"[api] Cart updated: {quantity}x {item_name}")
        return True

    async def get_cart_summary(self) -> dict:
        """No-op - cart is in agent memory."""
        return {"items": [], "total": None}

    async def open_cart(self) -> bool:
        return True

    async def proceed_to_checkout(self) -> bool:
        """Open Foodpanda in the user's real browser for checkout."""
        if self.current_vendor_code:
            url = f"{FOODPANDA_URL}/restaurant/{self.current_vendor_code}"
            print(f"[api] Opening in browser for checkout: {url}")
            webbrowser.open(url)
            return True
        return False

    async def get_current_url(self) -> str:
        if self.current_vendor_code:
            return f"{FOODPANDA_URL}/restaurant/{self.current_vendor_code}"
        return FOODPANDA_URL

    async def screenshot(self, name: str = "debug"):
        """No-op for API mode."""
        pass

    async def _dismiss_popups(self):
        """No-op for API mode."""
        pass
