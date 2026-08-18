"""
Business intelligence tools for the Decision-Memo agent entry point.

This file is self-contained — it does not import from other workshop modules
so it can be deployed as part of the AgentCore container image.
"""

from strands import tool


COMPANIES = {
    "novacart": {
        "company": "NovaCart",
        "industry": "e-commerce",
        "active_users": 2_000_000,
        "annual_churn_rate_pct": 22,
        "average_order_value_usd": 85.00,
        "customer_lifetime_value_usd": 340.00,
        "annual_revenue_usd": 142_000_000,
        "subscription_revenue_usd": 0,
        "top_spender_segment_pct": 10,
        "top_spender_avg_order_value_usd": 210.00,
        "q1_survey_premium_interest_pct": 38,
    }
}

BENCHMARKS = {
    "e-commerce": {
        "avg_annual_churn_rate_pct": 25,
        "avg_customer_lifetime_value_usd": 290.00,
        "subscription_adoption_rate_pct": 31,
        "avg_subscription_price_usd": 15.50,
        "premium_tier_adoption_top_spenders_pct": 68,
        "clv_lift_with_subscription_pct": "20-35",
        "avg_time_to_subscription_profitability_months": 9,
        "key_insight": (
            "E-commerce brands with subscription tiers see 20-35% higher CLV. "
            "Top-spender segments adopt at 2x the base rate."
        ),
    }
}

COMPETITORS = {
    "shopmart": {
        "tier_name": "ShopMart Plus",
        "launched": "Q2 2024",
        "monthly_price_usd": 16.99,
        "pilot_approach": "5% of users for 90 days before full rollout",
        "adoption_rate_6mo_pct": 28,
        "clv_lift_pct": 22,
        "time_to_profitability_months": 8,
        "key_insight": "5% pilot + validate unit economics before scaling → 28% adoption in 6 months.",
    },
    "primestore": {
        "tier_name": "PrimeStore Unlimited",
        "launched": "Q4 2023",
        "monthly_price_usd": 12.99,
        "pilot_approach": "Full launch to all users with 30-day free trial",
        "adoption_rate_6mo_pct": 19,
        "clv_lift_pct": 14,
        "time_to_profitability_months": 14,
        "key_insight": "Full launch + free trial → 40% churned post-trial. Slower ROI.",
    },
}


@tool
def get_company_data(company_name: str) -> str:
    """Get current financial and operational data for a company.

    Args:
        company_name: The company name to look up (e.g. 'NovaCart')
    """
    key = company_name.lower().strip()
    data = COMPANIES.get(key)
    if not data:
        return f"No data found for '{company_name}'. Available: {', '.join(COMPANIES)}"
    return (
        f"Company: {data['company']} ({data['industry']})"
        f"\nActive users: {data['active_users']:,}"
        f"\nAnnual churn rate: {data['annual_churn_rate_pct']}%"
        f"\nAverage order value: ${data['average_order_value_usd']:.2f}"
        f"\nCustomer Lifetime Value (CLV): ${data['customer_lifetime_value_usd']:.2f}"
        f"\nAnnual revenue: ${data['annual_revenue_usd']:,.0f}"
        f"\nSubscription revenue: ${data['subscription_revenue_usd']:,.0f}"
        f"\nTop {data['top_spender_segment_pct']}% spenders avg order: ${data['top_spender_avg_order_value_usd']:.2f}"
        f"\nQ1 survey — premium interest (top spenders): {data['q1_survey_premium_interest_pct']}%"
    )


@tool
def get_market_benchmarks(industry: str) -> str:
    """Get industry benchmarks and performance data for a given market sector.

    Args:
        industry: The industry sector (e.g. 'e-commerce')
    """
    key = industry.lower().strip()
    data = BENCHMARKS.get(key)
    if not data:
        return f"No benchmarks found for '{industry}'. Available: {', '.join(BENCHMARKS)}"
    return (
        f"Industry benchmarks: {key}"
        f"\nAvg annual churn rate: {data['avg_annual_churn_rate_pct']}%"
        f"\nAvg CLV: ${data['avg_customer_lifetime_value_usd']:.2f}"
        f"\nSubscription adoption rate: {data['subscription_adoption_rate_pct']}%"
        f"\nAvg subscription price: ${data['avg_subscription_price_usd']:.2f}/mo"
        f"\nPremium tier adoption (top spenders): {data['premium_tier_adoption_top_spenders_pct']}%"
        f"\nCLV lift with subscription: +{data['clv_lift_with_subscription_pct']}%"
        f"\nKey insight: {data['key_insight']}"
    )


@tool
def get_competitor_data(competitor_name: str) -> str:
    """Get information about a competitor's premium subscription tier.

    Args:
        competitor_name: The competitor name (e.g. 'shopmart', 'primestore')
    """
    key = competitor_name.lower().strip()
    data = COMPETITORS.get(key)
    if not data:
        return f"No data found for '{competitor_name}'. Available: {', '.join(COMPETITORS)}"
    return (
        f"Tier: {data['tier_name']} (launched {data['launched']})"
        f"\nPrice: ${data['monthly_price_usd']:.2f}/mo"
        f"\nPilot approach: {data['pilot_approach']}"
        f"\n6-month adoption rate: {data['adoption_rate_6mo_pct']}%"
        f"\nCLV lift observed: +{data['clv_lift_pct']}%"
        f"\nTime to profitability: {data['time_to_profitability_months']} months"
        f"\nKey insight: {data['key_insight']}"
    )
