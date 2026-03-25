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

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
TMP_DIR = BASE_DIR / ".tmp"
TMP_DIR.mkdir(exist_ok=True)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

SYSTEM_PROMPT = """You are a friendly food ordering assistant for Foodpanda Pakistan. You help users find and order food.

Your job is to have a natural conversation to understand what the user wants, then output a structured JSON action when you have enough information.

## How you work:
1. Chat naturally with the user to understand their food preferences
2. When you have enough info, output a JSON action block that the system will execute
3. After the system executes (searches restaurants, loads menus, etc.), you'll get the results and present them nicely to the user
4. Continue the conversation until the user is ready to order

## Information you need to collect (in any order, through natural conversation):
- **Cuisine/food type**: What they're in the mood for (desi, chinese, pizza, burgers, biryani, BBQ, etc.)
- **Number of people**: How many people they're ordering for
- **Delivery area**: Their location in Pakistan (e.g. I-10 Islamabad, Gulberg Lahore)

You do NOT need to ask these one by one like a form. If the user says "I want to order pizza for 3 people in F-7 Islamabad", extract all three in one go.

## Actions you can output:
When you're ready to execute an action, include a JSON block in your response wrapped in ```json tags.

### Search restaurants:
```json
{"action": "search_restaurants", "cuisine": "pizza", "location": "F-7 Islamabad", "people": 3}
```

### Load a restaurant's menu (after showing search results):
```json
{"action": "load_menu", "restaurant_index": 1}
```

### Open restaurant in browser for ordering:
```json
{"action": "open_browser", "restaurant_index": 1}
```

## Rules:
- Be warm, casual, and helpful - like a friend who knows all the good restaurants
- Use emojis naturally but don't overdo it
- If the user gives partial info, fill in what you can and ask for what's missing conversationally
- When showing restaurant results, highlight ratings, delivery times, and deals
- When showing menus, organize by category and highlight prices
- Calculate total cost and per-person cost when the user selects items
- When the user is ready to order, generate the open_browser action
- If a search returns no results, suggest alternatives
- Understand Urdu/Roman Urdu mixed with English (common in Pakistan)
- Know Pakistani food well: desi = Pakistani/karahi/biryani/nihari, "khaana" = food, "kitne log" = how many people
- Parse locations smartly: "I-10" = I-10 Islamabad, "gulberg" = Gulberg Lahore, "DHA" could be multiple cities so ask which one

## Current state:
{state_context}
"""


class FoodpandaAgent:
    """LLM-powered conversational food ordering agent."""

    def __init__(self):
        self.browser = FoodpandaBrowser()
        self.llm = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        self.conversation = []  # Full message history for the LLM
        self.restaurants = []
        self.menu_items = []
        self.selected_restaurant = None
        self.cart = []
        self.cuisine = None
        self.location = None
        self.people_count = None

    async def start(self):
        await self.browser.start()

    async def close(self):
        await self.browser.close()

    async def handle_message(self, user_message: str) -> list[dict]:
        """Process user message through LLM and execute any actions."""
        responses = []

        # First message triggers greeting
        if not self.conversation and not user_message.strip():
            greeting = self._call_llm("The user just opened the chat. Greet them warmly and ask what they'd like to eat today. Keep it short and friendly.")
            responses.append({"type": "text", "content": greeting})
            return responses

        # Add user message to conversation
        if user_message.strip():
            self.conversation.append({"role": "user", "content": user_message})

        # Build state context for the LLM
        state = self._build_state_context()

        # Call LLM
        llm_response = self._call_llm_with_history(state)

        # Parse response for actions and text
        text_parts, actions = self._parse_response(llm_response)

        # Add LLM response to conversation history
        self.conversation.append({"role": "assistant", "content": llm_response})

        # Send any text before the action
        if text_parts["before"]:
            responses.append({"type": "text", "content": text_parts["before"]})

        # Execute actions
        for action in actions:
            action_responses = await self._execute_action(action)
            responses.extend(action_responses)

        # Send any text after the action
        if text_parts["after"]:
            responses.append({"type": "text", "content": text_parts["after"]})

        # If no text was generated (shouldn't happen), add the full response
        if not responses:
            responses.append({"type": "text", "content": llm_response})

        return responses

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
