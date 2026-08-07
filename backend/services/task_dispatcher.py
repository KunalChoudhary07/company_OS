import asyncio
import json
import logging
import time
from typing import AsyncGenerator, Dict, Any

from backend.prompts.agents import (
    CEO_PLANNER_PROMPT,
    RESEARCH_AGENT_PROMPT,
    FINANCE_AGENT_PROMPT,
    MARKETING_AGENT_PROMPT,
    SALES_AGENT_PROMPT,
    CEO_SYNTHESIZER_PROMPT,
    build_context_prompt
)
from backend.services.orchestrator import _call_llm, _parse_and_validate
from backend.services.agents.registry import get_agent_metadata
from backend.services.agents.research_agent import run_research_agent

logger = logging.getLogger("companyos.dispatcher")

# Agents the dispatcher can actually execute. The CEO Planner is an LLM and
# (especially on smaller models like llama-3.1-8b-instant) will sometimes
# invent departments that don't exist — e.g. "development", "implementation",
# "operations". Those tasks used to fall through the execute_task() if/elif
# chain and silently do nothing: no result, no error, no visible failure.
# We validate the plan against this set before executing anything.
EXECUTABLE_AGENTS = ("research", "finance", "marketing", "sales")

# Canonical task shape used when the planner omits a required department.
# All four must run, because the final response (and the frontend) expects a
# block for each one.
_DEFAULT_TASKS = {
    "research":  {"taskId": "research-001",  "agent": "research",  "objective": "Analyze market, competitors and target customers", "priority": "high", "dependencies": [],                 "status": "QUEUED"},
    "finance":   {"taskId": "finance-001",   "agent": "finance",   "objective": "Analyze budget and financial requirements",        "priority": "high", "dependencies": [],                 "status": "QUEUED"},
    "marketing": {"taskId": "marketing-001", "agent": "marketing", "objective": "Create go-to-market campaign strategy",            "priority": "high", "dependencies": ["research-001"],   "status": "QUEUED"},
    "sales":     {"taskId": "sales-001",     "agent": "sales",     "objective": "Define ideal customers and sales strategy",        "priority": "high", "dependencies": ["research-001"],   "status": "QUEUED"},
}


def sanitize_plan(raw_plan: Any) -> tuple[list, list]:
    """
    Make an LLM-produced plan safe to execute.

    Returns (clean_plan, dropped) where `dropped` is a list of
    (agent_id, reason) tuples describing what was discarded and why, so the
    caller can surface it instead of failing invisibly.

    Guarantees about clean_plan:
      - every task targets an agent in EXECUTABLE_AGENTS
      - exactly one task per agent (duplicates dropped)
      - all four departments are present (missing ones are injected)
      - no dependency references a taskId that isn't in the plan
    """
    dropped: list = []
    seen_agents: set = set()
    clean: list = []

    if not isinstance(raw_plan, list):
        logger.warning(f"CEO plan was not a list (got {type(raw_plan).__name__}); rebuilding from defaults")
        raw_plan = []

    for task in raw_plan:
        if not isinstance(task, dict):
            dropped.append(("unknown", "task was not an object"))
            continue

        agent_id = task.get("agent")
        if agent_id not in EXECUTABLE_AGENTS:
            dropped.append((str(agent_id), "no such department in CompanyOS"))
            continue
        if agent_id in seen_agents:
            dropped.append((agent_id, "duplicate task for the same department"))
            continue

        seen_agents.add(agent_id)
        # Normalise the taskId so dependency wiring stays predictable.
        task = {**task, "taskId": _DEFAULT_TASKS[agent_id]["taskId"]}
        clean.append(task)

    # Inject any department the planner forgot — all four are required.
    for agent_id in EXECUTABLE_AGENTS:
        if agent_id not in seen_agents:
            logger.info(f"CEO plan omitted '{agent_id}'; injecting default task")
            clean.append(dict(_DEFAULT_TASKS[agent_id]))

    # Drop dependency references to tasks that no longer exist (e.g. marketing
    # depending on the hallucinated "development-001"). A dangling dependency
    # would otherwise push a task into the dependent batch waiting on
    # something that never runs.
    valid_ids = {t["taskId"] for t in clean}
    for task in clean:
        deps = task.get("dependencies") or []
        if not isinstance(deps, list):
            deps = []
        kept = [d for d in deps if d in valid_ids and d != task["taskId"]]
        if len(kept) != len(deps):
            removed = [d for d in deps if d not in kept]
            logger.info(f"Stripped dangling dependencies {removed} from {task['taskId']}")
        task["dependencies"] = kept

    # Keep a stable execution order: independents first, then dependents.
    clean.sort(key=lambda t: (bool(t.get("dependencies")), EXECUTABLE_AGENTS.index(t["agent"])))
    return clean, dropped


async def parse_json_from_llm(raw: str) -> Dict:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
    return json.loads(cleaned)

class TaskDispatcher:
    def __init__(self, req):
        self.req = req
        self.results = {}
        self.plan = []
        
    async def run(self) -> AsyncGenerator[str, None]:
        # 1. CEO Planning Phase
        yield self._format_sse("status", {"agent": "ceo", "status": "Planning execution..."})
        
        user_prompt = build_context_prompt(self.req)
        try:
            ceo_plan_raw = await _call_llm(CEO_PLANNER_PROMPT, user_prompt)
            ceo_plan = await parse_json_from_llm(ceo_plan_raw)
        except Exception as e:
            logger.error(f"CEO Planner failed: {e}")
            yield self._format_sse("error", {"message": f"CEO Planner failed: {e}"})
            return

        # Validate the LLM's plan before executing any of it. Without this,
        # invented departments silently no-op and the run appears to stall.
        self.plan, dropped_tasks = sanitize_plan(ceo_plan.get("plan", []))

        # Save CEO output parts that go into final response
        self.results["company"] = ceo_plan.get("company", {})
        self.results["initiative"] = ceo_plan.get("initiative", {})
        self.results["execution_plan"] = ceo_plan.get("execution_plan", [])
        
        yield self._format_sse("status", {"agent": "ceo", "status": "Plan created ✓"})

        # Surface anything we discarded so a bad plan is never invisible.
        for agent_id, reason in dropped_tasks:
            logger.warning(f"Dropped planned task for '{agent_id}': {reason}")
            yield self._format_sse("status", {
                "agent": "ceo",
                "status": f"Skipped unsupported task '{agent_id}' — {reason}",
            })

        yield self._format_sse("plan", {"plan": self.plan})
        
        # Mark all as QUEUED initially
        for task in self.plan:
            yield self._format_sse("status", {"agent": task["agent"], "status": "QUEUED"})

        # 2. Execution Phase
        # We handle dependencies simply: Research and Finance have no dependencies, Marketing and Sales depend on Research.
        # This matches the user's specific request.
        
        # Run independent tasks first (Research, Finance)
        independent_tasks = [t for t in self.plan if not t.get("dependencies")]
        dependent_tasks = [t for t in self.plan if t.get("dependencies")]
        
        # We will use asyncio.gather for tasks that can run in parallel
        async def execute_task(task: dict):
            agent_id = task["agent"]
            yield self._format_sse("status", {"agent": agent_id, "status": "RUNNING..."})

            # ── Research Agent: uses real web search ──────────────────────────
            if agent_id == "research":
                try:
                    # Use a local queue to collect events from the research agent callbacks
                    research_queue: asyncio.Queue = asyncio.Queue()

                    async def _emit_status(text: str):
                        await research_queue.put(
                            self._format_sse("status", {"agent": "research", "status": text})
                        )

                    async def _emit_search(query: str, count: int, results: list, error: str = None):
                        await research_queue.put(
                            self._format_sse("search", {
                                "query": query,
                                "count": count,
                                "results": results,
                                "error": error,
                            })
                        )

                    async def _run_research():
                        try:
                            result = await run_research_agent(
                                req=self.req,
                                emit_status=_emit_status,
                                emit_search=_emit_search,
                            )
                            await research_queue.put(("DONE", result))
                        except Exception as e:
                            await research_queue.put(("ERROR", str(e)))

                    research_task = asyncio.create_task(_run_research())

                    task_result = None
                    while True:
                        item = await research_queue.get()
                        if isinstance(item, str):
                            # It's an SSE string event
                            yield item
                        elif isinstance(item, tuple):
                            status, payload = item
                            if status == "DONE":
                                task_result = payload
                                break
                            else:  # ERROR
                                logger.error(f"Research Agent error: {payload}")
                                yield self._format_sse("status", {"agent": "research", "status": "FAILED ✗"})
                                yield self._format_sse("error", {"message": f"Research Agent failed: {payload}"})
                                return

                    self.results["research"] = task_result
                    yield self._format_sse("status", {"agent": "research", "status": "COMPLETED ✓"})
                    yield self._format_sse("result", {"agent": "research", "data": task_result})

                except Exception as e:
                    logger.error(f"Research Agent fatal: {e}")
                    yield self._format_sse("status", {"agent": "research", "status": "FAILED ✗"})
                    yield self._format_sse("error", {"message": f"Research Agent failed: {e}"})
                return

            # ── Finance Agent: parses CSV and calculates metrics ─────────────────
            elif agent_id == "finance":
                try:
                    from backend.services.agents.finance_agent import run_finance_agent
                    finance_queue: asyncio.Queue = asyncio.Queue()

                    async def _emit_finance_status(text: str):
                        await finance_queue.put(
                            self._format_sse("status", {"agent": "finance", "status": text})
                        )

                    async def _run_finance():
                        try:
                            # if no CSV, fail gracefully with the requested message
                            if not self.req.csv_data:
                                await finance_queue.put(("DONE", {
                                    "agent": "finance",
                                    "status": "COMPLETED",
                                    "metrics": {},
                                    "aiInsights": {"summary": "Financial dataset not available."},
                                    "dataQuality": {"rows": 0, "validRows": 0, "invalidRows": 0, "missingColumns": []},
                                    "forecast": {"available": False, "nextMonthRevenue": None, "nextThreeMonths": []}
                                }))
                                return

                            result = await run_finance_agent(self.req, self.req.csv_data, _emit_finance_status)
                            await finance_queue.put(("DONE", result))
                        except Exception as e:
                            await finance_queue.put(("ERROR", str(e)))

                    finance_task = asyncio.create_task(_run_finance())

                    task_result = None
                    while True:
                        item = await finance_queue.get()
                        if isinstance(item, str):
                            yield item
                        elif isinstance(item, tuple):
                            status, payload = item
                            if status == "DONE":
                                task_result = payload
                                break
                            else:
                                logger.error(f"Finance Agent error: {payload}")
                                yield self._format_sse("status", {"agent": "finance", "status": "FAILED ✗"})
                                yield self._format_sse("error", {"message": f"Finance Agent validation failed: {payload}"})
                                return

                    self.results["finance"] = task_result
                    yield self._format_sse("status", {"agent": "finance", "status": "COMPLETED ✓"})
                    yield self._format_sse("result", {"agent": "finance", "data": task_result})

                except Exception as e:
                    logger.error(f"Finance Agent fatal: {e}")
                    yield self._format_sse("status", {"agent": "finance", "status": "FAILED ✗"})
                    yield self._format_sse("error", {"message": f"Finance Agent failed: {e}"})
                return

            # ── Marketing Agent: Uses context from research & finance ────────
            elif agent_id == "marketing":
                try:
                    from backend.services.agents.marketing_agent import run_marketing_agent
                    mkt_queue: asyncio.Queue = asyncio.Queue()

                    async def _emit_mkt_status(text: str):
                        await mkt_queue.put(
                            self._format_sse("status", {"agent": "marketing", "status": text})
                        )

                    async def _run_mkt():
                        try:
                            result = await run_marketing_agent(self.req, self.results, _emit_mkt_status)
                            await mkt_queue.put(("DONE", result))
                        except Exception as e:
                            await mkt_queue.put(("ERROR", str(e)))

                    mkt_task = asyncio.create_task(_run_mkt())

                    task_result = None
                    while True:
                        item = await mkt_queue.get()
                        if isinstance(item, str):
                            yield item
                        elif isinstance(item, tuple):
                            status, payload = item
                            if status == "DONE":
                                task_result = payload
                                break
                            else:
                                logger.error(f"Marketing Agent error: {payload}")
                                yield self._format_sse("status", {"agent": "marketing", "status": "FAILED ✗"})
                                yield self._format_sse("error", {"message": f"Marketing Agent validation failed: {payload}"})
                                return

                    self.results["marketing"] = task_result
                    yield self._format_sse("status", {"agent": "marketing", "status": "COMPLETED ✓"})
                    yield self._format_sse("result", {"agent": "marketing", "data": task_result})

                except Exception as e:
                    logger.error(f"Marketing Agent fatal: {e}")
                    yield self._format_sse("status", {"agent": "marketing", "status": "FAILED ✗"})
                    yield self._format_sse("error", {"message": f"Marketing Agent failed: {e}"})
                return

            # ── Sales Agent: Prospecting & Lead Scoring ────────
            elif agent_id == "sales":
                try:
                    from backend.services.agents.sales_agent import run_sales_agent
                    sales_queue: asyncio.Queue = asyncio.Queue()

                    async def _emit_sales_status(text: str):
                        await sales_queue.put(
                            self._format_sse("status", {"agent": "sales", "status": text})
                        )

                    async def _run_sales():
                        try:
                            result = await run_sales_agent(self.req, self.results, _emit_sales_status)
                            await sales_queue.put(("DONE", result))
                        except Exception as e:
                            await sales_queue.put(("ERROR", str(e)))

                    sales_task = asyncio.create_task(_run_sales())

                    task_result = None
                    while True:
                        item = await sales_queue.get()
                        if isinstance(item, str):
                            yield item
                        elif isinstance(item, tuple):
                            status, payload = item
                            if status == "DONE":
                                task_result = payload
                                break
                            else:
                                logger.error(f"Sales Agent error: {payload}")
                                yield self._format_sse("status", {"agent": "sales", "status": "FAILED ✗"})
                                yield self._format_sse("error", {"message": f"Sales Agent validation failed: {payload}"})
                                return

                    self.results["sales"] = task_result
                    yield self._format_sse("status", {"agent": "sales", "status": "COMPLETED ✓"})
                    yield self._format_sse("result", {"agent": "sales", "data": task_result})

                except Exception as e:
                    logger.error(f"Sales Agent fatal: {e}")
                    yield self._format_sse("status", {"agent": "sales", "status": "FAILED ✗"})
                    yield self._format_sse("error", {"message": f"Sales Agent failed: {e}"})
                return

            # ── Safety net ────────────────────────────────────────────────────
            # sanitize_plan() should make this unreachable. If it ever is
            # reached, fail loudly rather than silently doing nothing — an
            # invisible no-op is what made the original bug so hard to spot.
            else:
                logger.error(f"execute_task reached an unhandled agent: '{agent_id}'")
                yield self._format_sse("status", {"agent": agent_id, "status": "SKIPPED ✗"})
                yield self._format_sse("error", {
                    "message": f"No executor is implemented for department '{agent_id}'. Task skipped."
                })
                return


        # Run independent tasks in parallel
        # Since we yield from generator, we need a queue or we just await them. 
        # Using a queue to interleave SSE yields from parallel tasks:
        queue = asyncio.Queue()
        
        async def run_and_queue(task):
            try:
                async for event in execute_task(task):
                    await queue.put(event)
            finally:
                await queue.put(None) # Marker for completion
        
        # Start independent tasks
        workers = [asyncio.create_task(run_and_queue(t)) for t in independent_tasks]
        
        # Read from queue as events come in
        finished_workers = 0
        while finished_workers < len(workers):
            event = await queue.get()
            if event is None:
                finished_workers += 1
            else:
                yield event

        # Now run dependent tasks
        workers = [asyncio.create_task(run_and_queue(t)) for t in dependent_tasks]
        finished_workers = 0
        while finished_workers < len(workers):
            event = await queue.get()
            if event is None:
                finished_workers += 1
            else:
                yield event

        # 3. CEO Synthesis Phase
        yield self._format_sse("status", {"agent": "ceo", "status": "Synthesizing results..."})
        
        try:
            ceo_synth_prompt = build_context_prompt(self.req, self.results)
            raw = await _call_llm(CEO_SYNTHESIZER_PROMPT, ceo_synth_prompt)
            ceo_synth = await parse_json_from_llm(raw)
        except Exception as e:
            logger.error(f"CEO Synthesis failed: {e}")
            yield self._format_sse("error", {"message": f"CEO Synthesis failed: {e}"})
            return

        # Build final response combining everything
        final_response = {
            "initiative": self.results.get("initiative", {}),
            "company": self.results.get("company", {}),
            "execution_plan": self.results.get("execution_plan", []),
            "research": self.results.get("research", {}),
            "finance": self.results.get("finance", {}),
            "marketing": self.results.get("marketing", {}),
            "sales": self.results.get("sales", {}),
            "executive_summary": ceo_synth.get("executive_summary", ""),
            "jarvis_voice_summary": ceo_synth.get("jarvis_voice_summary", ""),
            "recommendations": ceo_synth.get("recommendations", []),
            "next_steps": ceo_synth.get("next_steps", []),
            "agents": ceo_synth.get("agents", {})
        }
        
        yield self._format_sse("status", {"agent": "ceo", "status": "COMPANY LAUNCH PLAN READY ✓"})
        yield self._format_sse("complete", {"final_data": final_response})

    def _format_sse(self, event_type: str, data: Dict) -> str:
        return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
