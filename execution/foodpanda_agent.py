"""
Foodpanda Ordering Agent (Layer 3 - Execution)

Architecture:
- Chat layer: Claude Code CLI (claude -p) -- uses existing subscription, no API key
- Execution layer: Deterministic tools (search, menu, log, blacklist)
- Scheduler layer: Fully automated daily flow (no LLM needed)

The LLM is ONLY used in the chat to understand user intent and decide which
action to take. All actual work is done by deterministic Python functions.
Claude Code CLI is called via subprocess -- zero extra API keys.
"""

import asyncio
import json
import os
import subprocess
import shutil
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from foodpanda_browser import FoodpandaBrowser
import lunch_db

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
TMP_DIR = BASE_DIR / ".tmp"
TMP_DIR.mkdir(exist_ok=True)

CLAUDE_BIN = shutil.which("claude") or "claude"

SYSTEM_PROMPT = """You are a lunch ordering assistant for Foodpanda Pakistan embedded in a chat UI.

You will receive the user's message plus context about available restaurants, current state, etc.
Your job: understand what the user wants and respond with EITHER:

1. A natural text reply (for conversation, clarification, presenting info)
2. A JSON action block (when you need to execute something)

## Actions you can request (wrap in ```json tags):

### Search restaurants:
```json
{"action": "search_restaurants", "location": "I-10 Islamabad", "cuisine": "pizza"}
```
- location is required, cuisine is optional
- Know Pakistani areas: "I-10" = I-10 Islamabad, "gulberg" = Gulberg Lahore, "F-7" = F-7 Islamabad

### Load a restaurant menu:
```json
{"action": "load_menu", "number": 1}
```

### Open restaurant in browser for ordering:
```json
{"action": "open_restaurant", "number": 1}
```

### Log what the user ordered:
```json
{"action": "log_order", "restaurant_name": "Savour Foods", "items": ["Chicken Biryani", "Raita"], "cuisine": "Pakistani"}
```

### Blacklist a restaurant:
```json
{"action": "blacklist", "restaurant_name": "Bad Place", "reason": "food was stale"}
```

### Show today's pre-computed suggestions:
```json
{"action": "show_suggestions"}
```

### Show order history:
```json
{"action": "show_history"}
```

## Rules:
- Be concise. This is a chat, not an essay.
- Understand Urdu/Roman Urdu mixed with English (khaana=food, kitne log=how many people)
- Know Pakistani food: desi=Pakistani/karahi/biryani, etc.
- Parse locations smartly, default to their saved location if they don't specify
- After opening a restaurant for ordering, ask what they ended up ordering
- If someone had a bad experience, offer to blacklist
- When presenting search results or suggestions, just say a brief intro -- the UI renders the cards
- Use the user's default location if they don't specify one
"""


def _call_claude(prompt: str) -> str:
    """Call Claude Code CLI and return the text response."""
    try:
        result = subprocess.run(
            [CLAUDE_BIN, "-p", "--output-format", "json", "--model", "haiku"],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            print(f"[agent] claude CLI error: {result.stderr[:200]}")
            return ""

        data = json.loads(result.stdout)
        return data.get("result", "")
    except subprocess.TimeoutExpired:
        print("[agent] claude CLI timed out")
        return ""
    except (json.JSONDecodeError, Exception) as e:
        print(f"[agent] claude CLI parse error: {e}")
        return ""


def _parse_response(text: str) -> tuple[str, list[dict]]:
    """Split Claude's response into display text and action blocks."""
    import re
    actions = []
    clean_text = text

    # Find all ```json ... ``` blocks
    pattern = r'```json\s*\n?(.*?)\n?\s*```'
    for match in re.finditer(pattern, text, re.DOTALL):
        try:
            action = json.loads(match.group(1))
            if "action" in action:
                actions.append(action)
        except json.JSONDecodeError:
            pass

    # Remove JSON blocks from display text
    clean_text = re.sub(pattern, '', text, flags=re.DOTALL).strip()
    return clean_text, actions


class FoodpandaAgent:
    """Chat agent: Claude Code CLI for understanding, deterministic tools for execution."""

    def __init__(self):
        self.browser = FoodpandaBrowser()
        self.restaurants = []
        self.menu_items = []
        self.selected_restaurant = None
        self.location = None

    async def start(self):
        await self.browser.start()

    async def close(self):
        await self.browser.close()

    def _build_context(self) -> str:
        """Build current state context for Claude."""
        parts = []

        default_loc = lunch_db.get_config("default_location", "I-10 Islamabad")
        parts.append(f"User's default location: {default_loc}")

        if self.location:
            parts.append(f"Current search location: {self.location}")

        if self.restaurants:
            r_lines = []
            for i, r in enumerate(self.restaurants[:8]):
                deal = f" | {r['deal']}" if r.get("deal") else ""
                score = f" (score: {r['score']})" if r.get("score") else ""
                r_lines.append(f"  {i+1}. {r['name']} - {r.get('rating', '?')}/5 - {r.get('delivery_time', '?')}{deal}{score}")
            parts.append(f"Current restaurant results:\n" + "\n".join(r_lines))

        if self.selected_restaurant:
            parts.append(f"Selected restaurant: {self.selected_restaurant['name']}")

        if self.menu_items:
            m_lines = [f"  - {m['name']} ({m.get('price_display', m.get('price', '?'))})" for m in self.menu_items[:15]]
            parts.append(f"Loaded menu ({len(self.menu_items)} items):\n" + "\n".join(m_lines))

        recent = lunch_db.get_recent_orders(days=7)
        if recent:
            o_lines = [f"  {o['order_date']}: {o['restaurant_name']}" for o in recent[:5]]
            parts.append(f"Recent orders:\n" + "\n".join(o_lines))

        today = lunch_db.get_today_suggestions()
        if today:
            parts.append(f"Today's pre-computed suggestions: {len(today)} restaurants available")

        return "\n".join(parts)

    async def handle_message(self, user_message: str) -> list[dict]:
        """Process user message via Claude Code CLI + deterministic tools."""
        responses = []

        # First message -- build an init prompt
        if not user_message:
            today = lunch_db.get_today_suggestions()
            if today:
                self.restaurants = today
                self.location = lunch_db.get_config("default_location", "I-10 Islamabad")
                user_message = "[System: User just opened the chat. Today's suggestions are ready. Greet them briefly and show suggestions.]"
            else:
                user_message = "[System: User just opened the chat. No suggestions today. Greet them and ask what they want to eat.]"

        # Build full prompt
        context = self._build_context()
        full_prompt = f"""{SYSTEM_PROMPT}

## Current state:
{context}

## User message:
{user_message}"""

        # Call Claude Code CLI
        claude_response = await asyncio.to_thread(_call_claude, full_prompt)

        if not claude_response:
            return [{"type": "text", "content": "Something went wrong. Try again."}]

        # Parse into text + actions
        display_text, actions = _parse_response(claude_response)

        if display_text:
            responses.append({"type": "text", "content": display_text})

        # Execute any actions
        for action in actions:
            action_responses = await self._execute_action(action)
            responses.extend(action_responses)

        # If Claude returned actions, call it again to present the results
        if actions and not display_text:
            # Add a brief context note
            responses_text = [r for r in responses if r["type"] == "text"]
            if not responses_text:
                responses.insert(0, {"type": "text", "content": "Here's what I found:"})

        return responses if responses else [{"type": "text", "content": claude_response}]

    async def _execute_action(self, action: dict) -> list[dict]:
        """Execute a parsed action deterministically."""
        action_type = action.get("action")
        print(f"[agent] Executing: {action_type}")

        if action_type == "search_restaurants":
            return await self._do_search(action)
        elif action_type == "load_menu":
            return await self._do_load_menu(action)
        elif action_type == "open_restaurant":
            return await self._do_open_restaurant(action)
        elif action_type == "log_order":
            return self._do_log_order(action)
        elif action_type == "blacklist":
            return self._do_blacklist(action)
        elif action_type == "show_suggestions":
            return self._do_show_suggestions()
        elif action_type == "show_history":
            return self._do_show_history()
        else:
            return []

    async def _do_search(self, action: dict) -> list[dict]:
        location = action.get("location", self.location or lunch_db.get_config("default_location", "I-10 Islamabad"))
        cuisine = action.get("cuisine")

        self.location = location
        await self.browser.start()
        await self.browser.set_location(location)
        if cuisine:
            await self.browser.search_cuisine(cuisine)
        raw = await self.browser.scrape_restaurants(max_results=25)

        ranked = sorted(raw, key=lambda r: r.get("rating") or 0, reverse=True)
        ranked = [r for r in ranked if not r.get("rating") or r["rating"] >= 3.0]
        self.restaurants = ranked[:8]

        if self.restaurants:
            return [{"type": "restaurants", "content": self.restaurants}]
        else:
            cuisine_label = f" {cuisine}" if cuisine else ""
            return [{"type": "text", "content": f"No{cuisine_label} restaurants found in **{location}**."}]

    async def _do_load_menu(self, action: dict) -> list[dict]:
        idx = action.get("number", 1) - 1
        if idx < 0 or idx >= len(self.restaurants):
            return [{"type": "text", "content": "That restaurant number doesn't exist."}]

        self.selected_restaurant = self.restaurants[idx]
        url = self.selected_restaurant.get("url", "")

        await self.browser.start()
        await self.browser.set_location(self.location or "I-10 Islamabad")
        self.menu_items = await self.browser.scrape_restaurant_menu(url)

        if self.menu_items:
            return [{"type": "menu", "content": {"restaurant": self.selected_restaurant["name"], "items": self.menu_items[:30]}}]
        else:
            return [{"type": "text", "content": f"Couldn't load the menu. Direct link: {url}"}]

    async def _do_open_restaurant(self, action: dict) -> list[dict]:
        idx = action.get("number", 1) - 1
        if idx < 0 or idx >= len(self.restaurants):
            return [{"type": "text", "content": "That restaurant number doesn't exist."}]

        self.selected_restaurant = self.restaurants[idx]
        await self.browser.start()
        self.browser.current_vendor_code = self.selected_restaurant.get("code", "")
        await self.browser.proceed_to_checkout()
        return []

    def _do_log_order(self, action: dict) -> list[dict]:
        name = action.get("restaurant_name", "")
        items = action.get("items", [])
        cuisine = action.get("cuisine", "")

        code = ""
        for r in self.restaurants:
            if r.get("name", "").lower() == name.lower():
                code = r.get("code", "")
                if not cuisine:
                    cuisines = r.get("cuisines", [])
                    cuisine = cuisines[0] if cuisines else ""
                break

        lunch_db.save_order(restaurant_name=name, restaurant_code=code, items=items, cuisine=cuisine)
        lunch_db.mark_suggestion_picked(name)
        print(f"[agent] Order logged: {name} - {items}")
        return []

    def _do_blacklist(self, action: dict) -> list[dict]:
        name = action.get("restaurant_name", "")
        reason = action.get("reason", "user requested")

        code = ""
        for r in self.restaurants:
            if r.get("name", "").lower() == name.lower():
                code = r.get("code", "")
                break

        lunch_db.blacklist_restaurant(name, code, reason)
        print(f"[agent] Blacklisted: {name}")
        return []

    def _do_show_suggestions(self) -> list[dict]:
        suggestions = lunch_db.get_today_suggestions()
        if not suggestions:
            return [{"type": "text", "content": "No suggestions ready yet for today."}]
        self.restaurants = suggestions
        self.location = lunch_db.get_config("default_location", "I-10 Islamabad")
        return [{"type": "restaurants", "content": suggestions[:5]}]

    def _do_show_history(self) -> list[dict]:
        orders = lunch_db.get_recent_orders(days=30)
        if not orders:
            return [{"type": "text", "content": "No order history yet."}]
        lines = ["**Recent orders:**\n"]
        for o in orders[:15]:
            items_str = ", ".join(o["items"]) if o.get("items") else "not recorded"
            lines.append(f"- **{o['order_date']}**: {o['restaurant_name']} ({items_str})")
        return [{"type": "text", "content": "\n".join(lines)}]
