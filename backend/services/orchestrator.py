"""
CompanyOS Orchestrator
======================
Performs ONE LLM call per initiative.
Validates response against Pydantic schema.
Falls back to demo data ONLY when DEMO_MODE=true (explicit opt-in).
"""

import json
import logging
import os
from typing import Optional

from backend.prompts.master import (
    SYSTEM_PROMPT,
    FOLLOWUP_SYSTEM_PROMPT,
    build_user_prompt,
    build_followup_prompt,
)
from backend.schemas.companyos import CompanyOSResponse, InitiativeRequest
logger = logging.getLogger("companyos.orchestrator")

# CRITICAL FIX: Default to false — demo mode must be explicitly opted in.
# Previously defaulted to "true", causing ALL requests to return BeanRush data.
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite-preview")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

logger.info(f"[CompanyOS Backend] Orchestrator loaded — DEMO_MODE={DEMO_MODE}, LLM_PROVIDER={LLM_PROVIDER}, API_KEY={'SET' if LLM_API_KEY and LLM_API_KEY != 'your_api_key_here' else 'MISSING'}")


# ─── Demo Data ────────────────────────────────────────────────────────────────

DEMO_RESPONSE: dict = {
    "initiative": {
        "name": "BeanRush Coffee",
        "objective": "Launch a coffee startup in Chandigarh",
        "location": "Chandigarh, India",
        "status": "active"
    },
    "executive_summary": "BeanRush Coffee targets urban professionals and students in Chandigarh seeking high-quality, ethically sourced coffee with a focus on speed and technology-driven ordering. The primary differentiator is a proprietary mobile app enabling seamless pre-ordering for zero-wait pickup.\n\nInitial launch is planned at Sector 17 Plaza — high foot traffic, proximity to corporate offices and Panjab University. The model emphasizes high-margin espresso drinks and strategic partnerships with local artisanal bakeries.\n\nWith an initial investment of ₹8.5 lakh and a projected break-even at Month 8, BeanRush Coffee is positioned to capture ₹1.8 Cr in Year 1 revenue by capitalizing on the city's underserved tech-enabled grab-and-go coffee segment.",
    "jarvis_voice_summary": "The BeanRush Coffee plan is ready. Initial investment is ₹8.5 lakh with projected monthly revenue of ₹1.5 lakh by Month 3 and break-even at Month 8. The strongest opportunity is targeting young professionals and students through a mobile-first ordering experience.",
    "company": {
        "industry": "Food & Beverage — Specialty Coffee",
        "stage": "Pre-seed",
        "business_model": "B2C (walk-in + app pre-order) with B2B corporate orders",
        "target_market": "Urban professionals aged 22–38 and university students in Chandigarh seeking premium, fast, tech-enabled coffee experiences"
    },
    "agents": {
        "ceo": {"status": "completed", "summary": "Prioritized Sector 17 as launch location and mobile-first strategy as primary differentiator."},
        "research": {"status": "completed", "summary": "Identified 11% CAGR market growth with low penetration of tech-enabled grab-and-go models in Chandigarh."},
        "finance": {"status": "completed", "summary": "Modeled ₹8.5L capex with Month 8 break-even and 62% gross margin at steady state."},
        "marketing": {"status": "completed", "summary": "Recommended Instagram-first launch with university ambassador program and Swiggy/Zomato partnership."},
        "sales": {"status": "completed", "summary": "Identified corporate bulk orders and subscription beans as highest-margin secondary revenue channels."}
    },
    "research": {
        "market_overview": "The specialty coffee market in Chandigarh is growing at 11% CAGR, driven by a young, aspirational population and rising disposable incomes. The city has over 200 coffee outlets but fewer than 5 tech-enabled grab-and-go concepts, representing a clear whitespace opportunity.",
        "market_size_tam": "₹450 Cr",
        "market_size_sam": "₹120 Cr",
        "market_size_som": "₹18 Cr",
        "target_customers": [
            {"segment": "Young Professionals (22–38)", "description": "Corporate office workers and IT professionals who value speed, quality, and loyalty rewards. Located near Sector 17 and Mohali IT Park.", "priority": "primary"},
            {"segment": "University Students", "description": "Panjab University and Chandigarh University students who value Instagram-worthy experiences, app integrations, and affordable loyalty programs.", "priority": "secondary"},
            {"segment": "Health-Conscious Consumers", "description": "Growing segment seeking oat milk, cold brew, and functional coffee drinks. Willing to pay a 20% premium.", "priority": "tertiary"}
        ],
        "competitors": [
            {"name": "Barista Coffee", "strength": "Established brand, large menu", "weakness": "Slow service, no app ordering, dated interiors"},
            {"name": "Café Coffee Day", "strength": "Wide network, affordable pricing", "weakness": "Declining brand perception, average quality"},
            {"name": "Third Wave Coffee", "strength": "Premium positioning, strong digital brand", "weakness": "Limited Chandigarh presence, higher price point"}
        ],
        "market_opportunities": [
            "Zero-wait mobile pre-ordering — no competitor in Chandigarh offers this",
            "Corporate bulk delivery partnerships with Mohali IT Park companies",
            "University ambassador program tapping into 50,000+ student base",
            "Specialty cold brew and seasonal drinks — high margins, low competition"
        ],
        "risks": [
            "High commercial rent in Sector 17 — negotiate 6-month rent moratorium",
            "Arabica bean price volatility due to climate anomalies — hedge with fixed supplier contracts",
            "Copycat risk from established chains — protect via strong brand and loyalty ecosystem"
        ]
    },
    "finance": {
        "initial_investment": 850000,
        "monthly_revenue": 150000,
        "monthly_expenses": 88000,
        "estimated_profit": 62000,
        "gross_margin_percent": 41.3,
        "break_even_estimate": "Month 8",
        "cost_breakdown": [
            {"category": "Espresso Machines & Equipment", "amount": 320000, "percentage": 37.6},
            {"category": "Interior Fit-out & Build", "amount": 280000, "percentage": 32.9},
            {"category": "Working Capital (3 months)", "amount": 150000, "percentage": 17.6},
            {"category": "Tech & App Development", "amount": 60000, "percentage": 7.1},
            {"category": "Marketing Launch Budget", "amount": 40000, "percentage": 4.7}
        ],
        "year1_revenue": 1080000,
        "year2_revenue": 2880000,
        "year3_revenue": 4800000
    },
    "marketing": {
        "brand_positioning": "BeanRush Coffee is the 'fast-lane espresso' brand for Chandigarh's ambitious professionals — premium quality, zero wait, delivered through a seamless mobile experience.",
        "campaigns": [
            {"name": "Zero-Wait Launch", "channel": "Instagram + Google Ads", "description": "30-day pre-launch hype campaign showcasing the app ordering experience and Sector 17 location aesthetics.", "budget_estimate": "₹15,000/month"},
            {"name": "Campus Rush", "channel": "University Ambassadors + WhatsApp", "description": "5 campus reps at Panjab University with custom discount codes and weekly giveaways.", "budget_estimate": "₹8,000/month"},
            {"name": "Corporate Coffee Club", "channel": "Email + LinkedIn", "description": "B2B outreach to HR managers in Mohali IT Park for bulk morning orders and corporate accounts.", "budget_estimate": "₹5,000/month"}
        ],
        "channels": [
            {"name": "Instagram & Reels", "allocation_percent": 45, "rationale": "Primary brand-building and awareness channel for 18-35 demographic"},
            {"name": "Google Search Ads", "allocation_percent": 25, "rationale": "High-intent local searches for 'coffee near Sector 17'"},
            {"name": "Swiggy/Zomato Promotions", "allocation_percent": 20, "rationale": "Discovery channel with first-month discounted delivery deal"},
            {"name": "Referral Program", "allocation_percent": 10, "rationale": "In-app referral rewards to drive organic growth"}
        ],
        "content_ideas": [
            "Day-in-the-life of a BeanRush barista (Instagram Reels)",
            "Chandigarh Startup Culture content — coffee and code series",
            "Behind-the-bean: sourcing from Coorg coffee estates",
            "App tutorial: how to order in 10 seconds flat"
        ]
    },
    "sales": {
        "pricing_strategy": "Premium pricing 15-20% above CCD/Barista but 10% below Third Wave Coffee. Espresso drinks anchored at ₹180-280. Corporate bulk pricing at ₹120/cup with minimum 20-cup orders. Subscription bean boxes at ₹1,200/month.",
        "sales_channels": [
            "Walk-in café (primary — 60% of revenue)",
            "BeanRush mobile app pre-orders (30% of revenue)",
            "Swiggy/Zomato delivery (10% of revenue, grows to 20% by Year 2)"
        ],
        "customer_acquisition": [
            "Free first drink with app download during launch month",
            "Loyalty punch card: 10 purchases = 1 free drink",
            "Corporate account setup with net-30 invoicing",
            "Student discount: 15% off with valid university ID"
        ],
        "sales_targets": [
            {"period": "Month 1", "target": "500 customers", "metric": "Unique app downloads + walk-ins"},
            {"period": "Month 3", "target": "₹1.5L monthly revenue", "metric": "Monthly Revenue"},
            {"period": "Month 6", "target": "5 corporate accounts", "metric": "B2B contracts signed"}
        ]
    },
    "execution_plan": [
        {"week": "Week 1–2", "action": "Register business entity (LLP), sign Sector 17 lease, open business bank account", "owner": "CEO"},
        {"week": "Week 3–4", "action": "Procure espresso machines, begin interior fit-out, hire Head Barista", "owner": "Operations"},
        {"week": "Month 2", "action": "Train 3 baristas, develop BeanRush app MVP, run soft launch with 100 beta users", "owner": "Operations & Tech"},
        {"week": "Month 3", "action": "Grand opening event, activate Instagram campaign, begin corporate outreach", "owner": "Marketing & Sales"},
        {"week": "Month 4–6", "action": "Expand menu, onboard first 3 corporate accounts, add Swiggy/Zomato listing", "owner": "Sales"}
    ],
    "recommendations": [
        "Prioritize the mobile app as the primary brand differentiator — no Chandigarh competitor offers zero-wait ordering",
        "Negotiate a rent-free first 3 months with the Sector 17 landlord given the high fit-out investment",
        "Lock in a fixed-price Arabica supply contract with a Coorg estate for 12 months to hedge against price volatility"
    ],
    "next_steps": [
        "Register BeanRush Coffee as a Limited Liability Partnership this week",
        "Contact Sector 17 Plaza commercial leasing agent for unit availability",
        "Shortlist 3 local app development agencies for mobile ordering app",
        "Begin Instagram page creation and pre-launch teaser content immediately"
    ]
}


# ─── LLM Callers ─────────────────────────────────────────────────────────────

async def _call_gemini(system: str, user: str) -> str:
    """Call Google Gemini and return raw text response (async)."""
    import google.generativeai as genai
    genai.configure(api_key=LLM_API_KEY)
    model = genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        system_instruction=system,
        generation_config=genai.GenerationConfig(
            temperature=0.7,
            max_output_tokens=2048,
            response_mime_type="application/json",
        ),
    )
    response = await model.generate_content_async(user)
    return response.text


async def _call_openai(system: str, user: str) -> str:
    """Call OpenAI and return raw text response."""
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=LLM_API_KEY)
    completion = await client.chat.completions.create(
        model=OPENAI_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.7,
        max_tokens=2048,
    )
    return completion.choices[0].message.content


async def _call_groq(system: str, user: str) -> str:
    """Call Groq and return raw text response."""
    from groq import AsyncGroq
    client = AsyncGroq(api_key=LLM_API_KEY)
    completion = await client.chat.completions.create(
        model=GROQ_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.7,
        max_tokens=2048,
    )
    return completion.choices[0].message.content


async def _call_llm(system: str, user: str) -> str:
    """Dispatch to the configured LLM provider."""
    if LLM_PROVIDER == "openai":
        return await _call_openai(system, user)
    elif LLM_PROVIDER == "groq":
        return await _call_groq(system, user)
    else:
        return await _call_gemini(system, user)


# ─── Validation & Repair ─────────────────────────────────────────────────────

def _parse_and_validate(raw: str) -> CompanyOSResponse:
    """Parse JSON and validate against Pydantic schema."""
    # Strip markdown fences if model ignored the instruction
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

    data = json.loads(cleaned)
    return CompanyOSResponse(**data)


REPAIR_PROMPT = """The JSON you returned failed schema validation. 
Error: {error}

Original response:
{original}

Return ONLY the corrected JSON matching the required schema exactly. No prose."""


# ─── Main Orchestrator ───────────────────────────────────────────────────────

async def run_orchestrator(req: InitiativeRequest) -> CompanyOSResponse:
    """
    Main entry point. Returns a validated CompanyOSResponse.
    Uses 1 LLM call. Falls back to demo data ONLY when DEMO_MODE=true.
    In live mode, errors are raised — never silently replaced with BeanRush.
    """
    logger.info(f"[CompanyOS Backend] Orchestration started")
    logger.info(f"[CompanyOS Backend] Company: {req.company.name}")
    logger.info(f"[CompanyOS Backend] Industry: {req.company.industry}")
    logger.info(f"[CompanyOS Backend] Objective: {req.objective[:120]}")
    logger.info(f"[CompanyOS Backend] DEMO_MODE={DEMO_MODE}")

    # Demo mode — no LLM call (explicit opt-in only)
    if DEMO_MODE:
        logger.info("[CompanyOS Backend] DEMO_MODE=true — returning pre-built BeanRush Coffee response")
        return CompanyOSResponse(**DEMO_RESPONSE)

    # ── LIVE MODE: Gemini/OpenAI must be called ──────────────────────────
    if not LLM_API_KEY or LLM_API_KEY == "your_api_key_here":
        error_msg = (
            "No LLM API key configured. Set LLM_API_KEY in your .env file. "
            "Or set DEMO_MODE=true to use the BeanRush Coffee demo."
        )
        logger.error(f"[CompanyOS Backend] {error_msg}")
        raise RuntimeError(error_msg)

    # PRIMARY LLM CALL
    logger.info(f"[CompanyOS Backend] Calling Gemini (provider={LLM_PROVIDER}, model={GEMINI_MODEL})")
    user_prompt = build_user_prompt(req)

    try:
        raw = await _call_llm(SYSTEM_PROMPT, user_prompt)
        logger.info(f"[CompanyOS Backend] Gemini response received ({len(raw)} chars)")
    except Exception as e:
        error_msg = f"LLM call failed: {type(e).__name__}: {e}"
        logger.error(f"[CompanyOS Backend] {error_msg}")
        raise RuntimeError(error_msg)

    # Validate
    try:
        result = _parse_and_validate(raw)
        logger.info(f"[CompanyOS Backend] Parsed CompanyOS result — initiative: {result.initiative.name}")
        return result
    except Exception as e:
        validation_error = str(e)
        logger.warning(f"[CompanyOS Backend] Validation failed: {validation_error} — attempting repair call")

    # REPAIR CALL (optional second call)
    try:
        repair_user = REPAIR_PROMPT.format(error=validation_error, original=raw[:3000])
        raw2 = await _call_llm(SYSTEM_PROMPT, repair_user)
        result = _parse_and_validate(raw2)
        logger.info(f"[CompanyOS Backend] Repair successful — initiative: {result.initiative.name}")
        return result
    except Exception as e2:
        error_msg = f"LLM response failed validation even after repair: {type(e2).__name__}: {e2}"
        logger.error(f"[CompanyOS Backend] {error_msg}")
        raise RuntimeError(error_msg)


# ─── Follow-up Handler ───────────────────────────────────────────────────────

async def run_followup(question: str, initiative_data: dict) -> str:
    """
    Answer a follow-up question using stored context. One small LLM call.
    Does NOT regenerate the initiative plan.
    """
    logger.info(f"Follow-up question: {question[:80]}")

    if DEMO_MODE or not LLM_API_KEY or LLM_API_KEY == "your_api_key_here":
        return _demo_followup(question, initiative_data)

    # Build minimal context (just summary + relevant numbers)
    context = f"""
Initiative: {initiative_data.get('initiative', {}).get('name', '')}
Objective: {initiative_data.get('initiative', {}).get('objective', '')}
Executive Summary: {initiative_data.get('executive_summary', '')[:500]}
Finance: Initial investment ₹{initiative_data.get('finance', {}).get('initial_investment', 0):,.0f}, Monthly revenue ₹{initiative_data.get('finance', {}).get('monthly_revenue', 0):,.0f}, Break-even {initiative_data.get('finance', {}).get('break_even_estimate', '')}
Marketing: {initiative_data.get('marketing', {}).get('brand_positioning', '')}
Sales: {initiative_data.get('sales', {}).get('pricing_strategy', '')}
""".strip()

    user_prompt = build_followup_prompt(question, context)

    try:
        answer = await _call_llm(FOLLOWUP_SYSTEM_PROMPT, user_prompt)
        # Clean up if model returns JSON accidentally
        if answer.strip().startswith("{"):
            data = json.loads(answer)
            answer = data.get("answer", str(data))
        return answer.strip()
    except Exception as e:
        logger.error(f"Follow-up LLM call failed: {e}")
        raise RuntimeError(f"Follow-up LLM call failed: {e}")


def _demo_followup(question: str, data: dict) -> str:
    """Simple keyword-based demo follow-up responses."""
    q = question.lower()
    fin = data.get("finance", {})
    if any(w in q for w in ["price", "pricing", "cost", "charge"]):
        return data.get("sales", {}).get("pricing_strategy", "Pricing is set at a premium to competitors while remaining accessible to the target market.")
    if any(w in q for w in ["revenue", "money", "earn", "income"]):
        return f"Projected monthly revenue is ₹{fin.get('monthly_revenue', 0):,.0f} once at steady state, with break-even expected at {fin.get('break_even_estimate', 'Month 8')}."
    if any(w in q for w in ["invest", "capital", "fund", "₹", "rupee"]):
        return f"Total initial investment required is ₹{fin.get('initial_investment', 0):,.0f}, covering equipment, fit-out, working capital, and the app."
    if any(w in q for w in ["market", "customer", "target", "who"]):
        customers = data.get("research", {}).get("target_customers", [])
        if customers:
            return f"Primary customers are {customers[0].get('segment', '')}: {customers[0].get('description', '')}."
    if any(w in q for w in ["risk", "challenge", "problem"]):
        risks = data.get("research", {}).get("risks", [])
        return "Key risks include: " + "; ".join(risks[:2]) + "." if risks else "Key risks have been identified and mitigation strategies are included in the plan."
    return "Based on the CompanyOS analysis, this initiative is well-positioned for the identified market opportunity. Review the detailed sections for specific insights."
