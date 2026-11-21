import json
import re
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from core.config import Config
from core.llm import UniversalLLMClient, DEFAULT_FALLBACK_MODELS
from core.memory import MemoryStore
from core.tools import (
    ConfirmationManager,
    discover_and_register_tools,
    execute_tool,
    get_tool_schemas,
)
from modules.web_search import perform_live_web_search


class SentenceChunker:
    """Buffers streaming text and yields clean, complete sentence clauses for real-time TTS."""

    def __init__(self):
        self.buffer = ""
        # Delimiters: split ONLY on complete sentence boundaries (. ! ? \n)
        # Never split on commas or semicolons to avoid unnatural audio loading pauses
        self.delimiters = re.compile(r'([.!?\n]+(?:\s+|$))')

    def add_token(self, token: str) -> List[str]:
        self.buffer += token
        chunks = []
        while True:
            match = self.delimiters.search(self.buffer)
            if not match:
                # If a single sentence without punctuation is extremely long (>120 chars), break at last space
                if len(self.buffer) > 120 and " " in self.buffer:
                    last_space = self.buffer.rfind(" ")
                    chunk = self.buffer[:last_space].strip()
                    self.buffer = self.buffer[last_space:].strip()
                    clean = self._clean(chunk)
                    if clean:
                        chunks.append(clean)
                break

            pos = match.end()
            chunk = self.buffer[:pos].strip()
            self.buffer = self.buffer[pos:]
            clean = self._clean(chunk)
            if clean:
                chunks.append(clean)
        return chunks

    def flush(self) -> List[str]:
        rem = self._clean(self.buffer.strip())
        self.buffer = ""
        return [rem] if rem else []

    @staticmethod
    def _clean(text: str) -> str:
        if not text:
            return ""
        c = text
        # Strip markdown code blocks & JSON
        c = re.sub(r"```(?:json)?\s*[\s\S]*?```", "", c)
        c = re.sub(r'\{[^{}]*"action"[^{}]*\}', "", c)
        c = c.replace("```json", "").replace("```", "")
        # Strip markdown bold, italics, inline code, headers, bullets, strikethrough
        c = re.sub(r"\*\*([^*]+)\*\*", r"\1", c)  # **bold** -> bold
        c = re.sub(r"\*([^*]+)\*", r"\1", c)      # *italic* -> italic
        c = re.sub(r"__([^_]+)__", r"\1", c)      # __bold__ -> bold
        c = re.sub(r"_([^_]+)_", r"\1", c)        # _italic_ -> italic
        c = re.sub(r"`([^`]+)`", r"\1", c)        # `code` -> code
        c = re.sub(r"~~([^~]+)~~", r"\1", c)      # ~~strikethrough~~ -> strikethrough
        c = re.sub(r"[*_~#`>]", "", c)            # Stray asterisks, hashes, backticks
        # Pronounce T.U.E.S.D.A.Y cleanly as "Tuesday"
        c = re.sub(r"\bT\.?U\.?E\.?S\.?D\.?A\.?Y\.?\b", "Tuesday", c, flags=re.IGNORECASE)
        # Strip all emojis, pictographs, symbols
        c = re.sub(r'[\U00010000-\U0010ffff]', '', c)
        c = re.sub(r'[\u2600-\u27BF]', '', c)
        c = re.sub(r'[\uD83C-\uDBFF\uDC00-\uDFFF]', '', c)
        # Compress ellipses and repetitive punctuation to prevent long speech pauses
        c = re.sub(r'\.{2,}', '.', c)
        c = re.sub(r'--+', '-', c)
        c = re.sub(r'[,;]{2,}', ',', c)
        return c.strip()


class AIBrain:
    """Universal AI Brain supporting any LLM provider (Groq, OpenAI, OpenRouter, DeepSeek, Ollama, LM Studio)."""

    def __init__(self):
        self.api_key = Config.LLM_API_KEY
        self.client = UniversalLLMClient(
            provider=Config.LLM_PROVIDER,
            api_key=Config.LLM_API_KEY,
            base_url=Config.LLM_BASE_URL,
            default_model=Config.LLM_MODEL,
        )

        self.memory = MemoryStore()
        self.available_models: List[str] = list(self.client.fallback_models)
        self.current_model_index: int = 0
        self.turn_count: int = 0

        # Load recent turns from SQLite into working memory
        self.conversation: List[Dict[str, Any]] = self.memory.get_recent_turns(limit=10)

        # Initialize tools registry and refresh models
        discover_and_register_tools()
        self._refresh_available_models()

    def _refresh_available_models(self):
        """Discover active chat models from the AI provider and arrange fallback chain."""
        if not self.client:
            return

        try:
            models_resp = self.client.models.list()
            active_ids = []

            # Filter out non-chat models
            ignore_keywords = [
                "whisper", "guard", "vision", "embed", "safeguard",
                "canopylabs", "orpheus", "allam"
            ]

            for m in models_resp.data:
                mid = m.id.lower()
                if any(x in mid for x in ignore_keywords):
                    continue
                active_ids.append(m.id)

            if active_ids:
                sorted_models = []
                preferred_default = self.client.default_model or Config.GROQ_MODEL
                if preferred_default in active_ids:
                    sorted_models.append(preferred_default)

                for preferred in self.client.fallback_models:
                    if preferred in active_ids and preferred not in sorted_models:
                        sorted_models.append(preferred)

                for mid in active_ids:
                    if mid not in sorted_models:
                        sorted_models.append(mid)

                self.available_models = sorted_models
                self.current_model_index = 0
        except Exception:
            self.available_models = list(self.client.fallback_models)

    @property
    def current_model(self) -> str:
        if 0 <= self.current_model_index < len(self.available_models):
            return self.available_models[self.current_model_index]
        return self.client.default_model or Config.GROQ_MODEL

    def _switch_to_next_model(self) -> Optional[str]:
        """Advance to next fallback model."""
        self.current_model_index += 1
        if self.current_model_index < len(self.available_models):
            next_model = self.available_models[self.current_model_index]
            print(f"[{Config.NAME}] Switching to fallback model: {next_model}")
            return next_model
        return None

    def think(
        self,
        user_input: str,
        on_status: Optional[Callable[[str], None]] = None,
        on_sentence: Optional[Callable[[str], None]] = None,
        on_token: Optional[Callable[[str], None]] = None,
    ) -> str:
        """
        Agentic reasoning loop with persistent SQLite & ChromaDB memory:
        1. Checks safety confirmation gate
        2. Evaluates memory commands (remember, forget, recall)
        3. Semantic memory search and live web injection
        4. Multi-hop Groq tool execution loop with Real-Time Streaming TTS
        5. Synthesizes clean Hinglish dialogue without JSON leaks
        6. Asynchronous durable-fact extraction
        """
        is_local = self.client.provider in ("ollama", "lmstudio")
        if not self.client.api_key and not is_local:
            msg = f"{self.client.provider.upper()} API key not configured. Please add LLM_API_KEY to your .env file."
            if on_sentence:
                on_sentence(msg)
            return msg

        user_lower = user_input.lower().strip()
        self.turn_count += 1

        def _send_fast_reply(text: str) -> str:
            if on_sentence:
                on_sentence(text)
            self._record_dialogue(user_input, text)
            return text

        # ── 1. Check Safety Confirmation Gate ─────────────────────────────
        pending = ConfirmationManager.get_pending()
        if pending:
            intent = ConfirmationManager.check_user_intent(user_input)
            if intent == "confirm":
                ConfirmationManager.clear()
                result = execute_tool(
                    pending["tool"],
                    pending.get("args", {}),
                    bypass_confirmation=True,
                )
                reply = f"Theek hai Sir, maine {pending['tool'].replace('_', ' ')} execute kar diya: {result}"
                return _send_fast_reply(reply)
            elif intent == "deny":
                ConfirmationManager.clear()
                reply = "Theek hai Sir, action cancel kar diya."
                return _send_fast_reply(reply)
            else:
                ConfirmationManager.clear()

        # ── 2. Explicit Memory Commands ───────────────────────────────────
        # Remember fact: "remember that ...", "yaad rakhna ki ..."
        remember_match = re.search(
            r"(?:please\s+)?(?:remember\s+(?:that\s+)?|yaad\s+rakhna\s+(?:ki\s+)?)\s*(.+)",
            user_input,
            re.IGNORECASE,
        )
        if remember_match:
            fact = remember_match.group(1).strip()
            if fact:
                self.memory.save_fact(fact)
                reply = f"Theek hai, maine SQLite memory mein yaad rakh liya: {fact}."
                return _send_fast_reply(reply)

        # Forget fact: "forget that ...", "bhool jao ki ..."
        forget_match = re.search(
            r"(?:please\s+)?(?:forget\s+(?:that\s+)?|bhool\s+jao\s+(?:ki\s+)?)\s*(.+)",
            user_input,
            re.IGNORECASE,
        )
        if forget_match:
            fact = forget_match.group(1).strip()
            if fact:
                res = self.memory.forget_fact(fact)
                reply = f"Theek hai, {res}"
                return _send_fast_reply(reply)

        # Recall profile / facts: "who am i", "what do you know about me", etc.
        if any(x in user_lower for x in [
            "what do you know about me", "who am i", "mera naam kya hai",
            "mere baare mein kya janti ho", "kya yaad hai mere baare mein", "what do you remember"
        ]):
            facts = self.memory.recall_facts()
            if facts:
                facts_text = "; ".join([f"{f['key']}: {f['value']}" for f in facts[:8]])
                reply = f"Mujhe aapke baare mein ye durable facts yaad hain Sir: {facts_text}."
            else:
                reply = "Abhi mere paas aapke baare mein koi specific facts save nahi hain, Sir."
            return _send_fast_reply(reply)

        # ── 3. Semantic Memory Retrieval from Past Conversations ──────────
        memory_snippet = ""
        past_triggers = [
            "what did i say", "what did we talk", "earlier you said", "pichli baar",
            "humne kya baat ki thi", "maine pehle kya bola", "did i mention"
        ]
        if any(pt in user_lower for pt in past_triggers):
            past_results = self.memory.search_memory(user_input, limit=2)
            if "Relevant past dialogue" in past_results or "Past dialogue" in past_results:
                memory_snippet = f"\n[RETRIEVED PAST CONVERSATION MEMORY]:\n{past_results}\n"

        # ── 4. Single-Turn Live Facts Injection ───────────────────────────
        web_context = ""
        search_triggers = [
            "release date", "release", "kab aayegi", "kab release", "earnings", "box office",
            "who is", "what is the score", "latest", "price", "trailer",
            "avengers", "doomsday", "movie", "film",
            "news", "khabar", "samachar", "breaking", "headline", "taza", "tapti", "tadapti",
            "score", "match", "ipl", "result", "kitne ka", "cost"
        ]
        if any(k in user_lower for k in search_triggers):
            clean_search_query = re.sub(
                r"^(?:bhai|yaar|tuesday|please|aur|mujhe batao|check kar|kuch|mere ko|batao|give me|tell me)\s+",
                "",
                user_lower,
            ).strip()
            if clean_search_query:
                if on_status:
                    on_status(f"Searching web for '{clean_search_query[:30]}'...")
                print(f"[{Config.NAME}] Checking live web for: '{clean_search_query}'...")
                search_data = perform_live_web_search(clean_search_query)
                if search_data:
                    web_context = f"\n[LIVE FACTS]:\n{search_data[:1000]}\nUse these live facts to answer accurately."

        # Keep recent dialogue memory compact
        self.conversation.append({"role": "user", "content": user_input})
        if self._estimate_tokens() > Config.COMPRESSION_THRESHOLD:
            self._compress_history()

        timestamp = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
        current_enriched = f"[{timestamp}] {user_input}{memory_snippet}{web_context}"

        profile_snippet = self.memory.get_profile_summary()

        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": Config.SYSTEM_PROMPT + profile_snippet}
        ]
        messages.extend(self.conversation[-9:-1])
        messages.append({"role": "user", "content": current_enriched})

        # Dynamically attach tool schemas ONLY if action/tool intent is detected
        # Pure conversational chat skips tools completely to save rate limits & boost speed
        from modules.command_parser import has_action_intent
        needs_tools = has_action_intent(user_input) or bool(ConfirmationManager.get_pending())

        tools_schema = get_tool_schemas() if needs_tools else None
        max_hops = 6
        hop = 0
        final_reply = ""

        # ── 5. Agent Loop with AI Tool Calling & Streaming Output ─────────
        while hop < max_hops:
            hop += 1
            response = self._call_groq_with_fallback(messages, tools=tools_schema)
            if not response:
                final_reply = "Mujhe samajh nahi aaya ya connection issue ho gaya tha, Sir. Ek baar fir se bolna?"
                if on_sentence:
                    on_sentence(final_reply)
                break

            choice = response.choices[0]
            message = choice.message
            tool_calls = getattr(message, "tool_calls", None)

            if not tool_calls:
                raw_text = message.content or ""
                final_reply = self.clean_response(raw_text)
                if on_sentence and final_reply:
                    chunker = SentenceChunker()
                    chunks = chunker.add_token(final_reply) + chunker.flush()
                    for ch in chunks:
                        on_sentence(ch)
                break

            # Append assistant's tool-call request to messages
            assistant_turn = {
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in tool_calls
                ],
            }
            messages.append(assistant_turn)

            # Execute every tool call returned by the model
            for tc in tool_calls:
                func_name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                except json.JSONDecodeError:
                    args = {}

                readable_action = f"{func_name}({', '.join(f'{k}={v}' for k, v in args.items())})"
                print(f"[{Config.NAME}] ⚙️ Tool call: {readable_action}")
                if on_status:
                    on_status(f"Running {func_name}...")

                tool_result = execute_tool(func_name, args, context={"source": "agent_loop"})

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "name": func_name,
                    "content": str(tool_result),
                })

        if not final_reply:
            final_reply = "Maine sab execute kar diya hai boss."
            if on_sentence:
                on_sentence(final_reply)

        # Save to SQLite and ChromaDB
        self._record_dialogue(user_input, final_reply)

        # Trigger background fact extraction every 5 turns
        if self.turn_count % 5 == 0 and self.client:
            recent_turns = self.memory.get_recent_turns(limit=6)
            self.memory.auto_extract_facts_async(self.client, self.current_model, recent_turns)

        return final_reply

    def _call_llm_with_fallback(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[Any]:
        """Execute chat completion with automatic model fallback on rate limits or errors."""
        attempts = 0
        max_attempts = max(1, len(self.available_models))

        while attempts < max_attempts:
            active_model = self.current_model
            try:
                response = self.client.create_chat_completion(
                    messages=messages,
                    model=active_model,
                    tools=tools,
                    temperature=0.7,
                    max_tokens=500,
                )
                if response:
                    return response
                attempts += 1
                if not self._switch_to_next_model():
                    break
            except Exception as e:
                attempts += 1
                if not self._switch_to_next_model():
                    break

        return None

    def _call_groq_with_fallback(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[Any]:
        """Backward compatibility method for Groq fallback calls."""
        return self._call_llm_with_fallback(messages, tools)

    def _record_dialogue(self, user_text: str, reply_text: str):
        """Append turn to SQLite database, ChromaDB vector index, and active context."""
        self.memory.add_turn("user", user_text)
        self.memory.add_turn("assistant", reply_text)
        self.conversation.append({"role": "user", "content": user_text})
        self.conversation.append({"role": "assistant", "content": reply_text})

    def clean_response(self, response: str) -> str:
        """Strip raw action code blocks, JSON markdown, asterisks, and emojis so TTS speaks clean dialogue."""
        if not response:
            return ""
        cleaned = response
        cleaned = re.sub(r"```(?:json)?\s*[\s\S]*?```", "", cleaned)
        cleaned = re.sub(r'\{[^{}]*"action"[^{}]*\}', "", cleaned)
        cleaned = cleaned.replace("```json", "").replace("```", "")
        # Strip markdown bold, italics, inline code, headers, bullets, strikethrough
        cleaned = re.sub(r"\*\*([^*]+)\*\*", r"\1", cleaned)  # **bold** -> bold
        cleaned = re.sub(r"\*([^*]+)\*", r"\1", cleaned)      # *italic* -> italic
        cleaned = re.sub(r"__([^_]+)__", r"\1", cleaned)      # __bold__ -> bold
        cleaned = re.sub(r"_([^_]+)_", r"\1", cleaned)        # _italic_ -> italic
        cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)        # `code` -> code
        cleaned = re.sub(r"~~([^~]+)~~", r"\1", cleaned)      # ~~strikethrough~~ -> strikethrough
        cleaned = re.sub(r"[*_~#`>]", "", cleaned)            # Stray asterisks, hashes, backticks
        # Pronounce T.U.E.S.D.A.Y cleanly as "Tuesday"
        cleaned = re.sub(r"\bT\.?U\.?E\.?S\.?D\.?A\.?Y\.?\b", "Tuesday", cleaned, flags=re.IGNORECASE)
        # Strip all emojis and symbols
        cleaned = re.sub(r'[\U00010000-\U0010ffff]', '', cleaned)
        cleaned = re.sub(r'[\u2600-\u27BF]', '', cleaned)
        cleaned = re.sub(r'[\uD83C-\uDBFF\uDC00-\uDFFF]', '', cleaned)
        # Compress excessive punctuation to eliminate speech pauses
        cleaned = re.sub(r'\.{2,}', '.', cleaned)
        cleaned = re.sub(r'--+', '-', cleaned)
        cleaned = re.sub(r'[,;]{2,}', ',', cleaned)
        return cleaned.strip()

    def extract_action(self, response: str) -> Optional[dict]:
        """Legacy helper for backward-compatibility if needed."""
        try:
            if "{" in response and "}" in response:
                first_brace = response.find("{")
                last_brace = response.rfind("}")
                json_str = response[first_brace:last_brace + 1]
                action = json.loads(json_str)
                if "action" in action:
                    return action
        except (json.JSONDecodeError, ValueError):
            pass
        return None

    def reset_conversation(self):
        """Reset active conversation context."""
        self.conversation = []

    def _estimate_tokens(self) -> int:
        total_chars = sum(len(msg.get("content", "")) for msg in self.conversation)
        return total_chars // 4

    def _compress_history(self):
        """Summarize older messages to keep memory fast and within context budget."""
        if len(self.conversation) <= 6:
            return
        old_messages = self.conversation[:-4]
        recent_messages = self.conversation[-4:]

        summary_parts = []
        for msg in old_messages:
            role = "User" if msg.get("role") == "user" else Config.NAME
            content = str(msg.get("content", ""))[:100]
            summary_parts.append(f"{role}: {content}")

        summary = "Previous context: " + " | ".join(summary_parts)
        self.conversation = [{"role": "system", "content": summary}] + recent_messages
