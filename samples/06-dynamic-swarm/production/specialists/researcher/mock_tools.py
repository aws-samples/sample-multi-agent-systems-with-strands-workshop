"""Mock business intelligence tools for the production runtime.
Copy of decision_brief_tools.py: kept here so the container is self-contained.
In production, replace with AgentCore Gateway Web Search or another live data source.
"""

"""
Mock tools for the Decision Intelligence use case.

These tools simulate a real business intelligence backend for NovaCart,
a mid-size e-commerce company evaluating a Premium Tier subscription launch.
All data is hardcoded for workshop reproducibility.
"""

from strands import tool


# ── Mock data ──────────────────────────────────────────────────────────────


COMPANIES = {
    "novacart": {
        "company": "NovaCart",
        "industry": "e-commerce",
        "founded": 2018,
        "market": "US and Canada",
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
        "industry": "e-commerce",
        "avg_annual_churn_rate_pct": 25,
        "avg_customer_lifetime_value_usd": 290.00,
        "subscription_adoption_rate_pct": 31,
        "avg_subscription_price_usd": 15.50,
        "premium_tier_adoption_top_spenders_pct": 68,
        "clv_lift_with_subscription_pct": "20-35",
        "avg_time_to_subscription_profitability_months": 9,
        "key_insight": (
            "E-commerce brands with subscription tiers see 20-35% higher CLV vs "
            "non-subscribers. Top-spender segments adopt at 2x the rate of the general base."
        ),
    }
}

COMPETITORS = {
    "shopmart": {
        "company": "ShopMart",
        "tier_name": "ShopMart Plus",
        "launched": "Q2 2024",
        "monthly_price_usd": 16.99,
        "annual_price_usd": 149.99,
        "benefits": [
            "Free standard shipping on all orders",
            "5% cashback on every purchase",
            "Early access to flash sales",
            "Priority customer support",
        ],
        "pilot_approach": "5% of users for 90 days before full rollout",
        "adoption_rate_6mo_pct": 28,
        "clv_lift_pct": 22,
        "time_to_profitability_months": 8,
        "key_insight": (
            "ShopMart Plus launched with a 5% pilot. After 90 days they validated "
            "unit economics before scaling. Reached 28% adoption in 6 months."
        ),
    },
    "primestore": {
        "company": "PrimeStore",
        "tier_name": "PrimeStore Unlimited",
        "launched": "Q4 2023",
        "monthly_price_usd": 12.99,
        "annual_price_usd": 99.99,
        "benefits": [
            "Free 2-day shipping",
            "3% cashback",
            "Exclusive member deals",
            "30-day free trial",
        ],
        "pilot_approach": "Full launch to all users with 30-day free trial",
        "adoption_rate_6mo_pct": 19,
        "clv_lift_pct": 14,
        "time_to_profitability_months": 14,
        "key_insight": (
            "PrimeStore launched to all users at once. Lower price point drove higher "
            "sign-ups but lower retention: 40% churned after trial. Slower to profitability."
        ),
    },
}


# ── Tools ──────────────────────────────────────────────────────────────────


@tool
def get_company_data(company_name: str) -> str:
    """Get current financial and operational data for a company.

    Args:
        company_name: The company name to look up (e.g. 'NovaCart')
    """
    key = company_name.lower().strip()
    data = COMPANIES.get(key)
    if not data:
        available = ", ".join(COMPANIES.keys())
        return f"No data found for '{company_name}'. Available companies: {available}"

    return (
        f"Company: {data['company']} ({data['industry']}, founded {data['founded']})\n"
        f"Market: {data['market']}\n"
        f"Active users: {data['active_users']:,}\n"
        f"Annual churn rate: {data['annual_churn_rate_pct']}%\n"
        f"Average order value: ${data['average_order_value_usd']:.2f}\n"
        f"Customer Lifetime Value (CLV): ${data['customer_lifetime_value_usd']:.2f}\n"
        f"Annual revenue: ${data['annual_revenue_usd']:,.0f}\n"
        f"Current subscription revenue: ${data['subscription_revenue_usd']:,.0f}\n"
        f"Top spender segment: top {data['top_spender_segment_pct']}% of users, "
        f"avg order ${data['top_spender_avg_order_value_usd']:.2f}\n"
        f"Q1 survey: premium tier interest: {data['q1_survey_premium_interest_pct']}% of top spenders"
    )


@tool
def get_market_benchmarks(industry: str) -> str:
    """Get industry benchmarks and performance data for a given market sector.

    Args:
        industry: The industry sector to benchmark (e.g. 'e-commerce', 'saas')
    """
    key = industry.lower().strip()
    data = BENCHMARKS.get(key)
    if not data:
        available = ", ".join(BENCHMARKS.keys())
        return f"No benchmarks found for '{industry}'. Available industries: {available}"

    return (
        f"Industry: {data['industry']}\n"
        f"Average annual churn rate: {data['avg_annual_churn_rate_pct']}%\n"
        f"Average CLV: ${data['avg_customer_lifetime_value_usd']:.2f}\n"
        f"Subscription tier adoption rate: {data['subscription_adoption_rate_pct']}%\n"
        f"Average subscription price: ${data['avg_subscription_price_usd']:.2f}/mo\n"
        f"Premium tier adoption among top spenders: {data['premium_tier_adoption_top_spenders_pct']}%\n"
        f"CLV lift with subscription: {data['clv_lift_with_subscription_pct']}%\n"
        f"Avg time to subscription profitability: {data['avg_time_to_subscription_profitability_months']} months\n"
        f"Key insight: {data['key_insight']}"
    )


@tool
def get_competitor_data(competitor_name: str) -> str:
    """Get information about a competitor's premium subscription tier.

    Args:
        competitor_name: The competitor name to look up (e.g. 'shopmart', 'primestore')
    """
    key = competitor_name.lower().strip()
    data = COMPETITORS.get(key)
    if not data:
        available = ", ".join(COMPETITORS.keys())
        return f"No data found for '{competitor_name}'. Available competitors: {available}"

    benefits_str = "\n  ".join(f"- {b}" for b in data["benefits"])
    return (
        f"Competitor: {data['company']}: {data['tier_name']}\n"
        f"Launched: {data['launched']}\n"
        f"Price: ${data['monthly_price_usd']:.2f}/mo or ${data['annual_price_usd']:.2f}/yr\n"
        f"Benefits:\n  {benefits_str}\n"
        f"Pilot approach: {data['pilot_approach']}\n"
        f"6-month adoption rate: {data['adoption_rate_6mo_pct']}%\n"
        f"CLV lift observed: +{data['clv_lift_pct']}%\n"
        f"Time to profitability: {data['time_to_profitability_months']} months\n"
        f"Key insight: {data['key_insight']}"
    )
