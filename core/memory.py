"""
Unified Persistent Memory System for T.U.E.S.D.A.Y.
Features:
- Structured facts store in SQLite (memory/tuesday.db)
- Auto-migration from legacy memory/user_profile.json
- ChromaDB local semantic memory vector search over all dialogue turns
- Offline fallback to SQLite keyword search
- Automated background durable-facts extractor with strict privacy filters
"""

import json
import os
import re
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.config import Config

CHROMA_DIR = Config.MEMORY_DIR / "chroma_db"
SQLITE_DB_PATH = Config.MEMORY_DIR / "tuesday.db"


class MemoryStore:
    """Manages short-term context, SQLite long-term facts, and ChromaDB vector search."""

    _instance: Optional["MemoryStore"] = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(MemoryStore, cls).__new__(cls)
                cls._instance._init_store()
            return cls._instance

    def _init_store(self):
        Config.ensure_dirs()
        self.db_path = SQLITE_DB_PATH
        self._init_sqlite()
        self._migrate_legacy_profile()
        self._init_chroma()
        self._turn_counter = 0

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_sqlite(self):
        """Create tables for structured facts and conversational turns."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT DEFAULT 'general',
                    key TEXT UNIQUE,
                    value TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversation_turns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    due_timestamp REAL NOT NULL,
                    recurring TEXT DEFAULT 'none',
                    is_completed INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS todos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task TEXT NOT NULL,
                    is_completed INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS mood_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    detected_mood TEXT NOT NULL,
                    sentiment_score REAL DEFAULT 0.0,
                    user_snippet TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS habit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    hour_of_day INTEGER NOT NULL,
                    app_name TEXT NOT NULL,
                    day_key TEXT NOT NULL,
                    UNIQUE(hour_of_day, app_name, day_key)
                )
            """)
            conn.commit()

    def _migrate_legacy_profile(self):
        """Migrate existing user_profile.json data to SQLite if user_facts is empty."""
        try:
            with self._get_connection() as conn:
                count = conn.execute("SELECT COUNT(*) FROM user_facts").fetchone()[0]
                if count > 0:
                    return

                profile_path = Config.PROFILE_FILE
                if profile_path.exists():
                    with open(profile_path, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    city = data.get("city")
                    if city:
                        conn.execute(
                            "INSERT OR REPLACE INTO user_facts (category, key, value) VALUES (?, ?, ?)",
                            ("personal", "location", f"User lives in {city}")
                        )

                    name = data.get("name")
                    if name:
                        conn.execute(
                            "INSERT OR REPLACE INTO user_facts (category, key, value) VALUES (?, ?, ?)",
                            ("personal", "name", name)
                        )

                    notes = data.get("notes", [])
                    for idx, note in enumerate(notes):
                        clean_key = f"note_{idx+1}"
                        conn.execute(
                            "INSERT OR REPLACE INTO user_facts (category, key, value) VALUES (?, ?, ?)",
                            ("general", clean_key, note)
                        )
                    conn.commit()
                    print(f"[{Config.NAME}] Migrated legacy user_profile.json to SQLite database.")
        except Exception as e:
            print(f"[{Config.NAME}] Migration warning: {e}")

    def _init_chroma(self):
        """Initialize ChromaDB with local offline embeddings."""
        self.chroma_client = None
        self.collection = None
        try:
            import chromadb
            self.chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
            self.collection = self.chroma_client.get_or_create_collection(
                name="tuesday_conversation_memory",
                metadata={"description": "Semantic memory across past dialogues"}
            )
        except Exception as e:
            print(f"[{Config.NAME}] ChromaDB semantic memory offline, falling back to SQLite search: {e}")

    # ── Structured Facts API ──────────────────────────────────────────────

    def save_fact(self, fact: str, key: Optional[str] = None, category: str = "general") -> str:
        """Store or update a durable user fact in SQLite."""
        fact = fact.strip()
        if not fact:
            return "Cannot save an empty fact."

        if not key:
            # Generate key from first few words
            slug = re.sub(r"[^\w\s]", "", fact.lower())
            tokens = slug.split()[:4]
            key = "_".join(tokens) or f"fact_{int(datetime.now().timestamp())}"

        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO user_facts (category, key, value, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    category = excluded.category,
                    updated_at = excluded.updated_at
            """, (category.lower(), key.lower(), fact, now, now))
            conn.commit()

        return f"Fact remembered: {fact} (key: '{key}')"

    def recall_facts(self, category: Optional[str] = None, query: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve stored facts filtered by optional category or substring search."""
        sql = "SELECT category, key, value, updated_at FROM user_facts WHERE 1=1"
        params = []

        if category:
            sql += " AND category = ?"
            params.append(category.lower())
        if query:
            sql += " AND (value LIKE ? OR key LIKE ?)"
            params.extend([f"%{query}%", f"%{query}%"])

        sql += " ORDER BY updated_at DESC"

        with self._get_connection() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]

    def forget_fact(self, key_or_fact: str) -> str:
        """Remove a fact by key or value substring."""
        target = key_or_fact.strip().lower()
        with self._get_connection() as conn:
            cur = conn.execute(
                "DELETE FROM user_facts WHERE key = ? OR value LIKE ?",
                (target, f"%{target}%")
            )
            conn.commit()
            if cur.rowcount > 0:
                return f"Forgot {cur.rowcount} fact(s) matching '{key_or_fact}'."
        return f"No fact found matching '{key_or_fact}' to forget."

    def update_fact(self, key: str, new_value: str) -> str:
        """Update an existing fact key."""
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            cur = conn.execute(
                "UPDATE user_facts SET value = ?, updated_at = ? WHERE key = ?",
                (new_value.strip(), now, key.strip().lower())
            )
            conn.commit()
            if cur.rowcount > 0:
                return f"Updated '{key}' to: {new_value}"
        # If not found, insert fresh
        return self.save_fact(new_value, key=key)

    def get_profile_summary(self) -> str:
        """Generate a concise profile summary for system prompt injection."""
        facts = self.recall_facts()
        if not facts:
            return ""
        items = [f"{f['key']}: {f['value']}" for f in facts[:10]]
        return f"\n[PERSISTENT USER PROFILE]: {'; '.join(items)}."

    # ── Dialogue History & Semantic Indexing ──────────────────────────────

    def add_turn(self, role: str, content: str, session_id: str = "default") -> int:
        """Append dialogue turn to SQLite and vector index."""
        now = datetime.now().isoformat()
        turn_id = 0
        with self._get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO conversation_turns (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                (session_id, role, content, now)
            )
            conn.commit()
            turn_id = cur.lastrowid

        # Index in ChromaDB if available
        if self.collection and len(content.strip()) > 3:
            try:
                doc_id = f"turn_{turn_id}"
                self.collection.add(
                    documents=[content],
                    metadatas=[{"role": role, "timestamp": now, "turn_id": turn_id}],
                    ids=[doc_id]
                )
            except Exception:
                pass

        self._turn_counter += 1
        return turn_id

    def get_recent_turns(self, limit: int = 10) -> List[Dict[str, str]]:
        """Fetch last N turns from SQLite database."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT role, content FROM conversation_turns ORDER BY id DESC LIMIT ?",
                (limit,)
            ).fetchall()
            turns = [dict(r) for r in rows]
            turns.reverse()
            return turns

    def search_memory(self, query: str, limit: int = 3) -> str:
        """
        Semantic similarity search across historical dialogue turns.
        Falls back to SQLite LIKE search if vector DB is unavailable.
        """
        query = query.strip()
        if not query:
            return "No search query provided."

        # 1. Semantic search with ChromaDB
        if self.collection:
            try:
                results = self.collection.query(query_texts=[query], n_results=limit)
                docs = results.get("documents", [[]])[0]
                metas = results.get("metadatas", [[]])[0]
                if docs:
                    snippets = []
                    for doc, meta in zip(docs, metas):
                        role = meta.get("role", "speaker")
                        time_str = meta.get("timestamp", "")[:16].replace("T", " ")
                        snippets.append(f"[{time_str}] {role.title()}: {doc}")
                    return "Relevant past dialogue:\n" + "\n".join(snippets)
            except Exception as e:
                print(f"[Memory] Semantic query fallback: {e}")

        # 2. Offline fallback: SQLite keyword match
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT role, content, timestamp FROM conversation_turns WHERE content LIKE ? ORDER BY id DESC LIMIT ?",
                (f"%{query}%", limit)
            ).fetchall()
            if rows:
                snippets = [f"[{r['timestamp'][:16].replace('T', ' ')}] {r['role'].title()}: {r['content']}" for r in rows]
                return "Past dialogue (keyword match):\n" + "\n".join(snippets)

        return f"No past conversations found matching '{query}'."

    # ── Automatic Background Fact Extraction ──────────────────────────────

    def auto_extract_facts_async(self, groq_client, model: str, recent_turns: List[Dict[str, str]]):
        """Asynchronously analyze dialogue turns to extract and store durable facts."""
        thread = threading.Thread(
            target=self._run_fact_extraction,
            args=(groq_client, model, recent_turns),
            daemon=True
        )
        thread.start()

    def _run_fact_extraction(self, groq_client, model: str, recent_turns: List[Dict[str, str]]):
        if not groq_client or len(recent_turns) < 2:
            return

        dialogue_text = "\n".join([f"{t['role'].title()}: {t['content']}" for t in recent_turns])

        prompt = (
            "Analyze the following conversation and extract durable user facts (e.g. personal preferences, "
            "name, job, pets, projects, important dates, schedules, location). "
            "STRICT PRIVACY RULES: "
            "1. NEVER extract passwords, API keys, credit cards, bank details, OTPs, PINs, or ID numbers. "
            "2. Skip transient queries (weather, news, calculations, PC commands). "
            "Output ONLY a valid JSON array of objects with keys: 'category', 'key', 'value'. "
            "If no new facts, return [].\n\n"
            f"Conversation:\n{dialogue_text}\n\nJSON Output:"
        )

        try:
            res = groq_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a precise data extraction engine. Output JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=300,
            )
            raw = (res.choices[0].message.content or "").strip()
            # Clean markdown code blocks if present
            if "```" in raw:
                raw = re.sub(r"```(?:json)?\s*([\s\S]*?)\s*```", r"\1", raw).strip()

            if raw.startswith("[") and raw.endswith("]"):
                facts = json.loads(raw)
                for item in facts:
                    cat = item.get("category", "general")
                    key = item.get("key", "")
                    val = item.get("value", "")
                    if val and key:
                        self.save_fact(val, key=key, category=cat)
        except Exception:
            pass

    # ── Reminders & Alarms ──────────────────────────────────────────────────

    def add_reminder(self, title: str, due_timestamp: float, recurring: str = "none") -> int:
        """Store a persistent reminder in SQLite."""
        with self._get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO reminders (title, due_timestamp, recurring, is_completed) VALUES (?, ?, ?, 0)",
                (title.strip(), float(due_timestamp), recurring.lower().strip())
            )
            conn.commit()
            return cur.lastrowid

    def get_due_reminders(self, now_ts: Optional[float] = None) -> List[Dict[str, Any]]:
        """Fetch all reminders whose due_timestamp <= now and are not completed."""
        ts = now_ts or time.time()
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT id, title, due_timestamp, recurring FROM reminders WHERE is_completed = 0 AND due_timestamp <= ?",
                (ts,)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_all_reminders(self, include_completed: bool = False) -> List[Dict[str, Any]]:
        """Retrieve upcoming (and optionally completed) reminders."""
        query = "SELECT id, title, due_timestamp, recurring, is_completed FROM reminders"
        if not include_completed:
            query += " WHERE is_completed = 0"
        query += " ORDER BY due_timestamp ASC"
        with self._get_connection() as conn:
            rows = conn.execute(query).fetchall()
            return [dict(r) for r in rows]

    def complete_reminder(self, reminder_id: int) -> bool:
        """Mark reminder as completed, or reschedule if recurring."""
        with self._get_connection() as conn:
            row = conn.execute("SELECT recurring, due_timestamp FROM reminders WHERE id = ?", (reminder_id,)).fetchone()
            if not row:
                return False
            rec = row["recurring"]
            if rec == "daily":
                next_ts = row["due_timestamp"] + 86400
                conn.execute("UPDATE reminders SET due_timestamp = ? WHERE id = ?", (next_ts, reminder_id))
            elif rec == "weekly":
                next_ts = row["due_timestamp"] + 86400 * 7
                conn.execute("UPDATE reminders SET due_timestamp = ? WHERE id = ?", (next_ts, reminder_id))
            else:
                conn.execute("UPDATE reminders SET is_completed = 1 WHERE id = ?", (reminder_id,))
            conn.commit()
            return True

    def delete_reminder(self, reminder_id: int) -> bool:
        """Permanently remove a reminder."""
        with self._get_connection() as conn:
            cur = conn.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
            conn.commit()
            return cur.rowcount > 0

    # ── To-Do List Management ───────────────────────────────────────────────

    def add_todo(self, task: str) -> int:
        """Add a to-do item to SQLite."""
        with self._get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO todos (task, is_completed) VALUES (?, 0)",
                (task.strip(),)
            )
            conn.commit()
            return cur.lastrowid

    def get_todos(self, status: str = "pending") -> List[Dict[str, Any]]:
        """Fetch todos by status ('pending', 'completed', or 'all')."""
        query = "SELECT id, task, is_completed, created_at, completed_at FROM todos"
        if status == "pending":
            query += " WHERE is_completed = 0"
        elif status == "completed":
            query += " WHERE is_completed = 1"
        query += " ORDER BY id DESC"
        with self._get_connection() as conn:
            rows = conn.execute(query).fetchall()
            return [dict(r) for r in rows]

    def complete_todo(self, identifier: str) -> Optional[str]:
        """Mark a todo as completed by ID or keyword."""
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            if identifier.isdigit():
                cur = conn.execute(
                    "UPDATE todos SET is_completed = 1, completed_at = ? WHERE id = ?",
                    (now, int(identifier))
                )
                conn.commit()
                if cur.rowcount > 0:
                    return f"Task marked as completed."
            else:
                row = conn.execute(
                    "SELECT id FROM todos WHERE is_completed = 0 AND task LIKE ? LIMIT 1",
                    (f"%{identifier}%",)
                ).fetchone()
                if row:
                    conn.execute(
                        "UPDATE todos SET is_completed = 1, completed_at = ? WHERE id = ?",
                        (now, row["id"])
                    )
                    conn.commit()
                    return f"Task marked as completed."
        return None

    def delete_todo(self, identifier: str) -> bool:
        """Delete a todo by ID or keyword."""
        with self._get_connection() as conn:
            if identifier.isdigit():
                cur = conn.execute("DELETE FROM todos WHERE id = ?", (int(identifier),))
            else:
                cur = conn.execute("DELETE FROM todos WHERE task LIKE ?", (f"%{identifier}%",))
            conn.commit()
            return cur.rowcount > 0

    # ── Notes Management ────────────────────────────────────────────────────

    def add_note(self, title: str, content: str) -> int:
        """Create or update a note in SQLite."""
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO notes (title, content, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (title.strip(), content.strip(), now, now)
            )
            conn.commit()
            return cur.lastrowid

    def get_notes(self, query: Optional[str] = None) -> List[Dict[str, Any]]:
        """List notes, optionally filtered by keyword."""
        sql = "SELECT id, title, content, created_at, updated_at FROM notes"
        params: List[Any] = []
        if query:
            sql += " WHERE title LIKE ? OR content LIKE ?"
            params = [f"%{query}%", f"%{query}%"]
        sql += " ORDER BY updated_at DESC"
        with self._get_connection() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]

    def read_note(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Fetch a single note by ID or title match."""
        with self._get_connection() as conn:
            if identifier.isdigit():
                row = conn.execute("SELECT id, title, content, created_at FROM notes WHERE id = ?", (int(identifier),)).fetchone()
            else:
                row = conn.execute("SELECT id, title, content, created_at FROM notes WHERE title LIKE ? LIMIT 1", (f"%{identifier}%",)).fetchone()
            return dict(row) if row else None

    def delete_note(self, identifier: str) -> bool:
        """Delete note by ID or title."""
        with self._get_connection() as conn:
            if identifier.isdigit():
                cur = conn.execute("DELETE FROM notes WHERE id = ?", (int(identifier),))
            else:
                cur = conn.execute("DELETE FROM notes WHERE title LIKE ?", (f"%{identifier}%",))
            conn.commit()
            return cur.rowcount > 0

    # ── Mood Tracking ────────────────────────────────────────────────────────

    def log_mood(self, detected_mood: str, sentiment_score: float, user_snippet: str = "") -> int:
        """Record detected user mood and sentiment score in SQLite."""
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO mood_logs (detected_mood, sentiment_score, user_snippet, timestamp) VALUES (?, ?, ?, ?)",
                (detected_mood, float(sentiment_score), user_snippet[:200], now)
            )
            conn.commit()
            return cur.lastrowid

    def get_mood_history(self, days: int = 7) -> List[Dict[str, Any]]:
        """Fetch mood logs from the past N days."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT id, detected_mood, sentiment_score, user_snippet, timestamp FROM mood_logs WHERE timestamp >= ? ORDER BY id DESC",
                (cutoff,)
            ).fetchall()
            return [dict(r) for r in rows]

    # ── Workflow Habit Tracking ──────────────────────────────────────────────

    def log_habit(self, hour_of_day: int, app_name: str, day_key: Optional[str] = None) -> None:
        """Record an app used at a specific hour of day (deduplicated per day)."""
        if not app_name:
            return
        d_key = day_key or datetime.now().strftime("%Y-%m-%d")
        with self._get_connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO habit_logs (hour_of_day, app_name, day_key) VALUES (?, ?, ?)",
                (int(hour_of_day), app_name.lower().strip(), d_key)
            )
            conn.commit()

    def get_frequent_habits(self, hour_of_day: int, min_days: int = 3) -> List[str]:
        """Return app names used on at least `min_days` distinct days at the given hour."""
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT app_name, COUNT(DISTINCT day_key) as day_count
                FROM habit_logs
                WHERE hour_of_day = ?
                GROUP BY app_name
                HAVING day_count >= ?
                ORDER BY day_count DESC
                """,
                (int(hour_of_day), int(min_days))
            ).fetchall()
            return [r["app_name"] for r in rows]

