import io
import math
import logging
import json
import pandas as pd
from typing import Dict, Any, List, Optional
from sklearn.linear_model import LinearRegression
import numpy as np

from backend.schemas.companyos import InitiativeRequest
from backend.services.orchestrator import _call_llm, _parse_and_validate
from backend.prompts.agents import build_context_prompt

logger = logging.getLogger("companyos.agents.finance")

FINANCE_INTERPRETER_PROMPT = """You are the Finance Strategist for CompanyOS.
The data science team has already processed the financial data and calculated the metrics.
Your job is to interpret these numbers, explain what they mean for the business, identify risks/opportunities, and provide strategic recommendations.

Rules:
- Do NOT recalculate numbers.
- Do NOT include raw numbers unless highlighting a specific trend.
- Focus on insights: what do the margins, growth rates, and anomalies mean?
- Be direct, professional, and strategic.

You MUST output valid JSON ONLY matching exactly this schema:
{
  "summary": "<2-3 sentence strategic summary of financial health>",
  "findings": ["<insight 1>", "<insight 2>"],
  "risks": ["<risk 1>", "<risk 2>"],
  "opportunities": ["<opportunity 1>", "<opportunity 2>"],
  "recommendations": ["<recommendation 1>", "<recommendation 2>"]
}
"""

def _map_columns(df: pd.DataFrame) -> Dict[str, str]:
    """Fuzzy mapping of expected columns to actual CSV columns."""
    mapping = {}
    cols = [str(c).lower().strip() for c in df.columns]
    
    # Revenue aliases
    for c in cols:
        if c in ['revenue', 'sales', 'income', 'total_revenue']:
            mapping['revenue'] = df.columns[cols.index(c)]
            break
            
    # Expense aliases
    for c in cols:
        if c in ['expenses', 'cost', 'total_expenses']:
            mapping['expenses'] = df.columns[cols.index(c)]
            break
            
    # Marketing aliases
    for c in cols:
        if c in ['marketing_spend', 'marketing', 'ad_spend']:
            mapping['marketing_spend'] = df.columns[cols.index(c)]
            break
            
    # Customer aliases
    for c in cols:
        if c in ['customers', 'customer_count']:
            mapping['customers'] = df.columns[cols.index(c)]
            break
            
    # Orders aliases
    for c in cols:
        if c in ['orders', 'order_count']:
            mapping['orders'] = df.columns[cols.index(c)]
            break
            
    # Date aliases
    for c in cols:
        if c in ['date', 'month', 'period']:
            mapping['date'] = df.columns[cols.index(c)]
            break
            
    return mapping

def _calculate_growth(current: float, previous: float) -> float:
    if previous == 0:
        return 0.0
    return round(((current - previous) / previous) * 100, 2)

async def run_finance_agent(req: InitiativeRequest, csv_content: str, emit_status: callable) -> Dict[str, Any]:
    """
    Parses CSV, calculates financial metrics, runs basic forecasting, 
    and asks Groq to interpret the results.
    """
    await emit_status("Parsing financial dataset...")
    
    result = {
        "agent": "finance",
        "status": "COMPLETED",
        "metrics": {},
        "monthlyData": [],
        "trends": [],
        "anomalies": [],
        "forecast": {"available": False, "nextMonthRevenue": None, "nextThreeMonths": []},
        "aiInsights": {},
        "dataQuality": {"rows": 0, "validRows": 0, "invalidRows": 0, "missingColumns": []}
    }
    
    if not csv_content or not csv_content.strip():
        result["status"] = "FAILED"
        result["dataQuality"]["invalidRows"] = 0
        return result

    try:
        df = pd.read_csv(io.StringIO(csv_content))
    except Exception as e:
        logger.error(f"CSV parsing error: {e}")
        raise ValueError(f"Invalid CSV format: {str(e)}")

    result["dataQuality"]["rows"] = len(df)
    
    # Drop completely empty rows
    df.dropna(how='all', inplace=True)
    result["dataQuality"]["validRows"] = len(df)
    result["dataQuality"]["invalidRows"] = result["dataQuality"]["rows"] - len(df)
    
    if df.empty:
        raise ValueError("CSV contains no valid data rows.")

    # Column Mapping
    col_map = _map_columns(df)
    
    required_cols = ['revenue', 'expenses']
    missing = [c for c in required_cols if c not in col_map]
    if missing:
        result["dataQuality"]["missingColumns"] = missing
        raise ValueError(f"Missing required columns. Could not detect: {', '.join(missing)}")
        
    # Standardize column names in df for easier processing
    rename_dict = {orig: std for std, orig in col_map.items()}
    df.rename(columns=rename_dict, inplace=True)
    
    # Convert numeric columns
    numeric_cols = [c for c in ['revenue', 'expenses', 'marketing_spend', 'customers', 'orders'] if c in df.columns]
    for c in numeric_cols:
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
        
    await emit_status("Calculating financial metrics...")

    # Calculate Totals
    total_rev = df['revenue'].sum()
    total_exp = df['expenses'].sum()
    net_profit = total_rev - total_exp
    margin = (net_profit / total_rev * 100) if total_rev > 0 else 0
    
    mkt_spend = df['marketing_spend'].sum() if 'marketing_spend' in df.columns else 0
    total_cust = df['customers'].sum() if 'customers' in df.columns else 0
    total_orders = df['orders'].sum() if 'orders' in df.columns else 0
    
    result["metrics"].update({
        "totalRevenue": float(total_rev),
        "totalExpenses": float(total_exp),
        "netProfit": float(net_profit),
        "profitMargin": round(float(margin), 2),
        "marketingSpend": float(mkt_spend),
        "averageMonthlyRevenue": float(df['revenue'].mean()),
        "averageMonthlyExpenses": float(df['expenses'].mean()),
    })
    
    if 'orders' in df.columns and total_orders > 0:
        result["metrics"]["averageOrderValue"] = round(float(total_rev / total_orders), 2)
        
    if 'customers' in df.columns and total_cust > 0:
        if 'marketing_spend' in df.columns:
            result["metrics"]["customerAcquisitionCost"] = round(float(mkt_spend / total_cust), 2)
            
    # Process Time Series if Date exists
    if 'date' in df.columns:
        await emit_status("Analyzing monthly trends...")
        try:
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            
            # Monthly grouping
            monthly = df.groupby(df['date'].dt.to_period('M')).sum(numeric_only=True).reset_index()
            monthly['date'] = monthly['date'].astype(str)
            
            # Generate monthlyData for charts
            result["monthlyData"] = monthly.to_dict('records')
            
            if len(monthly) >= 2:
                # Calculate Growth (Last month vs Previous month)
                last = monthly.iloc[-1]
                prev = monthly.iloc[-2]
                
                result["metrics"]["revenueGrowth"] = _calculate_growth(last.get('revenue', 0), prev.get('revenue', 0))
                result["metrics"]["expenseGrowth"] = _calculate_growth(last.get('expenses', 0), prev.get('expenses', 0))
                if 'marketing_spend' in df.columns:
                    result["metrics"]["marketingGrowth"] = _calculate_growth(last.get('marketing_spend', 0), prev.get('marketing_spend', 0))
                
                # Simple Trend Detection
                if result["metrics"]["revenueGrowth"] > 0:
                    result["trends"].append("Revenue is increasing.")
                elif result["metrics"]["revenueGrowth"] < 0:
                    result["trends"].append("Revenue is decreasing.")
                    
                if result["metrics"]["expenseGrowth"] > 0:
                    result["trends"].append("Expenses are increasing.")
                
                # Anomaly Detection (Changes > 30%)
                if abs(result["metrics"]["revenueGrowth"]) > 30:
                    dir_str = "increased" if result["metrics"]["revenueGrowth"] > 0 else "decreased"
                    result["anomalies"].append(f"Revenue {dir_str} unusually by {abs(result['metrics']['revenueGrowth'])}% in the last month.")
                if 'marketing_spend' in df.columns and abs(result["metrics"]["marketingGrowth"]) > 30:
                    dir_str = "increased" if result["metrics"]["marketingGrowth"] > 0 else "decreased"
                    result["anomalies"].append(f"Marketing spend {dir_str} by {abs(result['metrics']['marketingGrowth'])}% recently.")

            # Forecasting (Requires at least 3 data points)
            if len(monthly) >= 3:
                await emit_status("Generating revenue forecast...")
                try:
                    X = np.arange(len(monthly)).reshape(-1, 1)
                    y = monthly['revenue'].values
                    
                    model = LinearRegression()
                    model.fit(X, y)
                    
                    # Predict next 3 months
                    X_future = np.arange(len(monthly), len(monthly) + 3).reshape(-1, 1)
                    predictions = model.predict(X_future)
                    
                    # Prevent negative revenue forecasts
                    predictions = [max(0, float(p)) for p in predictions]
                    
                    result["forecast"] = {
                        "available": True,
                        "nextMonthRevenue": round(predictions[0], 2),
                        "nextThreeMonths": [round(p, 2) for p in predictions]
                    }
                except Exception as e:
                    logger.warning(f"Forecasting failed: {e}")
                    
        except Exception as e:
            logger.warning(f"Time series analysis failed: {e}")
            
    # AI Interpretation
    await emit_status("Requesting AI financial interpretation...")
    try:
        # We send a compact version of the metrics to Groq to save tokens
        compact_summary = {
            "metrics": result["metrics"],
            "trends": result["trends"],
            "anomalies": result["anomalies"],
            "forecast_next_month": result["forecast"]["nextMonthRevenue"]
        }
        
        prompt = build_context_prompt(req)
        prompt += f"\n\nCalculated Financial Data:\n{json.dumps(compact_summary, indent=2)}\n"
        
        raw_llm = await _call_llm(FINANCE_INTERPRETER_PROMPT, prompt)
        
        # Clean JSON markdown if present
        cleaned = raw_llm.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
            
        insights = json.loads(cleaned)
        result["aiInsights"] = insights
    except Exception as e:
        logger.error(f"Groq finance interpretation failed: {e}")
        # We don't fail the whole task if Groq fails; we just return empty insights
        result["aiInsights"] = {
            "summary": "Financial calculations completed, but AI insights are temporarily unavailable.",
            "findings": [],
            "risks": [],
            "opportunities": [],
            "recommendations": []
        }

    return result
