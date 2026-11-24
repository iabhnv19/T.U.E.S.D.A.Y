"""
core/planner.py
Autonomous ReAct Planner (Multi-step goal execution) for T.U.E.S.D.A.Y.
Decomposes high-level user goals into structured action chains, executes tools
sequentially with observation analysis, and handles autonomous self-correction.
"""

import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from core.config import Config
from core.llm import UniversalLLMClient
from core.tools import execute_tool, list_tools


@dataclass
class PlanStep:
    """Represents a single atomic action within an autonomous plan."""
    step: int
    action: str
    args: Dict[str, Any] = field(default_factory=dict)
    purpose: str = ""
    status: str = "pending"  # pending, running, completed, failed, skipped
    result: Optional[str] = None


@dataclass
class Plan:
    """Structured multi-step autonomous execution plan."""
    goal: str
    thought: str
    steps: List[PlanStep] = field(default_factory=list)


class ReActPlanner:
    """
    Reason + Act (ReAct) Autonomous Planner.
    1. Analyzes whether a query represents a multi-step goal.
    2. Decomposes the goal into discrete steps using the registered tool catalog.
    3. Executes actions step-by-step, observing outputs.
    4. Self-corrects on failures (e.g., trying alternate parameters or tools).
    5. Synthesizes a unified response in Tuesday's Friday/JARVIS persona.
    """

    def __init__(self, client: Optional[UniversalLLMClient] = None, brain=None, memory=None):
        self.client = client
        self.brain = brain
        self.memory = memory
        self._cached_catalog: Optional[str] = None

        # Multi-step transition keywords in English and Hinglish
        self._transition_patterns = [
            re.compile(r"\b(?:and then|aur fir|aur phir|ke baad|after that|then open|then set|then do|along with|aur saath mein)\b", re.I),
            re.compile(r"\b(?:set up|setup|prepare|tayyar karo)\s+.*?(?:workspace|environment|session|workflow|everything|meeting)\b", re.I),
            re.compile(r"\b(?:workspace ready|clean up and|study mode and|coding mode and|organize everything)\b", re.I),
            re.compile(r"\b(?:karo aur|kijiye aur|kardo aur|step by step|automate|workflow)\b", re.I),
        ]

        # Multi-action connectors: e.g. "open chrome and mute volume"
        self._conjunction_pattern = re.compile(
            r"\b(open|launch|start|close|kill|set|minimize|maximize|snap|take|clean|record|create|search)\b.+?\b(and|aur|then|fir|phir)\b.+?\b(open|launch|start|close|kill|set|minimize|maximize|snap|take|clean|record|create|search|volume|timer|reminder|note|todo)\b",
            re.I
        )

    def is_complex_goal(self, query: str) -> bool:
        """
        Determine if the user query represents a multi-step autonomous goal.
        Returns False for simple, single-turn requests or pure conversation.
        """
        if not query or len(query.strip()) < 10:
            return False

        clean = query.strip().lower()

        # Check explicit multi-step keywords
        for pat in self._transition_patterns:
            if pat.search(clean):
                return True

        # Check multi-action conjunctions
        if self._conjunction_pattern.search(clean):
            return True

        return False

    def get_tool_catalog(self) -> str:
        """Construct a compact summary of available tools for fast in-context planning."""
        if self._cached_catalog is None:
            tools = list_tools()
            lines = []
            for t in sorted(tools, key=lambda x: x.name):
                # Omit high-risk destructive tools from autonomous chain by default
                if t.name in ("shutdown_pc", "restart_pc", "empty_recycle_bin"):
                    continue
                # Brief parameter hints from schema properties
                params = []
                props = t.params_schema.get("properties", {})
                for p_name, p_info in props.items():
                    p_type = p_info.get("type", "string")
                    params.append(f"{p_name}: {p_type}")
                param_str = f"({', '.join(params)})" if params else "()"
                desc = t.description[:90].replace("\n", " ")
                lines.append(f"- {t.name}{param_str}: {desc}")

            self._cached_catalog = "\n".join(lines)

        return self._cached_catalog

    def generate_plan(self, goal: str, context: str = "") -> Optional[Plan]:
        """
        Use LLM reasoning to decompose a high-level goal into an actionable plan.
        """
        if not self.client:
            return None

        catalog = self.get_tool_catalog()
        system_prompt = (
            "You are the Autonomous Planning Engine for T.U.E.S.D.A.Y. "
            "Your task is to decompose high-level user requests into a clean, minimal sequence "
            "of 1 to 5 concrete tool steps using the available tool catalog.\n\n"
            "STRICT RULES:\n"
            "1. ONLY use tools listed in the catalog below.\n"
            "2. Each step must have valid arguments according to its tool specification.\n"
            "3. Order steps logically (e.g., launch app before snapping or typing into it).\n"
            "4. Respond with a valid JSON object ONLY. Do NOT write conversational filler or preamble.\n\n"
            f"AVAILABLE TOOLS:\n{catalog}\n\n"
            "EXPECTED JSON FORMAT:\n"
            "{\n"
            '  "thought": "Brief reasoning explaining the execution strategy",\n'
            '  "steps": [\n'
            '    {"step": 1, "action": "tool_name", "args": {"key": "val"}, "purpose": "Short human description of what this step does"}\n'
            '  ]\n'
            "}"
        )

        user_prompt = f"Goal to achieve: {goal}"
        if context:
            user_prompt += f"\nAdditional Context: {context}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        active_model = getattr(self.brain, "current_model", self.client.default_model)
        try:
            resp = self.client.create_chat_completion(
                messages=messages,
                model=active_model,
                temperature=0.2,
                max_tokens=600,
            )
            if not resp or not resp.choices:
                return None

            raw_content = resp.choices[0].message.content or ""
            return self._parse_plan_json(goal, raw_content)
        except Exception as e:
            print(f"[{Config.NAME}] Planning error: {e}")
            return None

    def _parse_plan_json(self, goal: str, text: str) -> Optional[Plan]:
        """Robustly extract and validate Plan object from model output."""
        cleaned = text.strip()
        # Strip markdown fences if present
        if "```" in cleaned:
            cleaned = re.sub(r"```(?:json)?\s*([\s\S]*?)\s*```", r"\1", cleaned).strip()

        # Locate outermost JSON brackets
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None

        try:
            data = json.loads(cleaned[start:end + 1])
            thought = data.get("thought", "Autonomous multi-step execution")
            raw_steps = data.get("steps", [])
            if not raw_steps or not isinstance(raw_steps, list):
                return None

            steps = []
            for idx, s in enumerate(raw_steps, 1):
                action = s.get("action", "").strip()
                if not action:
                    continue
                args = s.get("args", {})
                if not isinstance(args, dict):
                    args = {}
                purpose = s.get("purpose", f"Execute {action}")
                steps.append(PlanStep(step=idx, action=action, args=args, purpose=purpose))

            if not steps:
                return None

            return Plan(goal=goal, thought=thought, steps=steps)
        except Exception:
            return None

    def _self_correct(self, failed_step: PlanStep, goal: str, completed_steps: List[PlanStep]) -> Optional[PlanStep]:
        """
        Attempt 1-turn corrective reasoning when a plan step fails or produces an error.
        """
        if not self.client:
            return None

        catalog = self.get_tool_catalog()
        history = "\n".join([
            f"Step {s.step} ({s.action}): {'SUCCESS - ' + str(s.result)[:80] if s.status == 'completed' else 'FAILED'}"
            for s in completed_steps
        ])

        system_prompt = (
            "You are the Self-Correction Engine for T.U.E.S.D.A.Y. "
            "A step in the autonomous plan failed. Propose an alternate or fixed single step to recover, "
            "or decide to skip gracefully if unrecoverable.\n\n"
            f"AVAILABLE TOOLS:\n{catalog}\n\n"
            "OUTPUT JSON ONLY:\n"
            '{"action": "tool_name", "args": {"key": "val"}, "purpose": "Explanation of fix"}\n'
            'Or if it cannot be recovered: {"action": "skip", "args": {}, "purpose": "Reason to skip"}'
        )

        user_prompt = (
            f"Overall Goal: {goal}\n"
            f"Execution History:\n{history}\n"
            f"Failed Step: {failed_step.action} with args {failed_step.args}\n"
            f"Error Output: {failed_step.result}\n"
            "What is the corrected action?"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        active_model = getattr(self.brain, "current_model", self.client.default_model)
        try:
            resp = self.client.create_chat_completion(
                messages=messages,
                model=active_model,
                temperature=0.1,
                max_tokens=300,
            )
            if not resp or not resp.choices:
                return None

            raw = resp.choices[0].message.content or ""
            if "```" in raw:
                raw = re.sub(r"```(?:json)?\s*([\s\S]*?)\s*```", r"\1", raw).strip()
            start = raw.find("{")
            end = raw.rfind("}")
            if start == -1 or end == -1:
                return None

            data = json.loads(raw[start:end + 1])
            new_action = data.get("action", "").strip()
            if not new_action or new_action == "skip":
                return None

            return PlanStep(
                step=failed_step.step,
                action=new_action,
                args=data.get("args", {}),
                purpose=data.get("purpose", f"Corrected {new_action}"),
            )
        except Exception:
            return None

    def execute_goal(
        self,
        goal: str,
        on_status: Optional[Callable[[str], None]] = None,
        on_sentence: Optional[Callable[[str], None]] = None,
        on_step: Optional[Callable[[PlanStep], None]] = None,
    ) -> str:
        """
        Full ReAct Execution Loop:
        1. Formulate Plan
        2. Execute Steps & Observe
        3. Self-correct if an error is encountered
        4. Synthesize final natural response
        """
        if on_status:
            on_status("Formulating autonomous plan...")

        print(f"\n[{Config.NAME}] 🧠 ReAct Planning for: '{goal}'")
        plan = self.generate_plan(goal)

        # Fallback if planning failed
        if not plan or not plan.steps:
            print(f"[{Config.NAME}] ⚠️ Could not generate multi-step plan, falling back to standard agent loop.")
            # Trigger standard tool-calling agent loop in brain
            if self.brain:
                return self.brain._execute_standard_agent_turn(goal, on_status=on_status, on_sentence=on_sentence)
            return "Sir, main is goal ke steps plan nahi kar paayi. Ek baar direct command dekar dekhein?"

        print(f"[{Config.NAME}] 📋 Plan generated ({len(plan.steps)} steps): {plan.thought}")
        for s in plan.steps:
            print(f"    Step {s.step}: {s.action}({s.args}) — {s.purpose}")

        completed_steps: List[PlanStep] = []

        for step in plan.steps:
            step.status = "running"
            status_msg = f"Step {step.step}/{len(plan.steps)}: {step.purpose}..."
            if on_status:
                on_status(status_msg)
            if on_step:
                on_step(step)

            print(f"[{Config.NAME}] ⚡ Executing Step {step.step}: {step.action}...")
            result = execute_tool(step.action, step.args, context={"source": "react_planner"})
            step.result = str(result)

            is_error = False
            lower_res = step.result.lower()
            if any(err_word in lower_res for err_word in ("error", "exception", "failed", "not found", "invalid")):
                # Some tools say "0 unread" or "No notes found" which is normal
                if "not found in registry" in lower_res or "error executing" in lower_res:
                    is_error = True

            if is_error:
                print(f"[{Config.NAME}] ⚠️ Step {step.step} failed: {step.result}. Initiating self-correction...")
                if on_status:
                    on_status(f"Step {step.step} had an issue, self-correcting...")
                corrected = self._self_correct(step, goal, completed_steps)
                if corrected:
                    print(f"[{Config.NAME}] 🔧 Corrective step: {corrected.action}({corrected.args})")
                    corr_result = execute_tool(corrected.action, corrected.args, context={"source": "react_planner"})
                    step.action = corrected.action
                    step.args = corrected.args
                    step.result = str(corr_result)
                    step.purpose = corrected.purpose
                    step.status = "completed"
                else:
                    step.status = "failed"
            else:
                step.status = "completed"

            completed_steps.append(step)

        # Final Synthesis
        if on_status:
            on_status("Synthesizing final update...")

        final_reply = self._synthesize_final_reply(goal, plan, completed_steps)

        # Stream sentences to TTS if callback provided
        if on_sentence and final_reply:
            from core.brain import SentenceChunker
            chunker = SentenceChunker()
            chunks = chunker.add_token(final_reply) + chunker.flush()
            for ch in chunks:
                on_sentence(ch)

        # Record turn in SQLite & context
        if self.brain:
            self.brain._record_dialogue(goal, final_reply)

        return final_reply

    def _synthesize_final_reply(self, goal: str, plan: Plan, steps: List[PlanStep]) -> str:
        """Synthesize a natural, respectful Friday/JARVIS spoken summary of completed steps."""
        if not self.client:
            successful = [s.purpose for s in steps if s.status == "completed"]
            return f"Sir, maine aapka goal poora kar diya hai: {', '.join(successful)}."

        steps_summary = []
        for s in steps:
            status_tag = "Done" if s.status == "completed" else "Skipped/Failed"
            steps_summary.append(f"- Step {s.step} ({status_tag}): {s.purpose} -> Result: {str(s.result)[:80]}")

        system_prompt = (
            f"{Config.SYSTEM_PROMPT}\n"
            "You are T.U.E.S.D.A.Y. You just autonomously executed a multi-step user goal. "
            "Give a concise, charming 1-2 sentence spoken summary in Hinglish addressed to Sir/Boss. "
            "Confirm that the workspace/environment is ready. "
            "STRICT RULES: No markdown asterisks, no bullet points, no emojis, plain natural speech only."
        )

        user_prompt = (
            f"User Goal: {goal}\n"
            f"Execution Results:\n" + "\n".join(steps_summary) + "\n\n"
            "Give your final brief spoken confirmation:"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        active_model = getattr(self.brain, "current_model", self.client.default_model)
        try:
            resp = self.client.create_chat_completion(
                messages=messages,
                model=active_model,
                temperature=0.6,
                max_tokens=250,
            )
            if resp and resp.choices:
                raw = resp.choices[0].message.content or ""
                from core.brain import _clean_text_for_speech
                return _clean_text_for_speech(raw)
        except Exception:
            pass

        return "Maine aapke saare steps execute kar diye hain Sir. Sab ready hai."
