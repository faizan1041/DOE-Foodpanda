"""
Lunch Scheduler (Layer 3 - Execution)
Daily restaurant search, scoring, and notification logic.
Triggered by APScheduler at 12:30 PM PKT.
"""

import asyncio
import json
import os
import subprocess
from datetime import date, timedelta

from foodpanda_browser import FoodpandaBrowser
import lunch_db


def score_restaurants(restaurants: list[dict], recent_orders: list[dict], blacklist: list[dict]) -> list[dict]:
    """Score and rank restaurants based on rating, variety, recency, and deals.

    Scoring (0-100 scale):
    - base_rating: (rating / 5.0) * 40  →  up to 40 pts
    - variety_bonus: +20 if not ordered in last 4 days, +15 if cuisine not in last 2 days, +10 if never ordered
    - recency_penalty: -30 yesterday, -20 two days ago, -10 three days ago
    - deal_bonus: +10 if active deal
    - delivery_bonus: +5 if ≤30 min, +2 if ≤45 min
    """
    blacklisted_names = {b["restaurant_name"].lower() for b in blacklist}
    blacklisted_codes = {b["restaurant_code"] for b in blacklist if b.get("restaurant_code")}

    # Build recency maps from order history
    today = date.today()
    restaurant_last_ordered = {}  # restaurant_name.lower() → days_ago
    cuisine_last_ordered = {}     # cuisine.lower() → days_ago
    all_ordered_names = set()

    for order in recent_orders:
        order_date = date.fromisoformat(order["order_date"])
        days_ago = (today - order_date).days
        rname = order["restaurant_name"].lower()
        all_ordered_names.add(rname)
        if rname not in restaurant_last_ordered or days_ago < restaurant_last_ordered[rname]:
            restaurant_last_ordered[rname] = days_ago
        if order.get("cuisine"):
            cname = order["cuisine"].lower()
            if cname not in cuisine_last_ordered or days_ago < cuisine_last_ordered[cname]:
                cuisine_last_ordered[cname] = days_ago

    scored = []
    for r in restaurants:
        name_lower = r["name"].lower()
        code = r.get("code", "")

        # Skip blacklisted
        if name_lower in blacklisted_names or code in blacklisted_codes:
            continue

        rating = r.get("rating") or 0
        if rating < 3.5:
            continue

        # Base rating score (up to 40)
        base_score = (rating / 5.0) * 40

        # Variety bonus
        variety = 0
        days_since = restaurant_last_ordered.get(name_lower)
        if days_since is None:
            variety += 20 + 10  # not ordered in last 4 days + never ordered
        elif days_since >= 4:
            variety += 20
        # Cuisine variety
        restaurant_cuisines = [c.lower() for c in r.get("cuisines", [])]
        cuisine_recent = False
        for c in restaurant_cuisines:
            if c in cuisine_last_ordered and cuisine_last_ordered[c] <= 2:
                cuisine_recent = True
                break
        if not cuisine_recent:
            variety += 15

        # Recency penalty
        recency = 0
        if days_since is not None:
            if days_since == 0:
                recency = -30
            elif days_since == 1:
                recency = -30
            elif days_since == 2:
                recency = -20
            elif days_since == 3:
                recency = -10

        # Deal bonus
        deal = 10 if r.get("deal") else 0

        # Delivery time bonus
        delivery = 0
        dt = r.get("delivery_time", "")
        if dt:
            try:
                minutes = int(dt.replace(" min", "").strip())
                if minutes <= 30:
                    delivery = 5
                elif minutes <= 45:
                    delivery = 2
            except (ValueError, AttributeError):
                pass

        total_score = base_score + variety + recency + deal + delivery
        scored.append({
            **r,
            "score": round(total_score, 1),
            "score_breakdown": {
                "base_rating": round(base_score, 1),
                "variety_bonus": variety,
                "recency_penalty": recency,
                "deal_bonus": deal,
                "delivery_bonus": delivery,
            },
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored


async def run_daily_lunch_search() -> list[dict]:
    """Main scheduled function: search, score, notify."""
    print("[scheduler] Running daily lunch search...")

    location = lunch_db.get_config("default_location", "I-10 Islamabad")
    print(f"[scheduler] Location: {location}")

    # Search restaurants
    browser = FoodpandaBrowser()
    await browser.start()
    try:
        await browser.set_location(location)
        raw_restaurants = await browser.scrape_restaurants(max_results=50)
    finally:
        await browser.close()

    if not raw_restaurants:
        print("[scheduler] No restaurants found")
        send_notification("Lunch Bot", "Couldn't find restaurants today. Open the chat to search manually.")
        return []

    # Get history and blacklist
    recent_orders = lunch_db.get_recent_orders(days=7)
    blacklist = lunch_db.get_blacklist()

    # Score and rank
    scored = score_restaurants(raw_restaurants, recent_orders, blacklist)
    top_5 = scored[:5]

    if not top_5:
        print("[scheduler] No restaurants passed scoring")
        send_notification("Lunch Bot", "No good restaurants found today. Try the chat for a manual search.")
        return []

    # Save suggestions
    lunch_db.save_daily_suggestions(top_5)

    # Build notification
    lines = ["Today's lunch picks:"]
    for i, r in enumerate(top_5, 1):
        deal_tag = f" | {r['deal']}" if r.get("deal") else ""
        lines.append(f"{i}. {r['name']} - {r.get('rating', '?')}/5 - {r.get('delivery_time', '?')}{deal_tag}")
    lines.append("\nOpen http://localhost:8422 to order!")
    body = "\n".join(lines)

    send_notification("Lunch Bot - Your picks are ready!", body)
    print(f"[scheduler] Suggested {len(top_5)} restaurants")
    return top_5


def send_notification(title: str, body: str):
    """Send a desktop notification via notify-send (Linux)."""
    try:
        subprocess.run(
            ["notify-send", "--urgency=normal", "--icon=dialog-information", title, body],
            timeout=5,
            check=False,
        )
        print(f"[notify] Sent: {title}")
    except FileNotFoundError:
        print("[notify] notify-send not found (install libnotify-bin)")
    except Exception as e:
        print(f"[notify] Error: {e}")


# Allow running standalone for testing
if __name__ == "__main__":
    results = asyncio.run(run_daily_lunch_search())
    if results:
        print(f"\nTop {len(results)} suggestions:")
        for i, r in enumerate(results, 1):
            print(f"  {i}. {r['name']} (score: {r['score']}) - {r.get('rating')}/5 - {r.get('deal', 'No deal')}")
            print(f"     Breakdown: {r['score_breakdown']}")
