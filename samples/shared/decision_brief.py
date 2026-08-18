"""Shared decision brief and mock data for all workshop modules."""

DECISION_BRIEF = """
DECISION BRIEF: NovaCart Premium Tier Launch

Company: NovaCart (mid-size e-commerce, 2M active users)
Decision owners: VP Product + CFO approval required

Context:
- Current annual churn rate: 22%
- Average order value: $85
- Customer Lifetime Value (CLV): $340
- A major competitor launched a similar subscription tier last quarter
- Q1 survey: 38% of top-spending users expressed interest in a premium tier

Options to evaluate:
- Option A: Exclusive Premium (invite-only for top 10% spenders, $19.99/mo)
- Option B: Gradual Rollout (5% A/B test pilot with kill-switch, $14.99/mo)
- Option C: Full Launch (open to all users immediately, $12.99/mo + 30-day free trial)

Success target: +15% CLV improvement within 6 months
Budget available: $2M (product + marketing + ops)
Decision deadline: 2027-01-31
"""

OPTIONS = {
    "A": {
        "name": "Option A: Exclusive Premium",
        "description": (
            "Invite-only tier for the top 10% of spenders (approx. 200,000 users). "
            "Price: $19.99/month. Benefits: free shipping, early access to sales, "
            "dedicated support. Marketing: word-of-mouth + targeted email to eligible users. "
            "Timeline to launch: 8 weeks."
        ),
    },
    "B": {
        "name": "Option B: Gradual Rollout",
        "description": (
            "5% A/B test pilot with a kill-switch if churn increases by more than 5 points. "
            "Price: $14.99/month. Benefits: free shipping, 5% cashback, priority support. "
            "Marketing: in-app banners for the pilot cohort only. "
            "Timeline to launch: 4 weeks. Evaluate and decide on full rollout at week 12."
        ),
    },
    "C": {
        "name": "Option C: Full Launch",
        "description": (
            "Open to all 2M active users immediately. "
            "Price: $12.99/month with a 30-day free trial. "
            "Benefits: free shipping, 3% cashback, exclusive deals. "
            "Marketing: full-channel campaign (email, social, in-app). "
            "Timeline to launch: 6 weeks."
        ),
    },
}
