from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ─── Sub-schemas ─────────────────────────────────────────────────────────────

class InitiativeMeta(BaseModel):
    name: str
    objective: str
    location: str
    status: str = "active"


class CompanyInfo(BaseModel):
    industry: str
    stage: str
    business_model: str
    target_market: str


class AgentStatus(BaseModel):
    status: str  # completed | active | queued
    summary: str


class AgentsBlock(BaseModel):
    ceo: AgentStatus
    research: AgentStatus
    finance: AgentStatus
    marketing: AgentStatus
    sales: AgentStatus


class TargetCustomer(BaseModel):
    segment: str
    description: str
    priority: str = "primary"


class Competitor(BaseModel):
    name: str
    strength: str
    weakness: str


class ResearchBlock(BaseModel):
    market_overview: str
    market_size_tam: str = ""
    market_size_sam: str = ""
    market_size_som: str = ""
    target_customers: List[TargetCustomer]
    competitors: List[Competitor]
    market_opportunities: List[str]
    risks: List[str]


class FinanceMetrics(BaseModel):
    totalRevenue: float = 0
    totalExpenses: float = 0
    netProfit: float = 0
    profitMargin: float = 0
    marketingSpend: float = 0
    averageMonthlyRevenue: float = 0
    averageMonthlyExpenses: float = 0
    revenueGrowth: float = 0
    expenseGrowth: float = 0
    marketingGrowth: float = 0
    averageOrderValue: float = 0
    customerAcquisitionCost: Optional[float] = None

class FinanceForecast(BaseModel):
    available: bool = False
    nextMonthRevenue: Optional[float] = None
    nextThreeMonths: List[float] = []

class FinanceAIInsights(BaseModel):
    summary: str = ""
    findings: List[str] = []
    risks: List[str] = []
    opportunities: List[str] = []
    recommendations: List[str] = []

class FinanceDataQuality(BaseModel):
    rows: int = 0
    validRows: int = 0
    invalidRows: int = 0
    missingColumns: List[str] = []

class FinanceBlock(BaseModel):
    agent: str = "finance"
    status: str = "COMPLETED"
    metrics: FinanceMetrics = Field(default_factory=FinanceMetrics)
    monthlyData: List[Dict[str, Any]] = []
    trends: List[str] = []
    anomalies: List[str] = []
    forecast: FinanceForecast = Field(default_factory=FinanceForecast)
    aiInsights: FinanceAIInsights = Field(default_factory=FinanceAIInsights)
    dataQuality: FinanceDataQuality = Field(default_factory=FinanceDataQuality)


class CampaignTargetAudience(BaseModel):
    demographics: str
    geography: str
    interests: List[str]
    pain_points: List[str]

class MarketingCampaign(BaseModel):
    name: str
    objective: str
    recommendedBudget: float
    durationDays: int
    dailyBudget: float
    channels: List[str]
    targetAudience: CampaignTargetAudience
    kpis: List[str]

class MarketingStrategy(BaseModel):
    positioning: str
    valueProposition: str
    messaging: str
    reasoning: str

class AdCopy(BaseModel):
    headlines: List[str]
    primaryTexts: List[str]
    ctas: List[str]

class CreativeConcept(BaseModel):
    format: str
    concept: str
    hook: Optional[str] = ""
    visualDirection: str
    cta: Optional[str] = ""
    slides: Optional[int] = 0

class AdSet(BaseModel):
    name: str
    audience: str
    ads: List[str]

class MarketingExecution(BaseModel):
    mode: str = "SANDBOX"
    status: str = "READY_FOR_APPROVAL"
    campaignId: Optional[str] = None

class MarketingBlock(BaseModel):
    agent: str = "marketing"
    status: str = "COMPLETED"
    campaign: MarketingCampaign
    strategy: MarketingStrategy
    adCopy: AdCopy
    creativeConcepts: List[CreativeConcept]
    adSets: List[AdSet]
    recommendations: List[str]
    risks: List[str]
    execution: MarketingExecution = Field(default_factory=MarketingExecution)


class SalesICP(BaseModel):
    industry: str
    location: str
    companySize: str
    painPoints: List[str]
    buyingSignals: List[str]

class ScoreBreakdown(BaseModel):
    industryFit: int = 0
    locationFit: int = 0
    companyFit: int = 0
    painPointFit: int = 0
    buyingSignals: int = 0

class Prospect(BaseModel):
    id: str
    companyName: str
    website: str
    industry: str
    location: str
    description: str
    score: int
    scoreBreakdown: ScoreBreakdown
    reason: str
    sourceUrls: List[str]
    publicEmail: Optional[str] = None
    # How the email was obtained: "search_snippet" | "website_scrape" | "guessed" | None
    emailSource: Optional[str] = None

class OutreachDraft(BaseModel):
    prospectId: str
    companyName: str
    email: Optional[str] = None
    subject: str
    body: str
    status: str = "DRAFT"

class SalesExecution(BaseModel):
    mode: str = "SANDBOX"
    status: str = "READY_FOR_APPROVAL"

class SalesBlock(BaseModel):
    agent: str = "sales"
    status: str = "COMPLETED"
    icp: SalesICP
    prospects: List[Prospect] = []
    outreach: List[OutreachDraft] = []
    execution: SalesExecution = Field(default_factory=SalesExecution)


class ExecutionStep(BaseModel):
    week: str
    action: str
    owner: str = ""


# ─── Root schema ─────────────────────────────────────────────────────────────

class CompanyOSResponse(BaseModel):
    initiative: InitiativeMeta
    executive_summary: str
    jarvis_voice_summary: str = Field(
        description="Short 2-3 sentence summary for JARVIS to speak aloud"
    )
    company: CompanyInfo
    agents: AgentsBlock
    research: ResearchBlock
    finance: FinanceBlock
    marketing: MarketingBlock
    sales: SalesBlock
    execution_plan: List[ExecutionStep]
    recommendations: List[str]
    next_steps: List[str]


# ─── API request/response wrappers ───────────────────────────────────────────

class CompanyProfileInput(BaseModel):
    name: str
    industry: str
    stage: str
    country: str
    city: str

class BusinessProfileInput(BaseModel):
    description: str
    business_model: str
    target_customers: str
    problem: str
    solution: str

class GoalsProfileInput(BaseModel):
    primary_goal: str
    short_term: str
    long_term: str

class FinanceProfileInput(BaseModel):
    budget: str
    expected_revenue: str
    monthly_budget: str
    funding_status: str

class TeamProfileInput(BaseModel):
    size: str
    founder_role: str
    skills: str
    departments: List[str]

class InitiativeRequest(BaseModel):
    company: CompanyProfileInput
    business: BusinessProfileInput
    goals: GoalsProfileInput
    finance: FinanceProfileInput
    team: TeamProfileInput
    objective: str = Field(min_length=5, max_length=1500)
    csv_data: Optional[str] = None


class FollowUpRequest(BaseModel):
    initiative_id: str
    question: str = Field(min_length=3, max_length=500)


class FollowUpResponse(BaseModel):
    answer: str
    initiative_id: str
