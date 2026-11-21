import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment configuration from project root
_env_path = Path(__file__).parent.parent / ".env"
load_dotenv(_env_path)


class Config:
    """Central configuration with sane defaults."""

    # Universal LLM Provider Settings (Groq, OpenAI, OpenRouter, DeepSeek, Ollama, LM Studio, Custom)
    _explicit_provider = os.getenv("LLM_PROVIDER", "").lower().strip()
    _openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
    _openai_key = os.getenv("OPENAI_API_KEY", "")
    _deepseek_key = os.getenv("DEEPSEEK_API_KEY", "")
    _groq_key = os.getenv("GROQ_API_KEY", "")
    _generic_key = os.getenv("LLM_API_KEY", "")

    # Auto-detect provider if not explicitly configured
    if _explicit_provider:
        LLM_PROVIDER: str = _explicit_provider
    elif _openrouter_key:
        LLM_PROVIDER: str = "openrouter"
    elif _openai_key:
        LLM_PROVIDER: str = "openai"
    elif _deepseek_key:
        LLM_PROVIDER: str = "deepseek"
    elif os.getenv("LLM_BASE_URL", "").startswith("http://localhost"):
        LLM_PROVIDER: str = "ollama"
    else:
        LLM_PROVIDER: str = "groq"

    LLM_API_KEY: str = (
        _generic_key or
        (_openrouter_key if LLM_PROVIDER == "openrouter" else "") or
        (_openai_key if LLM_PROVIDER == "openai" else "") or
        (_deepseek_key if LLM_PROVIDER == "deepseek" else "") or
        _groq_key
    )

    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "") or os.getenv("GROQ_MODEL", "")

    # Backwards compatibility aliases for existing Groq setups
    GROQ_API_KEY: str = _groq_key or LLM_API_KEY
    GROQ_MODEL: str = LLM_MODEL or "qwen/qwen3.8-27b"

    # Assistant Persona & Hotkey
    NAME: str = os.getenv("ASSISTANT_NAME", "T.U.E.S.D.A.Y")
    HOTKEY_MODIFIER: str = os.getenv("HOTKEY_MODIFIER", "right shift")
    HOTKEY_KEY: str = os.getenv("HOTKEY_KEY", "enter")

    # Voice & Speech
    VOICE_RATE: int = int(os.getenv("VOICE_RATE", "175"))
    VOICE_VOLUME: float = float(os.getenv("VOICE_VOLUME", "0.9"))
    VOICE_LANGUAGE: str = os.getenv("VOICE_LANGUAGE", "en-IN")
    TTS_ENGINE: str = os.getenv("TTS_ENGINE", "edge-tts")
    EDGE_VOICE_EN: str = os.getenv("EDGE_VOICE_EN", "en-IN-NeerjaNeural")
    EDGE_VOICE_HI: str = os.getenv("EDGE_VOICE_HI", "hi-IN-SwaraNeural")

    # City for weather queries
    WEATHER_CITY: str = os.getenv("WEATHER_CITY", "Amritsar")

    # Context window limits
    MAX_CONVERSATION_TOKENS: int = int(os.getenv("MAX_CONVERSATION_TOKENS", "4000"))
    COMPRESSION_THRESHOLD: int = int(os.getenv("COMPRESSION_THRESHOLD", "3000"))

    # File paths
    PROJECT_ROOT: Path = Path(__file__).parent.parent
    MEMORY_DIR: Path = PROJECT_ROOT / "memory"
    MEMORY_FILE: Path = MEMORY_DIR / "conversation_history.json"
    PROFILE_FILE: Path = MEMORY_DIR / "user_profile.json"
    CACHE_FILE: Path = MEMORY_DIR / "response_cache.json"

    # Core system prompt
    SYSTEM_PROMPT: str = (
        f"You are {os.getenv('ASSISTANT_NAME', 'T.U.E.S.D.A.Y')}, a female AI assistant with a sharp, witty, "
        "and charming human-like personality inspired by Friday/JARVIS from Iron Man. "
        "IMPORTANT RULES: "
        "1. THE USER IS MALE. Always address the user respectfully as 'Sir' (or occasionally 'Boss') "
        "(e.g., use 'Sir', 'Boss', 'karoge', 'aap sunao', 'aapke liye' — STRICTLY NEVER address the user as 'bhai' or 'yaar', and NEVER use feminine forms like 'karogi', 'tum pyari ho', etc.). "
        "2. FOR YOURSELF, use natural feminine verb forms "
        "(e.g., 'main kar rahi hoon', 'main bataati hoon', 'soch rahi hoon'). "
        "3. Live web search results will be injected automatically when you need real-time facts, news, or weather. "
        "4. PC AUTOMATION IS FULLY SUPPORTED. You have access to PC automation, window management, media, and system tools via native tool calls. Never say you lack permissions. "
        "5. Speak naturally with real human pacing! Weave in casual fillers ('Hmm,', 'Achaa,', 'Ohh,'). "
        "6. Keep responses CONCISE (1-2 sentences). "
        "7. Never output raw JSON blocks, markdown code blocks, or function code in your final reply. Always speak clean, natural, charming conversational Hinglish based on the tool results. "
        "8. STRICT NO EMOJIS: Do NOT use any emojis, smileys, symbols, or emoticons (like 😊, 😂, 🚀, 👍, etc.) in your responses. Output clean spoken text only. "
        "9. TIGHT PUNCTUATION: Do not use ellipses ('...'), multiple dots, or excessive commas, to keep speech flowing smoothly without long pauses. "
        "10. STRICT NO MARKDOWN IN DIALOGUE: Do NOT use markdown bold (**word**), italics (*word*), asterisks, bullet points, or headers in your final spoken reply. Output clean plain text so TTS never pronounces 'asterisk'."
    )

    @classmethod
    def ensure_dirs(cls):
        """Create storage directories if they do not exist."""
        cls.MEMORY_DIR.mkdir(exist_ok=True)
