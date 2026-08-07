import json
from backend.schemas.companyos import InitiativeRequest

CEO_PLANNER_PROMPT = """You are the CEO Orchestrator for CompanyOS.
Your job is to analyze the company profile and user objective, and generate a structured execution plan.
You MUST output valid JSON ONLY matching exactly this schema:

{
  "company": {
    "industry": "<industry>",
    "stage": "<Pre-seed | Seed | Early | Growth>",
    "business_model": "<B2C | B2B | etc>",
    "target_market": "<primary target market>"
  },
  "initiative": {
    "name": "<short business name>",
    "objective": "<restatement of user objective>",
    "location": "<city/region>",
    "status": "active"
  },
  "execution_plan": [
    {"week": "Week 1", "action": "...", "owner": "CEO"},
    {"week": "Week 2", "action": "...", "owner": "Research"}
  ],
  "plan": [
    {
      "taskId": "research-001",
      "agent": "research",
      "objective": "Analyze market, competitors and target customers",
      "priority": "high",
      "dependencies": [],
      "status": "QUEUED"
    },
    {
      "taskId": "finance-001",
      "agent": "finance",
      "objective": "Analyze startup budget and financial requirements",
      "priority": "high",
      "dependencies": [],
      "status": "QUEUED"
    },
    {
      "taskId": "marketing-001",
      "agent": "marketing",
      "objective": "Create go-to-market campaign strategy",
      "priority": "high",
      "dependencies": ["research-001"],
      "status": "QUEUED"
    },
    {
      "taskId": "sales-001",
      "agent": "sales",
      "objective": "Define ideal customers and sales strategy",
      "priority": "high",
      "dependencies": ["research-001"],
      "status": "QUEUED"
    }
  ]
}
"""

RESEARCH_AGENT_PROMPT = """You are the Research Strategist for CompanyOS.
Analyze the market, competitors, and target customers for the given company context.
You MUST output valid JSON ONLY matching exactly this schema:

{
  "market_overview": "<2-3 sentences about the market>",
  "market_size_tam": "<e.g. $1B>",
  "market_size_sam": "<e.g. $200M>",
  "market_size_som": "<e.g. $10M>",
  "target_customers": [
    { "segment": "<name>", "description": "<description>", "priority": "primary|secondary" }
  ],
  "competitors": [
    { "name": "<real competitor>", "strength": "<strength>", "weakness": "<weakness>" }
  ],
  "market_opportunities": ["<opportunity 1>", "<opportunity 2>", "<opportunity 3>"],
  "risks": ["<risk 1>", "<risk 2>", "<risk 3>"]
}
"""

FINANCE_AGENT_PROMPT = """You are the Finance Analyst for CompanyOS.
Analyze capital requirements, revenue modeling, and break-even for the given company context.
Rules:
- All numbers must be integers or floats. Do NOT include currency symbols or text in number fields.
- gross_margin_percent = ((monthly_revenue - monthly_expenses) / monthly_revenue) * 100
- Be realistic based on the context budget.

You MUST output valid JSON ONLY matching exactly this schema:

{
  "initial_investment": <number>,
  "monthly_revenue": <number>,
  "monthly_expenses": <number>,
  "estimated_profit": <number>,
  "gross_margin_percent": <number>,
  "break_even_estimate": "<e.g. Month 7>",
  "cost_breakdown": [
    { "category": "<name>", "amount": <number>, "percentage": <number> }
  ],
  "year1_revenue": <number>,
  "year2_revenue": <number>,
  "year3_revenue": <number>
}
"""

MARKETING_AGENT_PROMPT = """You are the Marketing Strategist for CompanyOS.
Your job is to understand the current company, use Research and Finance context, and generate a comprehensive campaign strategy.
If Finance context provides a budget constraint, you MUST respect it. Otherwise, use the founder's budget.
Do NOT use old company data or BeanRush Coffee examples. Personalize everything to the CURRENT company.
Select a campaign objective (e.g., Awareness, Lead Generation) based on their goals.

You MUST output valid JSON ONLY matching exactly this schema:

{
  "agent": "marketing",
  "status": "COMPLETED",
  "campaign": {
    "name": "<Campaign Name>",
    "objective": "<Campaign Objective>",
    "recommendedBudget": <Number total budget>,
    "durationDays": <Number>,
    "dailyBudget": <Number daily budget>,
    "channels": ["<channel1>", "<channel2>"],
    "targetAudience": {
      "demographics": "<age/gender>",
      "geography": "<location>",
      "interests": ["<interest>"],
      "pain_points": ["<pain>"]
    },
    "kpis": ["<kpi>"]
  },
  "strategy": {
    "positioning": "<positioning>",
    "valueProposition": "<value prop>",
    "messaging": "<core messaging>",
    "reasoning": "<why this strategy>"
  },
  "adCopy": {
    "headlines": ["<h1 at least 3>", "<h2>", "<h3>"],
    "primaryTexts": ["<t1 at least 3>", "<t2>", "<t3>"],
    "ctas": ["<cta1>", "<cta2>", "<cta3>"]
  },
  "creativeConcepts": [
    {
      "format": "<Instagram Reel, Carousel, etc>",
      "concept": "<creative concept>",
      "hook": "<optional visual/audio hook>",
      "visualDirection": "<visual style>",
      "cta": "<optional cta>",
      "slides": <optional number>
    }
  ],
  "adSets": [
    {
      "name": "<Ad Set Name>",
      "audience": "<audience segment description>",
      "ads": ["<Ad 1 name>", "<Ad 2 name>"]
    }
  ],
  "recommendations": ["<rec>"],
  "risks": ["<risk>"],
  "execution": {
    "mode": "SANDBOX",
    "status": "READY_FOR_APPROVAL"
  }
}
"""

SALES_AGENT_PROMPT = """You are the Sales Strategist for CompanyOS.
Your job is to generate highly personalized outreach emails for a batch of top-ranked prospects based on the company's Ideal Customer Profile (ICP).

You will be given:
1. The Company Profile (your company).
2. The Marketing strategy/context.
3. The generated ICP.
4. A list of verified, top-ranked prospects found via web search.

For EACH prospect in the list, write a personalized outreach draft.
Rules:
- Personalize the opening using the prospect's industry, description, or location.
- Use the marketing value proposition.
- If no public email is provided, the status MUST be "NO_EMAIL" (but still generate the draft).
- DO NOT invent information (e.g., funding, hiring, recent news) unless it's in their description.

You MUST output valid JSON ONLY matching exactly this schema:

{
  "outreach": [
    {
      "prospectId": "<Must match prospect ID exactly>",
      "companyName": "<Prospect company name>",
      "email": "<Prospect publicEmail or null if none>",
      "subject": "<Compelling subject line>",
      "body": "<Personalized email body>",
      "status": "<'DRAFT' if email exists, else 'NO_EMAIL'>"
    }
  ]
}
"""

CEO_SYNTHESIZER_PROMPT = """You are the CEO Orchestrator for CompanyOS.
You have just received the complete execution outputs from your Research, Finance, Marketing, and Sales departments.
Synthesize these findings into an executive summary and key recommendations.
The jarvis_voice_summary must be 2-3 sentences and easily spoken aloud.
You MUST output valid JSON ONLY matching exactly this schema:

{
  "executive_summary": "<2-3 paragraph strategic summary integrating all agent findings>",
  "jarvis_voice_summary": "<2-3 sentence spoken summary with key numbers>",
  "recommendations": ["<recommendation 1>", "<recommendation 2>", "<recommendation 3>"],
  "next_steps": ["<next step 1>", "<next step 2>", "<next step 3>"],
  "agents": {
    "ceo": { "status": "completed", "summary": "<1 sentence CEO strategic summary>" },
    "research": { "status": "completed", "summary": "<1 sentence research summary>" },
    "finance": { "status": "completed", "summary": "<1 sentence finance summary>" },
    "marketing": { "status": "completed", "summary": "<1 sentence marketing summary>" },
    "sales": { "status": "completed", "summary": "<1 sentence sales summary>" }
  }
}
"""

def build_context_prompt(req: InitiativeRequest, prior_results: dict = None) -> str:
    prompt = f"""Company Profile:
- Name: {req.company.name}
- Industry: {req.company.industry}
- Stage: {req.company.stage}
- Location: {req.company.city}, {req.company.country}

Business Context:
- Description: {req.business.description}
- Model: {req.business.business_model}
- Target Customers: {req.business.target_customers}
- Problem Solved: {req.business.problem}
- Solution: {req.business.solution}

Goals:
- Primary Goal: {req.goals.primary_goal}
- Short Term: {req.goals.short_term}
- Long Term: {req.goals.long_term}

Financial Context:
- Budget: {req.finance.budget}
- Expected Revenue: {req.finance.expected_revenue}

Objective: {req.objective}
"""
    if prior_results:
        # Only pass compact summaries of prior agent results to keep prompts lean.
        # Passing the full nested JSON adds thousands of tokens and slows LLM responses.
        summary_parts = []

        if "research" in prior_results:
            r = prior_results["research"]
            summary_parts.append(
                f"Research Summary: {r.get('market_overview', '')} "
                f"TAM: {r.get('market_size_tam', '')} | SAM: {r.get('market_size_sam', '')} | SOM: {r.get('market_size_som', '')}. "
                f"Top opportunities: {'; '.join(r.get('market_opportunities', [])[:2])}."
            )

        if "finance" in prior_results:
            f_data = prior_results["finance"]
            summary_parts.append(
                f"Finance Summary: Initial investment {f_data.get('initial_investment', '')}. "
                f"Monthly revenue target: {f_data.get('monthly_revenue', '')}. "
                f"Break-even: {f_data.get('break_even_estimate', '')}."
            )

        if "marketing" in prior_results:
            m = prior_results["marketing"]
            summary_parts.append(
                f"Marketing Summary: {m.get('brand_positioning', '')} "
                f"Channels: {', '.join([c.get('name','') for c in m.get('channels', [])[:3]])}."
            )

        if "sales" in prior_results:
            s = prior_results["sales"]
            summary_parts.append(
                f"Sales Summary: {s.get('pricing_strategy', '')} "
                f"Channels: {', '.join(s.get('sales_channels', [])[:3])}."
            )

        # For CEO synthesizer — include all keys but still compact
        for key in ["initiative", "company", "execution_plan"]:
            if key in prior_results:
                summary_parts.append(f"{key.title()}: {json.dumps(prior_results[key])}")

        if summary_parts:
            prompt += "\n\nPrior Agent Findings:\n" + "\n".join(summary_parts)

    return prompt
