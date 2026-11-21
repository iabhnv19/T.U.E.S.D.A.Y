"""
core/mood.py
Mood-Adaptive Personality Engine for T.U.E.S.D.A.Y.
Detects user mood from text/sentiment patterns and shifts assistant personality in real-time.
Tracks mood history in SQLite and adapts system prompt based on emotion and time of day.
"""

from datetime import datetime, timedelta
import re
from typing import Dict, Any, List, Optional, Tuple

from core.memory import MemoryStore


class MoodEngine:
    """Detects mood, manages time-of-day personality shifts, and tracks mood history."""

    _instance: Optional["MoodEngine"] = None

    def __init__(self, memory: Optional[MemoryStore] = None):
        self.memory = memory or MemoryStore()

        # Emotion lexicon (bilingual English + Hinglish)
        self._mood_lexicon = {
            "frustrated": {
                "keywords": {
                    "angry", "annoyed", "irritated", "frustrated", "hate", "damn", "stupid",
                    "idiot", "gussa", "bakwas", "bekar", "kharab", "pagal", "useless", "gadbad",
                    "dimag kharab", "chidh", "bura", "shit", "fuck", "crap", "ridiculous",
                    "slow", "hang", "crash", "bug", "error", "horrible", "terrible", "worst",
                    "mar jau", "faltu", "ghatiya"
                },
                "score": -0.8,
                "tone": "deeply empathetic, patient, calm, reassuring, and do not make jokes or be overly bubbly",
            },
            "stressed": {
                "keywords": {
                    "stress", "stressed", "tension", "worried", "worry", "panic", "pareshan",
                    "ghabrahat", "deadline", "overwhelmed", "problem", "mushkil", "pressure",
                    "anxious", "anxiety", "urgent", "busy", "load", "fat rahi", "darr", "scared",
                    "bohot kaam", "sambhal", "kaise hoga"
                },
                "score": -0.6,
                "tone": "grounding, supportive, structured, offer clear step-by-step assistance with a calm, reassuring demeanor",
            },
            "tired": {
                "keywords": {
                    "tired", "exhausted", "sleepy", "neend", "thak gaya", "thaka", "thaki",
                    "energy nahi", "drained", "headache", "sar dard", "yawning", "lazy", "alas",
                    "sone ja raha", "heavy", "fatigued", "burnt out", "burnout", "chur chur"
                },
                "score": -0.3,
                "tone": "very brief, gentle, comforting, soft-spoken, and minimize cognitive load",
            },
            "sad": {
                "keywords": {
                    "sad", "upset", "depressed", "depression", "unhappy", "dukhi", "bura lag raha",
                    "lonely", "alone", "disappointed", "heartbroken", "cry", "crying", "rona",
                    "dard", "hurt", "hopeless", "miss", "gam", "udaas", "udas"
                },
                "score": -0.7,
                "tone": "warm, caring, understanding, uplifting with genuine compassion and heartfelt kindness",
            },
            "happy": {
                "keywords": {
                    "happy", "excited", "great", "awesome", "mast", "badhiya", "shandar",
                    "zabardast", "maza", "kamaal", "congrats", "party", "love", "loved",
                    "yay", "super", "win", "won", "good", "nice", "glad", "celebrate", "proud",
                    "best", "perfect", "badiya", "khush", "success", "rocking", "cheerful", "mazedar"
                },
                "score": 0.8,
                "tone": "match user's high energy with witty, enthusiastic, cheerful charm and celebration",
            },
            "relaxed": {
                "keywords": {
                    "chill", "peace", "sukoon", "aram", "relax", "relaxed", "chilling",
                    "easy", "smooth", "free", "weekend", "shanti", "cool", "satisfied", "fine",
                    "aaram", "peaceful"
                },
                "score": 0.5,
                "tone": "smooth, casual, pleasant, easy-going, and playfully companionable",
            },
        }

    def detect_mood(self, text: str) -> Tuple[str, float]:
        """
        Analyze text sentiment using bilingual keyword scoring.
        Returns (detected_mood, sentiment_score).
        """
        if not text:
            return "neutral", 0.0

        clean = text.lower()
        words = set(re.findall(r"\b\w+\b", clean))

        best_mood = "neutral"
        best_count = 0
        sentiment_score = 0.0

        for mood, data in self._mood_lexicon.items():
            matches = words & data["keywords"]
            # Also check for multi-word phrases
            for kw in data["keywords"]:
                if " " in kw and kw in clean:
                    matches.add(kw)

            if len(matches) > best_count:
                best_count = len(matches)
                best_mood = mood
                sentiment_score = data["score"]

        # Boost intensity based on punctuation
        if "!" in text and sentiment_score > 0:
            sentiment_score = min(1.0, sentiment_score + 0.15)
        if ("?!" in text or "!?" in text) and sentiment_score < 0:
            sentiment_score = max(-1.0, sentiment_score - 0.15)

        return best_mood, sentiment_score

    def get_time_of_day_context(self) -> Tuple[str, str]:
        """
        Determine time-of-day vibe.
        Returns (period_name, behavioral_vibe).
        """
        hour = datetime.now().hour
        if 5 <= hour < 12:
            return "morning", "energetic, proactive, uplifting, sharp and ready for the day"
        elif 12 <= hour < 17:
            return "afternoon", "focused, crisp, efficient, keeping momentum productive"
        elif 17 <= hour < 22:
            return "evening", "warm, friendly, conversational, unwinding after work"
        else:
            return "late_night", "calm, gentle, soothing, soft-spoken, relaxed pacing"

    def get_prompt_injection(self, user_input: str) -> str:
        """
        Generate dynamic prompt injection incorporating user mood and time-of-day vibe.
        """
        mood, score = self.detect_mood(user_input)
        period, vibe = self.get_time_of_day_context()

        tone = self._mood_lexicon.get(mood, {}).get("tone", "standard charming, witty, respectful Friday/JARVIS style")

        injection = (
            f"\n[CURRENT_MOOD & CONTEXT ADAPTATION]: "
            f"Detected User Mood: {mood.upper()} (Sentiment: {score:+.2f}). "
            f"Tone Instruction: {tone}. "
            f"Time of Day Vibe ({period}): {vibe}. "
            f"Seamlessly adapt your pacing, warmth, and phrasing accordingly while always maintaining respectful address as Sir/Boss."
        )
        return injection

    def record_mood(self, user_input: str) -> Tuple[str, float]:
        """Detect and log mood to SQLite."""
        mood, score = self.detect_mood(user_input)
        snippet = user_input[:120].strip()
        try:
            self.memory.log_mood(mood, score, snippet)
        except Exception:
            pass
        return mood, score

    def get_mood_summary(self, days: int = 7) -> str:
        """
        Generate a human-readable summary of user mood history over the given period.
        """
        logs = self.memory.get_mood_history(days=days)
        if not logs:
            return f"Past {days} days mein mere paas aapke mood logs save nahi hain, Sir."

        total = len(logs)
        counts: Dict[str, int] = {}
        total_score = 0.0

        for entry in logs:
            m = entry.get("detected_mood", "neutral")
            counts[m] = counts.get(m, 0) + 1
            total_score += float(entry.get("sentiment_score", 0.0))

        avg_score = total_score / total if total > 0 else 0.0

        positive_count = counts.get("happy", 0) + counts.get("relaxed", 0)
        negative_count = counts.get("frustrated", 0) + counts.get("stressed", 0) + counts.get("sad", 0) + counts.get("tired", 0)
        neutral_count = counts.get("neutral", 0)

        pos_pct = int((positive_count / total) * 100)
        neg_pct = int((negative_count / total) * 100)
        neu_pct = int((neutral_count / total) * 100)

        dominant_mood = max(counts.items(), key=lambda x: x[1])[0]

        summary_parts = [
            f"Over the last {days} days across {total} recorded interactions, your mood was mostly {dominant_mood.upper()}.",
            f"Breakdown: {pos_pct}% Positive (Happy/Relaxed), {neg_pct}% Strained (Stressed/Frustrated/Tired), {neu_pct}% Neutral.",
        ]

        if avg_score >= 0.2:
            summary_parts.append("Overall sentiment is very positive and upbeat! Keep this great energy going, Sir.")
        elif avg_score <= -0.2:
            summary_parts.append("It looks like it was a challenging or tiring period. Remember to take breaks and rest well, Sir.")
        else:
            summary_parts.append("Overall steady and balanced, Sir.")

        return " ".join(summary_parts)
