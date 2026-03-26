import json
import os
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

import os

def get_api_key():
    try:
        import streamlit as st
        if hasattr(st, "secrets") and "ANTHROPIC_API_KEY" in st.secrets:
            return st.secrets["ANTHROPIC_API_KEY"]
    except Exception:
        pass
    return os.getenv("ANTHROPIC_API_KEY")

client = Anthropic(api_key=get_api_key())

def load_data(filepath="data/merchants.json"):
    with open(filepath, "r") as f:
        return json.load(f)

def run_lucio(data: dict) -> dict:
    partner_name   = data["partner_name"]
    partner_id     = data["partner_id"]
    rev_share_rate = data["rev_share_rate"]
    funnel         = data["funnel"]
    merchants      = data["merchants"]

    total_rev_share = sum(m["partner_revenue_share"] for m in merchants)
    active_count    = sum(1 for m in merchants if m["financing_status"] == "ACTIVE")

    # Weekly signals from backend
    weekly         = data.get("weekly_signals", {})
    weekly_sales   = weekly.get("weekly_gross_sales_usd", 0)
    weekly_consist = weekly.get("weekly_consistency_pct", 0)
    week_start     = weekly.get("week_start", "")
    week_end       = weekly.get("week_end", "")
    merchants_selling = weekly.get("merchants_selling_this_week", active_count)

    # Calculate avg uplift of top performers
    top_performers = [m for m in merchants
                      if m.get("repayment_pace_ratio", 0) >= 1.1
                      and m.get("financing_status") in ["ACTIVE", "PAID"]
                      and m.get("gross_sales_uplift_pct", 0) >= 25]
    avg_uplift = round(
        sum(m.get("gross_sales_uplift_pct", 0) for m in top_performers) / len(top_performers), 1
    ) if top_performers else 0

    # Weekly revenue share = new loans disbursed this week * rev_share_rate
    # The partner earns rev share at disbursement time, not from daily repayments
    from datetime import datetime, timedelta
    week_start_date = (datetime.now().date() - timedelta(days=7)).isoformat()
    weekly_rev = sum(
        m.get("partner_revenue_share", 0) for m in merchants
        if m.get("disbursement_date", "") >= week_start_date
    )

    from datetime import datetime
    week = datetime.now().strftime("%B %d, %Y")

    context = (
        "You are Lucio, a partner intelligence agent built by R2 - a revenue-based "
        "financing company operating across Latin America.\n\n"
        "R2 already runs Arturo, a collections agent that monitors merchants showing "
        "risk signals (repayment_pace_ratio < 0.8) and intervenes before default. "
        "Arturo owns that segment entirely.\n\n"
        "Your role is the opposite. You operate EXCLUSIVELY on merchants that are "
        "healthy and thriving. Your filter:\n"
        "  - repayment_pace_ratio >= 1.1\n"
        "  - financing_status in [ACTIVE, PAID]\n\n"
        f"PARTNER: {partner_name} (ID: {partner_id})\n"
        f"Revenue share rate: {rev_share_rate * 100:.1f}%\n"
        f"Total revenue share earned: ${total_rev_share:,.2f}\n"
        f"Active relationships: {active_count}\n\n"
        f"FUNNEL (last 90 days):\n"
        f"Total applications: {funnel['total_applications']}\n"
        f"Approved: {funnel['total_approved']} ({funnel['approval_rate_pct']}%)\n"
        f"Denied: {funnel['total_denied']}\n"
        f"Top denial reasons: {json.dumps(funnel['top_denial_reasons'], indent=2)}\n\n"
        f"MERCHANT PORTFOLIO:\n"
        f"{json.dumps(merchants, indent=2)}\n\n"
        "FIELD DEFINITIONS:\n"
        "gross_sales_pre_avg_monthly - avg monthly sales BEFORE credit\n"
        "gross_sales_90d_post - total sales in first 90 days AFTER disbursement\n"
        "gross_sales_uplift_pct - % change post vs pre credit\n"
        "gross_sales_trend - slope of monthly sales trend before credit (positive = growing)\n"
        "avg_order_size - average ticket per order\n"
        "repayment_pace_ratio - actual speed / projected speed (>1.1 = thriving, <0.8 = Arturo)\n"
        "refund_rate - % of orders refunded (>5% is a warning sign)\n"
        "total_prior_credits - fully repaid R2 loans before this one\n"
        "zero_sales_days_last_90d - days with no sales pre-credit\n"
        "avg_monthly_txn_count - number of orders per month\n"
        "financing_status - ACTIVE, PAID, PAUSED\n"
    )

    # STEP 1 - Classify merchants
    step1 = context + """
TASK - STEP 1: CLASSIFY EVERY MERCHANT
Go through every merchant one by one.

Arturo territory: repayment_pace_ratio < 0.8 OR financing_status = PAUSED
Top Performer (ALL must be true):
  - gross_sales_uplift_pct >= 25%
  - repayment_pace_ratio >= 1.1
  - financing_status in [ACTIVE, PAID]
Neutral: healthy but not standout

For each merchant state classification, exact numbers, and one standout signal.

End with summary:
TOP PERFORMERS: [id - name]
NEUTRAL: [id - name]
ARTURO TERRITORY: [id - name]
"""

    r1 = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8000,
        thinking={"type": "enabled", "budget_tokens": 5000},
        messages=[{"role": "user", "content": step1}]
    )

    classification_thinking = ""
    classification_text = ""
    for block in r1.content:
        if block.type == "thinking":
            classification_thinking = block.thinking
        elif block.type == "text":
            classification_text = block.text

    # STEP 2 - Build pre-credit ICP
    step2 = context + f"""
STEP 1 RESULTS:
{classification_text}

TASK - STEP 2: BUILD THE PRE-CREDIT ICP PROFILE
Using ONLY TOP PERFORMERS from Step 1, extract what these merchants
looked like BEFORE they ever took a loan with R2.

This is critical: the partner needs to find merchants that look like
this BEFORE credit. Use ONLY pre-credit fields:
- gross_sales_pre_avg_monthly, gross_sales_trend
- platform_join_date, active_listings
- avg_order_size, refund_rate
- zero_sales_days_last_90d, avg_monthly_txn_count
- customer_rating, segment, business_type, country
- total_prior_credits

For each dimension give thresholds that separate top from rest.

End with:
"Before taking their first R2 loan, your top performers looked like this: [description]"
"""

    r2 = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=5000,
        thinking={"type": "enabled", "budget_tokens": 3000},
        messages=[{"role": "user", "content": step2}]
    )

    icp_thinking = ""
    icp_text = ""
    for block in r2.content:
        if block.type == "thinking":
            icp_thinking = block.thinking
        elif block.type == "text":
            icp_text = block.text

    # STEP 3 - Write the weekly digest
    step3 = context + f"""
STEP 1 RESULTS:
{classification_text}

STEP 2 PRE-CREDIT ICP:
{icp_text}

TASK - STEP 3: WRITE THE WEEKLY DIGEST
Write the weekly digest Lucio sends to {partner_name} credit program manager.
This person works in marketing or partnerships - not a data analyst.
Keep it concise - this will be sent via WhatsApp.

FALLBACK RULE: If fewer than 3 top performers this week, skip the
"THIS WEEK'S TOP PERFORMERS" section entirely and write instead:
"Your top performers so far had an average sales increase of {avg_uplift}% -
here is what they looked like:" then go directly to WHAT YOUR WINNERS LOOKED LIKE BEFORE CREDIT.

WEEKLY DATA TO USE (this week only):
- Gross sales this week: ${weekly_sales:,.2f}
- Merchants selling this week: {merchants_selling}
- Sales consistency: {weekly_consist}%
- Approval rate: {funnel['approval_rate_pct']}%
- Revenue share earned this week: ${weekly_rev:,.2f}
- Active financing relationships: {active_count}

Follow this structure EXACTLY:

---
Hey {partner_name} team! Here is your R2 program performance summary for the week of {week}.

YOUR PROGRAM THIS WEEK
- Gross sales across active merchants: $[use weekly_sales]
- Sales consistency: [use weekly_consist]% of merchants sold every day this week
- Credit approval rate: [use approval_rate_pct]% of applications approved
- Active financing relationships: [use active_count] merchants
- Revenue share earned this week: $[use weekly_rev]

THIS WEEK'S TOP PERFORMERS
[List top 3-5 performers. For each:
  - Name, segment, city
  - Gross sales uplift % vs pre-credit average
  - Repayment pace: paying Xx faster than projected
  - One human sentence on what makes them stand out]

Your top performers had an average sales increase of {avg_uplift}% compared to their pre-credit baseline.

WHAT YOUR WINNERS LOOKED LIKE BEFORE CREDIT
[4-5 bullet points from PRE-CREDIT ICP only. Concrete numbers. A checklist the partner can use to filter merchants.]

USE THIS TO GROW YOUR PROGRAM
Target your credit offers to merchants hitting these operational benchmarks - they are already
demonstrating the cashflow consistency and growth trajectory that predicts success with financing.
Dark kitchens meeting these criteria should be your first priority, followed by established
restaurants with 15+ months tenure. Skip merchants with inconsistent sales patterns or ratings
below 4.5 stars.

How can I help you dig deeper into this data and identify the best opportunities to boost your revenue?
---

Tone: professional but warm. Conversational. For a marketing manager not a data analyst.
In English. Output ONLY the digest text, nothing else.
"""

    r3 = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": step3}]
    )

    brief_text = r3.content[0].text

    return {
        "partner_name":            partner_name,
        "total_rev_share":         total_rev_share,
        "active_count":            active_count,
        "funnel":                  funnel,
        "classification_thinking": classification_thinking,
        "classification_text":     classification_text,
        "icp_thinking":            icp_thinking,
        "icp_text":                icp_text,
        "brief":                   brief_text,
    }


if __name__ == "__main__":
    print("Loading data...")
    data = load_data()
    print(f"Running Lucio for {data['partner_name']}...")
    result = run_lucio(data)
    print("\n" + "="*60)
    print("DIGEST")
    print("="*60)
    print(result["brief"])
