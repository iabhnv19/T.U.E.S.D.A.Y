import json
import re
import urllib.parse
import urllib.request
import warnings
import xml.etree.ElementTree as ET
import concurrent.futures
from typing import Optional

# Suppress package rename notices from duckduckgo_search
warnings.filterwarnings("ignore", category=UserWarning)


def _fetch_rss_items(url: str, limit: int = 4) -> list:
    """Fetch and parse items from an RSS feed."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            tree = ET.parse(resp)
            return tree.findall(".//item")[:limit]
    except Exception:
        return []


def fetch_live_news(query: str = "") -> str:
    """Fetch top headlines via Google News RSS without requiring API keys."""
    try:
        clean = re.sub(
            r"^(?:ok so|can you|please|tell me|give me|kuch|aaj ki|latest|breaking|news in|news about|batao|sunao|yaar|bhai)\s+",
            "",
            query,
            flags=re.IGNORECASE
        ).strip().lower()

        # Categorize by topic if requested
        if any(k in clean for k in ["tech", "technology", "ai", "artificial intelligence", "robot", "software"]):
            url = "https://news.google.com/rss/search?q=technology+AI&hl=en-IN&gl=IN&ceid=IN:en"
        elif any(k in clean for k in ["cricket", "sports", "ipl", "match", "football", "khel"]):
            url = "https://news.google.com/rss/search?q=cricket+sports&hl=en-IN&gl=IN&ceid=IN:en"
        elif any(k in clean for k in ["bollywood", "movie", "entertainment", "cinema", "film"]):
            url = "https://news.google.com/rss/search?q=bollywood+entertainment&hl=en-IN&gl=IN&ceid=IN:en"
        elif clean and not any(k in clean for k in ["taza", "khabar", "samachar", "tadapti", "bhadakti", "kuch", "news"]):
            encoded = urllib.parse.quote(clean)
            url = f"https://news.google.com/rss/search?q={encoded}&hl=en-IN&gl=IN&ceid=IN:en"
        else:
            url = "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en"

        items = _fetch_rss_items(url, limit=4)
        if not items:
            # Fall back to top general headlines
            items = _fetch_rss_items("https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en", limit=4)

        if not items:
            return ""

        headlines = []
        for i, it in enumerate(items, 1):
            title = it.find("title").text if it.find("title") is not None else ""
            headlines.append(f"{i}. {title}")
        return "Live News Headlines:\n" + "\n".join(headlines)
    except Exception:
        return ""


def fetch_live_weather(query: str) -> str:
    """Fetch real-time conditions and 3-day forecast from wttr.in JSON API."""
    try:
        # Extract target city from natural language query
        m = re.search(r"(?:in|for|at|of)\s+([a-zA-Z\s]+?)(?:\s+(?:punjab|india|forecast|today|tomorrow|now)|$)", query, re.I)
        city = m.group(1).strip() if m else ""
        if not city or len(city) < 3 or city.lower() in ["5 days", "five days", "the weather", "forecast"]:
            words = re.findall(r"[a-zA-Z]+", query)
            for w in words:
                if w.lower() in ["amritsar", "delhi", "mumbai", "bangalore", "kolkata", "chandigarh", "pune", "jaipur", "london"]:
                    city = w
                    break
        if not city:
            city = "Amritsar"

        url = f"https://wttr.in/{urllib.parse.quote(city)}?format=j1"
        req = urllib.request.Request(url, headers={"User-Agent": "curl/7.68.0"})
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read().decode())
            curr = data["current_condition"][0]
            desc = curr["weatherDesc"][0]["value"]
            temp = curr["temp_C"]
            humidity = curr["humidity"]
            wind = curr["windspeedKmph"]
            res = [f"Live Weather for {city.title()}: Current {temp}°C, {desc} (Humidity: {humidity}%, Wind: {wind} km/h)."]
            res.append("Forecast:")
            for d in data.get("weather", [])[:3]:
                date = d.get("date", "")
                min_t = d.get("mintempC", "")
                max_t = d.get("maxtempC", "")
                cond = d.get("hourly", [{}])[4].get("weatherDesc", [{}])[0].get("value", "")
                res.append(f"- {date}: Min {min_t}°C, Max {max_t}°C, {cond}")
            return "\n".join(res)
    except Exception:
        return ""


def fetch_wikipedia_knowledge(query: str) -> str:
    """Query Wikipedia search API for summaries of pop culture, people, or events."""
    try:
        clean_q = re.sub(r"^(?:who is|what is|when is|tell me about|release date of|release date)\s+", "", query, flags=re.IGNORECASE).strip()
        encoded = urllib.parse.quote(clean_q)
        url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={encoded}&format=json"
        req = urllib.request.Request(url, headers={"User-Agent": "TuesdayAssistant/3.0"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode())
            results = data.get("query", {}).get("search", [])
            if not results:
                return ""

            top_title = results[0]["title"]
            encoded_title = urllib.parse.quote(top_title)
            ext_url = f"https://en.wikipedia.org/w/api.php?action=query&prop=extracts&exintro=1&explaintext=1&titles={encoded_title}&format=json"
            ext_req = urllib.request.Request(ext_url, headers={"User-Agent": "TuesdayAssistant/3.0"})
            with urllib.request.urlopen(ext_req, timeout=4) as ext_resp:
                ext_data = json.loads(ext_resp.read().decode())
                pages = ext_data.get("query", {}).get("pages", {})
                for pid, p in pages.items():
                    extract = p.get("extract", "")
                    if extract:
                        return f"Source ({top_title}): {extract[:800]}"

            snippets = [re.sub(r"<[^>]+>", "", r["snippet"]) for r in results[:2]]
            return f"Source ({top_title}): " + " ".join(snippets)
    except Exception:
        return ""


def perform_live_web_search(query: str) -> str:
    """Unified entry point for real-time weather, news, and knowledge retrieval."""
    q_lower = query.lower()

    # Weather checks
    if any(k in q_lower for k in ["weather", "forecast", "mausam", "temperature", "barish", "rain"]):
        weather_info = fetch_live_weather(query)
        if weather_info:
            return weather_info

    # News checks
    if any(k in q_lower for k in ["news", "headline", "breaking", "khabar", "samachar", "taza", "tadapti"]):
        news_info = fetch_live_news(query)
        if news_info:
            return news_info

    # Wikipedia knowledge
    wiki_info = fetch_wikipedia_knowledge(query)
    if wiki_info and len(wiki_info) > 60:
        return wiki_info

    # DuckDuckGo fallback wrapped in strict timeout to prevent hangs
    try:
        from duckduckgo_search import DDGS

        def _ddg_lookup():
            return list(DDGS().text(query, max_results=2))

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_ddg_lookup)
            results = future.result(timeout=2.5)
            if results:
                lines = [f"[{r.get('title', '')}]: {r.get('body', '')}" for r in results]
                return "\n".join(lines)
    except Exception:
        pass

    return ""
