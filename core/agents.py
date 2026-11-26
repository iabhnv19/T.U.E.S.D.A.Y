"""
core/agents.py
Specialist Multi-Agent Swarm for T.U.E.S.D.A.Y.
Orchestrates parallel micro-agents for deep research, comparison, and synthesis:
1. ResearcherAgent: Fans out parallel live web searches for sub-topics.
2. AnalystAgent: Cross-checks facts, compares specs/prices, filters fluff.
3. WriterAgent: Formats structured output, optionally saves notes, and produces a crisp spoken verdict.
"""

import concurrent.futures
import json
import re
from typing import Any, Callable, Dict, List, Optional

from core.config import Config
from core.llm import UniversalLLMClient
from core.memory import MemoryStore
from modules.web_search import perform_live_web_search


class ResearcherAgent:
    """Specialist agent that gathers real-time web facts across parallel sub-queries."""

    def gather(self, sub_queries: List[str]) -> str:
        """Execute web searches in parallel and aggregate raw findings."""
        if not sub_queries:
            return ""

        findings: List[str] = []

        def _search_one(q: str) -> str:
            res = perform_live_web_search(q)
            if not res:
                try:
                    from duckduckgo_search import DDGS
                    results = list(DDGS().text(q, max_results=3))
                    if results:
                        res = "\n".join(f"- {r.get('title', '')}: {r.get('body', '')}" for r in results)
                except Exception:
                    res = ""
            return f"### Query: {q}\n{res}" if res else ""

        with concurrent.futures.ThreadPoolExecutor(max_workers=min(3, len(sub_queries))) as executor:
            futures = [executor.submit(_search_one, q) for q in sub_queries[:3]]
            for f in concurrent.futures.as_completed(futures, timeout=8.0):
                try:
                    out = f.result()
                    if out:
                        findings.append(out)
                except Exception:
                    pass

        return "\n\n".join(findings)


class AnalystAgent:
    """Specialist agent that extracts specs, compares options, and filters fluff."""

    def __init__(self, client: Optional[UniversalLLMClient], model: str):
        self.client = client
        self.model = model

    def analyze(self, goal: str, raw_research: str) -> str:
        """Cross-check and structure raw research findings into a comparison."""
        if not self.client:
            return raw_research[:1200] if raw_research else "No live data found."

        prompt = (
            "You are the AnalystAgent. Given raw web research (or general knowledge if web data is sparse), "
            "extract concrete specs, prices, pros, cons, and a structured comparison answering the user's request.\n"
            "Be factual, concise, and skip marketing fluff.\n\n"
            f"User Request: {goal}\n\n"
            f"Raw Research:\n{raw_research[:3000] if raw_research else 'No live web snippets available; use accurate domain knowledge.'}"
        )
        try:
            resp = self.client.create_chat_completion(
                messages=[
                    {"role": "system", "content": "You are a sharp technical & product analyst."},
                    {"role": "user", "content": prompt},
                ],
                model=self.model,
                temperature=0.3,
                max_tokens=500,
            )
            if resp and resp.choices:
                return resp.choices[0].message.content or ""
        except Exception:
            pass
        return raw_research[:1000]


class WriterAgent:
    """Specialist agent that saves structured notes (if requested) and produces a crisp spoken verdict."""

    def __init__(self, client: Optional[UniversalLLMClient], model: str, memory: Optional[MemoryStore] = None):
        self.client = client
        self.model = model
        self.memory = memory or MemoryStore()

    def synthesize(self, goal: str, analysis: str, save_note: bool = False) -> str:
        """Format final spoken verdict and optionally persist detailed analysis as a note."""
        if save_note and analysis:
            try:
                title = re.sub(r"^(?:find|research|compare|best)\s+", "", goal, flags=re.I).strip()[:40] or "Research Summary"
                self.memory.add_note(title=title, content=analysis)
            except Exception:
                pass

        if not self.client:
            return analysis[:300]

        note_hint = " Mention that you saved the detailed comparison to their notes." if save_note else ""
        system_prompt = (
            f"{Config.SYSTEM_PROMPT}\n"
            "You are T.U.E.S.D.A.Y delivering the final verdict from your specialist research swarm. "
            "Summarize the top recommendation(s) in 2-3 natural Hinglish sentences addressed to Sir/Boss."
            f"{note_hint} "
            "STRICT RULES: No markdown asterisks, no bullet points, no emojis, plain spoken text only."
        )
        try:
            resp = self.client.create_chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Goal: {goal}\n\nAnalyst Findings:\n{analysis}\n\nSpoken Verdict:"},
                ],
                model=self.model,
                temperature=0.5,
                max_tokens=250,
            )
            if resp and resp.choices:
                raw = resp.choices[0].message.content or ""
                from core.brain import _clean_text_for_speech
                return _clean_text_for_speech(raw)
        except Exception:
            pass
        return "Sir, research complete ho gayi hai aur maine best options nikaal liye hain."


class AgentSwarm:
    """Orchestrates ResearcherAgent -> AnalystAgent -> WriterAgent for deep research & comparison tasks."""

    def __init__(self, client: Optional[UniversalLLMClient] = None, brain=None, memory: Optional[MemoryStore] = None):
        self.client = client
        self.brain = brain
        self.memory = memory or MemoryStore()

        self._swarm_patterns = [
            re.compile(r"\b(?:compare|comparison|vs|versus)\b", re.I),
            re.compile(r"\b(?:research|deep dive|in-depth|find the best|top \d+)\b", re.I),
            re.compile(r"\b(?:pros and cons|which is better|best .+ under)\b", re.I),
        ]

    def is_swarm_query(self, query: str) -> bool:
        """Detect queries that benefit from parallel multi-agent research & analysis."""
        if not query or len(query.strip()) < 12:
            return False
        lower = query.lower()
        # Require at least one deep research/comparison pattern
        return any(p.search(lower) for p in self._swarm_patterns)

    def _decompose_queries(self, goal: str) -> List[str]:
        """Split a research goal into 2-3 focused search queries."""
        clean = re.sub(r"\b(?:and save a note|save note|note likho|and compare.*)\b", "", goal, flags=re.I).strip()
        queries = [clean]
        if "compare" in goal.lower() or "best" in goal.lower():
            queries.append(f"{clean} specs pros cons review")
        return queries[:2]

    def run_swarm(
        self,
        goal: str,
        on_status: Optional[Callable[[str], None]] = None,
        on_sentence: Optional[Callable[[str], None]] = None,
    ) -> str:
        """Execute full Researcher -> Analyst -> Writer pipeline."""
        active_model = getattr(self.brain, "current_model", self.client.default_model if self.client else Config.LLM_MODEL)
        save_note = any(k in goal.lower() for k in ("save a note", "save note", "save it", "note likho", "make a note"))

        if on_status:
            on_status("Swarm: ResearcherAgent gathering live data...")
        print(f"\n[{Config.NAME}] 🐝 Spawning Specialist Swarm for: '{goal}'")

        sub_queries = self._decompose_queries(goal)
        researcher = ResearcherAgent()
        raw_research = researcher.gather(sub_queries)

        if on_status:
            on_status("Swarm: AnalystAgent comparing specs & facts...")
        analyst = AnalystAgent(self.client, active_model)
        analysis = analyst.analyze(goal, raw_research)

        if on_status:
            on_status("Swarm: WriterAgent synthesizing verdict...")
        writer = WriterAgent(self.client, active_model, self.memory)
        verdict = writer.synthesize(goal, analysis, save_note=save_note)

        if on_sentence and verdict:
            from core.brain import SentenceChunker
            chunker = SentenceChunker()
            for ch in chunker.add_token(verdict) + chunker.flush():
                on_sentence(ch)

        if self.brain:
            self.brain._record_dialogue(goal, verdict)

        return verdict
