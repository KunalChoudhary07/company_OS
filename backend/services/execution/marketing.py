import logging
import uuid
from typing import Any, Dict, Optional, Tuple

import httpx

logger = logging.getLogger("companyos.execution.marketing")

META_GRAPH_BASE = "https://graph.facebook.com/v19.0"
REQUEST_TIMEOUT = 20


class CampaignExecutionProvider:
    """Abstract interface for campaign execution."""
    def validate_campaign(self, campaign_data: dict) -> Tuple[bool, str]:
        raise NotImplementedError

    async def create_campaign(self, campaign_data: dict) -> dict:
        raise NotImplementedError


class SandboxCampaignProvider(CampaignExecutionProvider):
    """Sandbox implementation that mimics a real ads API without spending money."""

    def validate_campaign(self, campaign_data: dict) -> Tuple[bool, str]:
        if not campaign_data:
            return False, "Campaign data is empty."

        c = campaign_data.get("campaign", {})
        if not c.get("name"):
            return False, "Campaign name is missing."
        if not c.get("objective"):
            return False, "Campaign objective is missing."
        if c.get("recommendedBudget", 0) <= 0:
            return False, "Campaign budget must be greater than zero."
        if not c.get("channels"):
            return False, "At least one channel is required."

        # In a real integration, we'd also validate ad assets, audience size, etc.
        return True, "Valid"

    async def create_campaign(self, campaign_data: dict) -> dict:
        """Executes the sandbox campaign and returns the result."""
        sandbox_id = f"sandbox-campaign-{uuid.uuid4().hex[:8]}"

        c = campaign_data.get("campaign", {})

        return {
            "mode": "SANDBOX",
            "status": "EXECUTED",
            "campaignId": sandbox_id,
            "budget": c.get("recommendedBudget"),
            "channels": c.get("channels")
        }


# Meta objective strings changed in Graph API v19+ ("outcome-based" objectives).
# We map CompanyOS's freeform campaign objective text to the closest valid value.
_META_OBJECTIVE_MAP = {
    "awareness": "OUTCOME_AWARENESS",
    "brand awareness": "OUTCOME_AWARENESS",
    "traffic": "OUTCOME_TRAFFIC",
    "engagement": "OUTCOME_ENGAGEMENT",
    "lead generation": "OUTCOME_LEADS",
    "leads": "OUTCOME_LEADS",
    "sales": "OUTCOME_SALES",
    "conversions": "OUTCOME_SALES",
    "app promotion": "OUTCOME_APP_PROMOTION",
}


def _map_meta_objective(objective_text: str) -> str:
    text = (objective_text or "").lower()
    for key, value in _META_OBJECTIVE_MAP.items():
        if key in text:
            return value
    return "OUTCOME_AWARENESS"  # safe, low-risk default


class MetaAdsProvider(CampaignExecutionProvider):
    """
    Live integration with the Meta (Facebook/Instagram) Marketing API.

    SAFETY: Every campaign and ad set created here is forced to status=PAUSED.
    Nothing spends money until the founder reviews it in Meta Ads Manager and
    manually switches it to ACTIVE. We never activate a campaign automatically.

    Requires (all provided by the user at request time, never stored server-side):
      - access_token: a Meta access token with the ads_management permission
      - ad_account_id: the numeric ad account id, with or without the "act_" prefix
    """

    def __init__(self, access_token: str, ad_account_id: str):
        if not access_token or not ad_account_id:
            raise ValueError("Meta access token and ad account ID are required.")
        self.access_token = access_token
        self.ad_account_id = ad_account_id if ad_account_id.startswith("act_") else f"act_{ad_account_id}"

    def validate_campaign(self, campaign_data: dict) -> Tuple[bool, str]:
        if not campaign_data:
            return False, "Campaign data is empty."

        c = campaign_data.get("campaign", {})
        if not c.get("name"):
            return False, "Campaign name is missing."
        if not c.get("objective"):
            return False, "Campaign objective is missing."
        if c.get("recommendedBudget", 0) <= 0:
            return False, "Campaign budget must be greater than zero."
        if not c.get("channels"):
            return False, "At least one channel is required."

        return True, "Valid"

    async def _graph_post(self, client: httpx.AsyncClient, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        payload = {**payload, "access_token": self.access_token}
        resp = await client.post(f"{META_GRAPH_BASE}/{path}", data=payload, timeout=REQUEST_TIMEOUT)
        data = resp.json()
        if resp.status_code >= 400:
            err = data.get("error", {})
            message = err.get("message", f"Meta API error (HTTP {resp.status_code})")
            raise RuntimeError(message)
        return data

    async def create_campaign(self, campaign_data: dict) -> dict:
        """
        Creates a real Campaign + Ad Set on Meta, both forced to PAUSED.
        Does NOT create ad creatives/ads yet — that requires a connected Facebook
        Page and media assets, which is a follow-up step the founder completes
        directly in Ads Manager before activating.
        """
        c = campaign_data.get("campaign", {})
        audience = c.get("targetAudience", {})

        name = c.get("name", "CompanyOS Campaign")
        objective = _map_meta_objective(c.get("objective", ""))
        total_budget = float(c.get("recommendedBudget", 0) or 0)
        daily_budget = float(c.get("dailyBudget", 0) or (total_budget / max(c.get("durationDays", 1) or 1, 1)))
        # Meta budgets are in the smallest currency unit (e.g. cents/paise) as integers.
        daily_budget_minor_units = max(int(round(daily_budget * 100)), 100)

        async with httpx.AsyncClient() as client:
            try:
                campaign_resp = await self._graph_post(
                    client,
                    f"{self.ad_account_id}/campaigns",
                    {
                        "name": name,
                        "objective": objective,
                        "status": "PAUSED",
                        "special_ad_categories": "[]",
                    },
                )
                campaign_id = campaign_resp.get("id")

                adset_resp = await self._graph_post(
                    client,
                    f"{self.ad_account_id}/adsets",
                    {
                        "name": f"{name} — Ad Set",
                        "campaign_id": campaign_id,
                        "daily_budget": daily_budget_minor_units,
                        "billing_event": "IMPRESSIONS",
                        "optimization_goal": "REACH" if objective == "OUTCOME_AWARENESS" else "LINK_CLICKS",
                        "status": "PAUSED",
                        # Minimal broad targeting; the founder should refine this in Ads Manager
                        # before activating. We deliberately keep this permissive rather than
                        # guessing detailed interest/location targeting on the user's behalf.
                        "targeting": '{"geo_locations":{"countries":["US"]}}',
                    },
                )
                adset_id = adset_resp.get("id")
            except RuntimeError as e:
                logger.error(f"Meta campaign creation failed: {e}")
                raise

        return {
            "mode": "META_LIVE",
            "status": "PAUSED",
            "campaignId": campaign_id,
            "adSetId": adset_id,
            "budget": total_budget,
            "channels": c.get("channels"),
            "adsManagerUrl": f"https://adsmanager.facebook.com/adsmanager/manage/campaigns?act={self.ad_account_id.replace('act_', '')}",
            "note": "Campaign and ad set were created in PAUSED status. Review targeting, budget, and add creatives in Meta Ads Manager, then activate manually when ready.",
        }


# Provider factory. `credentials` is only required/used for MODE == "META_LIVE".
def get_campaign_provider(mode: str = "SANDBOX", credentials: Optional[Dict[str, str]] = None) -> CampaignExecutionProvider:
    if mode == "SANDBOX":
        return SandboxCampaignProvider()
    if mode == "META_LIVE":
        credentials = credentials or {}
        return MetaAdsProvider(
            access_token=credentials.get("accessToken", ""),
            ad_account_id=credentials.get("adAccountId", ""),
        )
    raise ValueError(f"Unknown execution mode: {mode}")
