"""
Foodpanda Ordering Agent (Layer 3 - Execution)
LLM-powered conversational agent that understands natural language,
extracts structured data, and orchestrates Foodpanda food ordering.
"""

import asyncio
import json
import os
import re
from datetime import datetime
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from foodpanda_browser import FoodpandaBrowser
import lunch_db

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
TMP_DIR = BASE_DIR / ".tmp"
TMP_DIR.mkdir(exist_ok=True)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

SYSTEM_PROMPT = """You are a friendly food ordering assistant for Foodpanda Pakistan. You help users find and order food. You also act as a proactive daily lunch assistant that tracks orders and makes smart suggestions.

Your job is to have a natural conversation to understand what the user wants, then output a structured JSON action when you have enough information.

## How you work:
1. Chat naturally with the user to understand their food preferences
2. When you have enough info, output a JSON action block that the system will execute
3. After the system executes (searches restaurants, loads menus, etc.), you'll get the results and present them nicely to the user
4. Continue the conversation until the user is ready to order
5. After the user picks a restaurant and browses the menu, proactively ask what they ended up ordering so you can log it for future suggestions

## Information you need to collect (in any order, through natural conversation):
- **Cuisine/food type**: What they're in the mood for (desi, chinese, pizza, burgers, biryani, BBQ, etc.)
- **Number of people**: How many people they're ordering for
- **Delivery area**: Their location in Pakistan (e.g. I-10 Islamabad, Gulberg Lahore)

You do NOT need to ask these one by one like a form. If the user says "I want to order pizza for 3 people in F-7 Islamabad", extract all three in one go.

## Actions you can output:
When you're ready to execute an action, include a JSON block in your response wrapped in ```json tags.

### Search restaurants:
```json
{{"action": "search_restaurants", "cuisine": "pizza", "location": "F-7 Islamabad", "people": 3}}
```

### Load a restaurant's menu (after showing search results):
```json
{{"action": "load_menu", "restaurant_index": 1}}
```

### Open restaurant in browser for ordering:
```json
{{"action": "open_browser", "restaurant_index": 1}}
```

### Log an order (after user tells you what they ordered):
```json
{{"action": "log_order", "restaurant_name": "Savour Foods", "restaurant_code": "s2hg", "items": ["Chicken Biryani", "Raita"], "cuisine": "Pakistani"}}
```

### Blacklist a restaurant (when user says never suggest a place again):
```json
{{"action": "blacklist_restaurant", "restaurant_name": "Bad Restaurant", "restaurant_code": "xxxx", "reason": "food quality was poor"}}
```

### Show today's pre-computed lunch suggestions:
```json
{{"action": "show_today_suggestions"}}
```

## Rules:
- Be warm, casual, and helpful - like a friend who knows all the good restaurants
- Use emojis naturally but don't overdo it
- If the user gives partial info, fill in what you can and ask for what's missing conversationally
- When showing restaurant results, highlight ratings, delivery times, and deals
- When showing menus, organize by category and highlight prices
- Calculate total cost and per-person cost when the user selects items
- When the user is ready to order, generate the open_browser action
- After opening the browser for ordering, ask the user what they ended up ordering so you can track it
- If a search returns no results, suggest alternatives
- Understand Urdu/Roman Urdu mixed with English (common in Pakistan)
- Know Pakistani food well: desi = Pakistani/karahi/biryani/nihari, "khaana" = food, "kitne log" = how many people
- Parse locations smartly: "I-10" = I-10 Islamabad, "gulberg" = Gulberg Lahore, "DHA" could be multiple cities so ask which one
- If the user mentions a bad experience at a restaurant, offer to blacklist it
- When suggesting restaurants, mention if the user hasn't tried a place before or hasn't had that cuisine recently
- If today's lunch suggestions are available, show them when the user opens the chat around lunch time

## Current state:
{state_context}
"""


class FoodpandaAgent:
    """Food ordering agent with deterministic lunch flow + optional LLM for general chat."""

    # Lunch flow states
    LUNCH_IDLE = "idle"
    LUNCH_AWAITING_PICK = "awaiting_pick"       # Showed suggestions, waiting for restaurant number
    LUNCH_AWAITING_ORDER = "awaiting_order"      # User picked restaurant, waiting for what they ordered
    LUNCH_AWAITING_BLACKLIST = "awaiting_blacklist"  # Asked if they want to blacklist

    def __init__(self):
        self.browser = FoodpandaBrowser()
        self.conversation = []  # Full message history for the LLM
        self.restaurants = []
        self.menu_items = []
        self.selected_restaurant = None
        self.cart = []
        self.cuisine = None
        self.location = None
        self.people_count = None
        self.lunch_state = self.LUNCH_IDLE
        self._has_llm = bool(ANTHROPIC_API_KEY)
        if self._has_llm:
            self.llm = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        else:
            self.llm = None

    async def start(self):
        await self.browser.start()

    async def close(self):
        await self.browser.close()

    async def handle_message(self, user_message: str) -> list[dict]:
        """Process user message - deterministic lunch flow first, LLM fallback for general chat."""
        responses = []
        msg = user_message.strip()

        # ── First message: show today's suggestions or greeting ──
        if not self.conversation and not msg:
            today_suggestions = lunch_db.get_today_suggestions()
            if today_suggestions:
                self.restaurants = today_suggestions
                self.location = lunch_db.get_config("default_location", "I-10 Islamabad")
                self.lunch_state = self.LUNCH_AWAITING_PICK

                # Build recent orders context
                recent = lunch_db.get_recent_orders(days=4)
                recent_text = ""
                if recent:
                    recent_names = [o["restaurant_name"] for o in recent[:4]]
                    recent_text = f"\n\nYou recently ordered from: {', '.join(recent_names)}"

                responses.append({
                    "type": "text",
                    "content": f"Hey! Your lunch picks for today are ready 🍽️{recent_text}\n\nPick a number to see the menu, or type **'order [number]'** to open it directly:"
                })
                responses.append({"type": "restaurants", "content": today_suggestions[:5]})
                return responses
            else:
                responses.append({
                    "type": "text",
                    "content": "Hey! What are you in the mood for today? Tell me a cuisine and your area, and I'll find the best spots for you."
                })
                return responses

        # ── Deterministic lunch flow ──
        lunch_response = await self._handle_lunch_flow(msg)
        if lunch_response is not None:
            return lunch_response

        # ── Fallback: LLM-powered general chat (if API key available) ──
        if self._has_llm:
            if msg:
                self.conversation.append({"role": "user", "content": msg})
            state = self._build_state_context()
            llm_response = self._call_llm_with_history(state)
            text_parts, actions = self._parse_response(llm_response)
            self.conversation.append({"role": "assistant", "content": llm_response})

            if text_parts["before"]:
                responses.append({"type": "text", "content": text_parts["before"]})
            for action in actions:
                action_responses = await self._execute_action(action)
                responses.extend(action_responses)
            if text_parts["after"]:
                responses.append({"type": "text", "content": text_parts["after"]})
            if not responses:
                responses.append({"type": "text", "content": llm_response})
        else:
            # No LLM available - handle basic commands deterministically
            responses = await self._handle_basic_command(msg)

        return responses

    async def _handle_lunch_flow(self, msg: str) -> list[dict] | None:
        """Handle the deterministic lunch flow. Returns None if not a lunch command."""
        msg_lower = msg.lower().strip()

        # ── Blacklist commands (work in any state) ──
        if msg_lower.startswith("blacklist ") or msg_lower.startswith("never suggest "):
            name = msg.split(" ", 1)[1] if msg_lower.startswith("blacklist ") else msg.split("suggest ", 1)[1]
            # Try to match against current restaurants
            matched = self._match_restaurant(name)
            if matched:
                lunch_db.blacklist_restaurant(matched["name"], matched.get("code", ""), "user requested")
                return [{"type": "text", "content": f"Done! **{matched['name']}** has been blacklisted. I won't suggest it again."}]
            else:
                lunch_db.blacklist_restaurant(name.strip(), "", "user requested")
                return [{"type": "text", "content": f"Done! **{name.strip()}** has been blacklisted."}]

        # ── Show history ──
        if msg_lower in ("history", "order history", "past orders"):
            orders = lunch_db.get_recent_orders(days=30)
            if not orders:
                return [{"type": "text", "content": "No order history yet!"}]
            lines = ["**Your recent orders:**\n"]
            for o in orders[:15]:
                items_str = ", ".join(o["items"]) if o.get("items") else "not specified"
                lines.append(f"- **{o['order_date']}**: {o['restaurant_name']} ({items_str})")
            return [{"type": "text", "content": "\n".join(lines)}]

        # ── Show blacklist ──
        if msg_lower in ("blacklist", "show blacklist", "blocked"):
            bl = lunch_db.get_blacklist()
            if not bl:
                return [{"type": "text", "content": "No blacklisted restaurants."}]
            lines = ["**Blacklisted restaurants:**\n"]
            for b in bl:
                lines.append(f"- {b['restaurant_name']}: {b.get('reason', 'no reason')}")
            return [{"type": "text", "content": "\n".join(lines)}]

        # ── State: Awaiting restaurant pick ──
        if self.lunch_state == self.LUNCH_AWAITING_PICK:
            # Check if user typed a number
            num = self._extract_number(msg_lower)

            # "order 3" or "open 3" — open directly in browser
            if msg_lower.startswith("order") or msg_lower.startswith("open"):
                parts = msg_lower.split()
                if len(parts) >= 2:
                    num = self._extract_number(parts[1])
                if num and 1 <= num <= len(self.restaurants):
                    idx = num - 1
                    self.selected_restaurant = self.restaurants[idx]
                    url = self.selected_restaurant.get("url", "https://www.foodpanda.pk")
                    await self.browser.start()
                    self.browser.current_vendor_code = self.selected_restaurant.get("code", "")
                    await self.browser.proceed_to_checkout()
                    self.lunch_state = self.LUNCH_AWAITING_ORDER
                    return [{"type": "text", "content": f"Opening **{self.selected_restaurant['name']}** in your browser!\n\n🔗 {url}\n\nOnce you've ordered, tell me what you got so I can save it! Just type the items (e.g. \"chicken biryani, raita\")"}]

            # Just a number — show menu
            if num and 1 <= num <= len(self.restaurants):
                idx = num - 1
                self.selected_restaurant = self.restaurants[idx]
                url = self.selected_restaurant.get("url", "")
                await self.browser.start()
                await self.browser.set_location(self.location or "I-10 Islamabad")
                menu_items = await self.browser.scrape_restaurant_menu(url)
                self.menu_items = menu_items

                responses = []
                if menu_items:
                    responses.append({
                        "type": "text",
                        "content": f"Here's the menu for **{self.selected_restaurant['name']}**:"
                    })
                    responses.append({
                        "type": "menu",
                        "content": {"restaurant": self.selected_restaurant["name"], "items": menu_items[:30]},
                    })
                    responses.append({
                        "type": "text",
                        "content": f"Type **'order {num}'** to open it in Foodpanda, or pick another number."
                    })
                else:
                    responses.append({
                        "type": "text",
                        "content": f"Couldn't load the menu for **{self.selected_restaurant['name']}**.\n\nType **'order {num}'** to open it directly on Foodpanda."
                    })
                return responses

            # Not a number — don't handle, let it fall through
            return None

        # ── State: Awaiting what they ordered ──
        if self.lunch_state == self.LUNCH_AWAITING_ORDER:
            if msg_lower in ("skip", "nothing", "cancel", "nevermind"):
                self.lunch_state = self.LUNCH_IDLE
                return [{"type": "text", "content": "No worries! Your order wasn't logged."}]

            # Parse items from the message (comma-separated or just the whole message)
            items = [item.strip() for item in msg.split(",") if item.strip()]
            if not items:
                items = [msg]

            restaurant_name = self.selected_restaurant["name"] if self.selected_restaurant else "Unknown"
            restaurant_code = self.selected_restaurant.get("code", "") if self.selected_restaurant else ""
            cuisines = self.selected_restaurant.get("cuisines", []) if self.selected_restaurant else []
            cuisine = cuisines[0] if cuisines else ""

            lunch_db.save_order(
                restaurant_name=restaurant_name,
                restaurant_code=restaurant_code,
                items=items,
                cuisine=cuisine,
            )
            lunch_db.mark_suggestion_picked(restaurant_name)
            self.lunch_state = self.LUNCH_IDLE
            print(f"[agent] Order logged: {restaurant_name} - {items}")

            return [{"type": "text", "content": f"Got it! Logged your order from **{restaurant_name}**: {', '.join(items)}\n\nI'll factor this into tomorrow's suggestions. Enjoy your meal!"}]

        return None

    async def _handle_basic_command(self, msg: str) -> list[dict]:
        """Handle basic commands without LLM."""
        msg_lower = msg.lower().strip()

        # Search command
        if any(msg_lower.startswith(kw) for kw in ["search", "find", "show me"]):
            return [{"type": "text", "content": "To search, I need your area and what you're craving. For example: **'pizza in I-10 Islamabad'**"}]

        # Trigger suggestions
        if msg_lower in ("suggestions", "suggest", "lunch", "what should i eat"):
            suggestions = lunch_db.get_today_suggestions()
            if suggestions:
                self.restaurants = suggestions
                self.lunch_state = self.LUNCH_AWAITING_PICK
                return [
                    {"type": "text", "content": "Here are today's picks! Type a number to see the menu:"},
                    {"type": "restaurants", "content": suggestions[:5]},
                ]
            return [{"type": "text", "content": "No suggestions ready yet. Use **/api/trigger-lunch-search** to generate them, or tell me what cuisine you want!"}]

        return [{"type": "text", "content": "I can help you with lunch! Try:\n- **'suggestions'** — see today's picks\n- **'history'** — see past orders\n- **'blacklist [name]'** — block a restaurant\n- Or just tell me what you're craving!"}]

    def _extract_number(self, text: str) -> int | None:
        """Extract a number from text."""
        match = re.match(r'^(\d+)$', text.strip())
        if match:
            return int(match.group(1))
        return None

    def _match_restaurant(self, name: str) -> dict | None:
        """Try to match a name against current restaurant list."""
        name_lower = name.lower().strip()
        for r in self.restaurants:
            if name_lower in r["name"].lower():
                return r
        return None

    # ── LLM Calls ──────────────────────────────────────────────────────

    def _call_llm(self, prompt: str) -> str:
        """Simple one-shot LLM call."""
        try:
            resp = self.llm.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                system=SYSTEM_PROMPT.replace("{state_context}", self._build_state_context()),
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.content[0].text
        except Exception as e:
            print(f"[agent] LLM error: {e}")
            return "Hey! I'm having a moment - could you try that again? 😅"

    def _call_llm_with_history(self, state_context: str) -> str:
        """Call LLM with full conversation history."""
        try:
            resp = self.llm.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
                system=SYSTEM_PROMPT.replace("{state_context}", state_context),
                messages=self.conversation,
            )
            return resp.content[0].text
        except Exception as e:
            print(f"[agent] LLM error: {e}")
            return "Sorry, I hit a snag. Could you say that again?"

    def _build_state_context(self) -> str:
        """Build context about current state for the LLM."""
        parts = []
        if self.cuisine:
            parts.append(f"Cuisine: {self.cuisine}")
        if self.location:
            parts.append(f"Location: {self.location}")
        if self.people_count:
            parts.append(f"People: {self.people_count}")
        if self.restaurants:
            rest_list = "\n".join(
                f"  {i+1}. {r['name']} - ⭐{r.get('rating', 'N/A')} - {r.get('delivery_time', '')} - {r.get('deal', 'No deal')} - {r.get('url', '')}"
                for i, r in enumerate(self.restaurants)
            )
            parts.append(f"Search results ({len(self.restaurants)} restaurants):\n{rest_list}")
        if self.selected_restaurant:
            parts.append(f"Selected restaurant: {self.selected_restaurant['name']}")
        if self.menu_items:
            menu_preview = "\n".join(
                f"  {i+1}. {item['name']} - {item.get('price_display', '')} [{item.get('category', '')}]"
                for i, item in enumerate(self.menu_items[:30])
            )
            parts.append(f"Menu ({len(self.menu_items)} items):\n{menu_preview}")
        if self.cart:
            cart_lines = "\n".join(
                f"  {item['quantity']}x {item['name']} - Rs. {item.get('price', 0) * item['quantity']}"
                for item in self.cart
            )
            total = sum(i.get("price", 0) * i["quantity"] for i in self.cart)
            parts.append(f"Cart:\n{cart_lines}\n  Total: Rs. {total:,}")

        # Order history (last 7 days)
        recent_orders = lunch_db.get_recent_orders(days=7)
        if recent_orders:
            order_lines = []
            for o in recent_orders[:10]:
                items_str = ", ".join(o["items"]) if o.get("items") else "unknown items"
                order_lines.append(f"  {o['order_date']}: {o['restaurant_name']} ({items_str})")
            parts.append(f"Recent orders (last 7 days):\n" + "\n".join(order_lines))

        # Blacklist
        blacklist = lunch_db.get_blacklist()
        if blacklist:
            bl_lines = [f"  - {b['restaurant_name']}: {b.get('reason', 'no reason given')}" for b in blacklist[:10]]
            parts.append(f"Blacklisted restaurants:\n" + "\n".join(bl_lines))

        # Today's suggestions
        today_suggestions = lunch_db.get_today_suggestions()
        if today_suggestions:
            sug_lines = []
            for i, s in enumerate(today_suggestions[:5], 1):
                deal_tag = f" | {s['deal']}" if s.get("deal") else ""
                sug_lines.append(f"  {i}. {s['name']} - ⭐{s.get('rating', '?')} - {s.get('delivery_time', '?')}{deal_tag} (score: {s.get('score', '?')})")
            parts.append(f"Today's lunch suggestions (pre-computed):\n" + "\n".join(sug_lines))

        return "\n".join(parts) if parts else "No information collected yet."

    # ── Response Parsing ───────────────────────────────────────────────

    def _parse_response(self, response: str) -> tuple[dict, list]:
        """Extract text and JSON action blocks from LLM response."""
        text_parts = {"before": "", "after": ""}
        actions = []

        # Find all JSON code blocks
        pattern = r'```json\s*\n?(.*?)\n?\s*```'
        matches = list(re.finditer(pattern, response, re.DOTALL))

        if not matches:
            text_parts["before"] = response.strip()
            return text_parts, actions

        # Text before first action
        text_parts["before"] = response[:matches[0].start()].strip()

        # Text after last action
        text_parts["after"] = response[matches[-1].end():].strip()

        # Parse each JSON block
        for match in matches:
            try:
                action = json.loads(match.group(1))
                if "action" in action:
                    actions.append(action)
            except json.JSONDecodeError as e:
                print(f"[agent] JSON parse error: {e}")

        return text_parts, actions

    # ── Action Execution ───────────────────────────────────────────────

    async def _execute_action(self, action: dict) -> list[dict]:
        """Execute a parsed action and return responses."""
        responses = []
        action_type = action.get("action")

        if action_type == "search_restaurants":
            responses = await self._do_search(action)
        elif action_type == "load_menu":
            responses = await self._do_load_menu(action)
        elif action_type == "open_browser":
            responses = await self._do_open_browser(action)
        elif action_type == "log_order":
            responses = self._do_log_order(action)
        elif action_type == "blacklist_restaurant":
            responses = self._do_blacklist(action)
        elif action_type == "show_today_suggestions":
            responses = self._do_show_suggestions()

        # Feed results back to LLM for natural presentation
        if responses:
            result_context = json.dumps([r for r in responses if r["type"] != "text"], default=str)
            if result_context != "[]":
                # Add result to conversation so LLM knows what happened
                self.conversation.append({
                    "role": "user",
                    "content": f"[SYSTEM: Action '{action_type}' completed. Results are being shown to the user. Continue the conversation naturally based on the results.]"
                })

        return responses

    async def _do_search(self, action: dict) -> list[dict]:
        """Search for restaurants."""
        responses = []
        self.cuisine = action.get("cuisine", self.cuisine)
        self.location = action.get("location", self.location)
        self.people_count = action.get("people", self.people_count)

        if not self.location:
            responses.append({"type": "text", "content": "I need your delivery area to search. Where should I deliver to?"})
            return responses

        await self.browser.set_location(self.location)
        if self.cuisine:
            await self.browser.search_cuisine(self.cuisine)
        raw = await self.browser.scrape_restaurants(max_results=25)

        # Rank by rating
        ranked = sorted(raw, key=lambda r: r.get("rating") or 0, reverse=True)
        # Filter out < 3.0 rating
        ranked = [r for r in ranked if not r.get("rating") or r["rating"] >= 3.0]
        self.restaurants = ranked[:8]

        if self.restaurants:
            responses.append({
                "type": "restaurants",
                "content": self.restaurants,
            })
        else:
            responses.append({
                "type": "text",
                "content": f"No restaurants found for **{self.cuisine}** in **{self.location}**. Try a different cuisine or area!"
            })

        return responses

    async def _do_load_menu(self, action: dict) -> list[dict]:
        """Load a restaurant's menu."""
        responses = []
        idx = action.get("restaurant_index", 1) - 1

        if not self.restaurants or idx < 0 or idx >= len(self.restaurants):
            responses.append({"type": "text", "content": "That restaurant number doesn't exist. Pick from the list!"})
            return responses

        self.selected_restaurant = self.restaurants[idx]
        url = self.selected_restaurant.get("url", "")

        self.menu_items = await self.browser.scrape_restaurant_menu(url)

        if self.menu_items:
            responses.append({
                "type": "menu",
                "content": {
                    "restaurant": self.selected_restaurant.get("name"),
                    "items": self.menu_items[:30],
                },
            })
        else:
            responses.append({
                "type": "text",
                "content": f"Couldn't load the menu. You can check it directly: 🔗 {url}"
            })

        return responses

    async def _do_open_browser(self, action: dict) -> list[dict]:
        """Open restaurant in user's real browser."""
        responses = []
        idx = action.get("restaurant_index", 1) - 1

        if self.selected_restaurant:
            restaurant = self.selected_restaurant
        elif self.restaurants and 0 <= idx < len(self.restaurants):
            restaurant = self.restaurants[idx]
        else:
            responses.append({"type": "text", "content": "Pick a restaurant first!"})
            return responses

        url = restaurant.get("url", "https://www.foodpanda.pk")
        await self.browser.proceed_to_checkout()

        responses.append({
            "type": "text",
            "content": f"🎉 Opening **{restaurant['name']}** in your browser!\n\n🔗 {url}\n\nAdd the items to your cart there and complete the order. Enjoy your meal!"
        })

        return responses

    def _do_log_order(self, action: dict) -> list[dict]:
        """Log an order to the database."""
        restaurant_name = action.get("restaurant_name", "")
        if not restaurant_name and self.selected_restaurant:
            restaurant_name = self.selected_restaurant.get("name", "Unknown")

        restaurant_code = action.get("restaurant_code", "")
        if not restaurant_code and self.selected_restaurant:
            restaurant_code = self.selected_restaurant.get("code", "")

        items = action.get("items", [])
        cuisine = action.get("cuisine", "")

        lunch_db.save_order(
            restaurant_name=restaurant_name,
            restaurant_code=restaurant_code,
            items=items if items else None,
            cuisine=cuisine if cuisine else None,
        )
        lunch_db.mark_suggestion_picked(restaurant_name)
        print(f"[agent] Order logged: {restaurant_name} - {items}")
        return []

    def _do_blacklist(self, action: dict) -> list[dict]:
        """Blacklist a restaurant."""
        restaurant_name = action.get("restaurant_name", "")
        if not restaurant_name and self.selected_restaurant:
            restaurant_name = self.selected_restaurant.get("name", "Unknown")

        restaurant_code = action.get("restaurant_code", "")
        if not restaurant_code and self.selected_restaurant:
            restaurant_code = self.selected_restaurant.get("code", "")

        reason = action.get("reason", "")

        lunch_db.blacklist_restaurant(
            restaurant_name=restaurant_name,
            restaurant_code=restaurant_code,
            reason=reason,
        )
        print(f"[agent] Blacklisted: {restaurant_name} - {reason}")
        return []

    def _do_show_suggestions(self) -> list[dict]:
        """Show today's pre-computed lunch suggestions."""
        suggestions = lunch_db.get_today_suggestions()
        if not suggestions:
            return [{"type": "text", "content": "No lunch suggestions ready yet for today. Want me to search for restaurants now?"}]

        self.restaurants = suggestions
        return [{"type": "restaurants", "content": suggestions}]
