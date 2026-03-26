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

WEEK_START = "2026-03-22"  # Fixed week start for demo

def load_data(filepath="data/merchants.json"):
    with open(filepath, "r") as f:
        return json.load(f)

def run_lucio(data: dict) -> dict:
    from datetime import datetime, timedelta

    partner_name   = data["partner_name"]
    partner_id     = data["partner_id"]
    rev_share_rate = data["rev_share_rate"]
    funnel         = data["funnel"]
    merchants      = data["merchants"]

    # Weekly signals — pre-computed by backend, this week only
    weekly            = data.get("weekly_signals", {})
    weekly_sales      = weekly.get("weekly_gross_sales_usd", 0)
    weekly_consist    = weekly.get("weekly_consistency_pct", 0)
    merchants_selling = weekly.get("merchants_selling_this_week", 0)

    total_rev_share = sum(m["partner_revenue_share"] for m in merchants)
    active_count    = sum(1 for m in merchants if m["financing_status"] == "ACTIVE")

    # Revenue share earned THIS WEEK = new disbursements this week
    weekly_rev = sum(
        m.get("partner_revenue_share", 0) for m in merchants
        if m.get("disbursement_date", "") >= WEEK_START
    )

    # New merchants this week
    new_this_week = sum(
        1 for m in merchants
        if m.get("disbursement_date", "") >= WEEK_START
    )

    # Approval rate this week
    week_apps     = funnel.get("total_applications", 0)
    week_approved = funnel.get("total_approved", 0)
    approval_rate = funnel.get("approval_rate_pct", 0)

    # Top performers: pace >= 1.1 AND uplift >= 25%
    top_performers = [
        m for m in merchants
        if m.get("repayment_pace_ratio", 0) >= 1.1
        and m.get("financing_status") in ["ACTIVE", "PAID"]
        and m.get("gross_sales_uplift_pct", 0) >= 25
    ]

    # Fallback ICP source: if no top performers, use neutral merchants
    icp_source = top_performers if top_performers else [
        m for m in merchants
        if m.get("repayment_pace_ratio", 0) >= 0.8
        and m.get("financing_status") in ["ACTIVE", "PAID"]
        and m.get("gross_sales_uplift_pct", 0) >= 5
    ][:15]

    avg_uplift = round(
        sum(m.get("gross_sales_uplift_pct", 0) for m in top_performers)
        / len(top_performers), 1
    ) if top_performers else 0

    # Weekly gross sales for top performers only
    top_weekly_sales = sum(
        m.get("gross_sales_uplift_pct", 0) * m.get("gross_sales_pre_avg_monthly", 0) / 100
        for m in top_performers
    )

    week = datetime.now().strftime("%B %d, %Y")

    context = (
        "You are Lucio, a partner intelligence agent built by R2 - a revenue-based "
        "financing company operating across Latin America.\n\n"
        "R2 runs Arturo, a collections agent for merchants with risk signals "
        "(repayment_pace_ratio < 0.8). Arturo owns that segment entirely.\n\n"
        "Your role: analyze thriving merchants and produce a weekly digest for "
        "the partner credit program manager.\n\n"
        f"PARTNER: {partner_name} (ID: {partner_id})\n"
        f"Revenue share rate: {rev_share_rate * 100:.1f}%\n\n"
        f"THIS WEEK DATA (March 22-26, 2026 ONLY):\n"
        f"- Weekly gross sales ALL merchants: ${weekly_sales:,.2f}\n"
        f"- Merchants selling this week: {merchants_selling}\n"
        f"- Sales consistency: {weekly_consist}%\n"
        f"- New merchants onboarded this week: {new_this_week}\n"
        f"- Revenue share earned this week (new disbursements): ${weekly_rev:,.2f}\n"
        f"- Approval rate: {approval_rate}%\n"
        f"- Active financing relationships: {active_count}\n\n"
        f"TOP PERFORMERS THIS WEEK ({len(top_performers)} merchants):\n"
        f"pace >= 1.1 AND gross_sales_uplift_pct >= 25%\n\n"
        f"MERCHANT PORTFOLIO (all {len(merchants)} merchants):\n"
        f"{json.dumps(merchants[:80], indent=2)}\n\n"
        "FIELD DEFINITIONS:\n"
        "gross_sales_pre_avg_monthly - avg monthly sales BEFORE credit\n"
        "gross_sales_90d_post - total sales in 90 days AFTER disbursement\n"
        "gross_sales_uplift_pct - % change post vs pre credit monthly avg\n"
        "gross_sales_trend - slope of monthly sales before credit (positive = growing)\n"
        "avg_order_size - average ticket per order\n"
        "repayment_pace_ratio - actual speed / projected (>1.1 = thriving, <0.8 = Arturo)\n"
        "refund_rate - % of orders refunded\n"
        "total_prior_credits - fully repaid R2 loans before this one\n"
        "zero_sales_days_last_90d - days with no sales pre-credit\n"
        "financing_status - ACTIVE, PAID, PAUSED\n"
        "disbursement_date - date the loan was disbursed\n"
    )

    # STEP 1 - Classify merchants
    step1 = context + f"""
TASK - STEP 1: CLASSIFY MERCHANTS
Classify merchants using ONLY these criteria:

Arturo territory: repayment_pace_ratio < 0.8 OR financing_status = PAUSED
Top Performer (ALL must be true):
  - gross_sales_uplift_pct >= 25%
  - repayment_pace_ratio >= 1.1
  - financing_status in [ACTIVE, PAID]
Neutral: everything else that is healthy

Focus your analysis on the top {min(len(top_performers)+20, 50)} merchants by repayment_pace_ratio.

End with:
TOP PERFORMERS: [id - name - uplift% - pace ratio]
NEUTRAL: [id - name] (top 10 only)
ARTURO TERRITORY: [id - name] (top 5 only)
"""

    r1 = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=6000,
        thinking={"type": "enabled", "budget_tokens": 4000},
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
    icp_data = json.dumps(icp_source[:20], indent=2)
    fallback_note = "" if top_performers else "(NOTE: No merchants met top performer criteria this week. Using neutral merchants with positive uplift as ICP proxy.)"

    step2 = context + f"""
STEP 1 RESULTS:
{classification_text}

TASK - STEP 2: BUILD THE PRE-CREDIT ICP PROFILE
{fallback_note}

Using these merchants as your ICP source:
{icp_data}

Extract what these merchants looked like BEFORE they took a loan with R2.
Use ONLY pre-credit fields:
- gross_sales_pre_avg_monthly, gross_sales_trend
- platform_join_date / months on platform
- active_listings, avg_order_size
- refund_rate, zero_sales_days_last_90d
- avg_monthly_txn_count, customer_rating
- segment, business_type, country

Give concrete thresholds. End with:
"Before taking their first R2 loan, your top performers looked like this: [description]"
"""

    r2 = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=3000,
        thinking={"type": "enabled", "budget_tokens": 2000},
        messages=[{"role": "user", "content": step2}]
    )

    icp_thinking = ""
    icp_text = ""
    for block in r2.content:
        if block.type == "thinking":
            icp_thinking = block.thinking
        elif block.type == "text":
            icp_text = block.text

    # STEP 3 - Write weekly digest
    top_list = "\n".join([
        f"  - {m['merchant_name']} ({m['segment'].replace('_',' ')}, {m.get('city','')}, {m['country']}): "
        f"+{m.get('gross_sales_uplift_pct',0):.1f}% sales uplift, "
        f"{m.get('repayment_pace_ratio',0):.2f}x repayment pace"
        for m in sorted(top_performers, key=lambda x: x.get('gross_sales_uplift_pct',0), reverse=True)[:5]
    ]) if top_performers else "  (No merchants met top performer criteria this week)"

    step3 = f"""
You are Lucio, R2's partner intelligence agent.
Write the weekly digest for {partner_name}'s credit program manager.
This person works in marketing or partnerships - not a data analyst.
Keep it concise - sent via WhatsApp.

USE ONLY THESE NUMBERS - DO NOT CALCULATE OR INVENT:
Weekly gross sales (top performers): ${weekly_sales:,.2f}
Sales consistency: {weekly_consist}% sold every day
Credit approval rate: {approval_rate}%
New active financing relationships this week: {new_this_week} merchants
Revenue share earned this week: ${weekly_rev:,.2f}
Average sales uplift of top performers: {avg_uplift}%

TOP PERFORMERS LIST:
{top_list}

PRE-CREDIT ICP:
{icp_text[:800]}

FALLBACK RULE: If fewer than 3 top performers, write:
"Your top performers so far had an average sales increase of {avg_uplift}% - here is what they looked like:"
Then go straight to WHAT YOUR WINNERS LOOKED LIKE BEFORE CREDIT.

Write EXACTLY this structure:

---
Hey {partner_name} team! Here is your R2 program performance summary for the week of March 22-26, 2026.

YOUR PROGRAM THIS WEEK - TOP PERFORMERS
- Gross sales across top performers this week: $[use weekly_sales number above]
- Sales consistency: [use weekly_consist]% of top merchants sold every day this week
- Credit approval rate: [use approval_rate]% of applications approved this week
- New active financing relationships: [use new_this_week] new merchants this week
- Revenue share earned this week: $[use weekly_rev number above]

THIS WEEK'S TOP PERFORMERS
[List top 3-5 from the list above. For each: name, segment, city, uplift %, pace ratio, one human sentence]

Your top performers had an average sales increase of {avg_uplift}% compared to their pre-credit baseline.

WHAT YOUR WINNERS LOOKED LIKE BEFORE CREDIT
[4-5 bullet points from ICP. Concrete numbers only. A checklist the partner can use.]

USE THIS TO GROW YOUR PROGRAM
Target your credit offers to merchants hitting these operational benchmarks - they are already
demonstrating the cashflow consistency and growth trajectory that predicts success with financing.

How can I help you dig deeper into this data and identify the best opportunities to boost your revenue?
---

Tone: professional but warm. For a marketing manager. In English. Output ONLY the digest.
"""

    r3 = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
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
