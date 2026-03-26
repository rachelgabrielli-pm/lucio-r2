import json
import os
from datetime import datetime, timedelta
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

# Week start = always last 7 days from today
WEEK_START = (datetime.now().date() - timedelta(days=7)).isoformat()

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

    # Weekly signals — pre-computed by backend, this week only
    weekly            = data.get("weekly_signals", {})
    weekly_sales      = weekly.get("weekly_gross_sales_usd", 0)
    weekly_consist    = weekly.get("weekly_consistency_pct", 0)
    merchants_selling = weekly.get("merchants_selling_this_week", 0)

    total_rev_share = sum(m["partner_revenue_share"] for m in merchants)
    active_count    = sum(1 for m in merchants if m["financing_status"] == "ACTIVE")

    # Revenue share earned THIS WEEK = new disbursements this week x rev_share_rate
    weekly_rev = sum(
        m.get("partner_revenue_share", 0) for m in merchants
        if m.get("disbursement_date", "") >= WEEK_START
    )

    # New merchants onboarded this week
    new_this_week = sum(
        1 for m in merchants
        if m.get("disbursement_date", "") >= WEEK_START
    )

    approval_rate = funnel.get("approval_rate_pct", 0)

    # Top performers: pace >= 1.1 AND uplift >= 25%
    top_performers = [
        m for m in merchants
        if m.get("repayment_pace_ratio", 0) >= 1.1
        and m.get("financing_status") in ["ACTIVE", "PAID"]
        and m.get("gross_sales_uplift_pct", 0) >= 25
    ]

    # Fallback ICP: if no top performers, use neutral merchants with positive uplift
    icp_source = top_performers if top_performers else [
        m for m in merchants
        if m.get("repayment_pace_ratio", 0) >= 0.8
        and m.get("financing_status") in ["ACTIVE", "PAID"]
        and m.get("gross_sales_uplift_pct", 0) >= 5
    ][:20]

    avg_uplift = round(
        sum(m.get("gross_sales_uplift_pct", 0) for m in top_performers)
        / len(top_performers), 1
    ) if top_performers else 0

    week = datetime.now().strftime("%B %d, %Y")
    week_start_fmt = datetime.fromisoformat(WEEK_START).strftime("%B %d")

    # Slim merchant context — only essential fields, top 40 by pace ratio
    slim_merchants = [
        {
            "merchant_id":               m["merchant_id"],
            "merchant_name":             m["merchant_name"],
            "segment":                   m["segment"],
            "country":                   m["country"],
            "city":                      m.get("city", ""),
            "financing_status":          m["financing_status"],
            "repayment_pace_ratio":      m.get("repayment_pace_ratio", 0),
            "gross_sales_uplift_pct":    m.get("gross_sales_uplift_pct", 0),
            "gross_sales_pre_avg_monthly": m.get("gross_sales_pre_avg_monthly", 0),
            "gross_sales_trend":         m.get("gross_sales_trend", 0),
            "avg_order_size":            m.get("avg_order_size", 0),
            "refund_rate":               m.get("refund_rate", 0),
            "customer_rating":           m.get("customer_rating", 0),
            "active_listings":           m.get("active_listings", 0),
            "avg_monthly_txn_count":     m.get("avg_monthly_txn_count", 0),
            "zero_sales_days_last_90d":  m.get("zero_sales_days_last_90d", 0),
            "disbursement_date":         m.get("disbursement_date", ""),
            "partner_revenue_share":     m.get("partner_revenue_share", 0),
            "total_prior_credits":       m.get("total_prior_credits", 0),
        }
        for m in sorted(merchants, key=lambda x: x.get("repayment_pace_ratio", 0), reverse=True)[:40]
    ]

    context = (
        f"You are Lucio, a partner intelligence agent built by R2 - a revenue-based "
        f"financing company operating across Latin America.\n\n"
        f"R2 also runs Arturo, a collections agent for merchants with risk signals "
        f"(repayment_pace_ratio < 0.8). Arturo owns that segment.\n\n"
        f"PARTNER: {partner_name} (ID: {partner_id})\n"
        f"Revenue share rate: {rev_share_rate * 100:.1f}%\n\n"
        f"THIS WEEK DATA ({week_start_fmt} - {week} ONLY):\n"
        f"- Weekly gross sales ALL active merchants: ${weekly_sales:,.2f}\n"
        f"- Merchants selling this week: {merchants_selling}\n"
        f"- Sales consistency: {weekly_consist}%\n"
        f"- New merchants onboarded this week: {new_this_week}\n"
        f"- Revenue share earned this week (new disbursements): ${weekly_rev:,.2f}\n"
        f"- Approval rate: {approval_rate}%\n"
        f"- Active financing relationships: {active_count}\n\n"
        f"TOP PERFORMERS IDENTIFIED ({len(top_performers)} merchants with pace>=1.1 AND uplift>=25%):\n"
        f"MERCHANT PORTFOLIO (top 40 by repayment pace):\n"
        f"{json.dumps(slim_merchants, indent=2)}\n\n"
        f"FIELD DEFINITIONS:\n"
        f"gross_sales_pre_avg_monthly - avg monthly sales BEFORE credit\n"
        f"gross_sales_uplift_pct - % change post vs pre credit monthly avg\n"
        f"gross_sales_trend - slope of sales before credit (positive = already growing)\n"
        f"repayment_pace_ratio - actual repayment speed / projected speed\n"
        f"  >1.1 = paying faster than projected (thriving)\n"
        f"  <0.8 = paying slower (Arturo territory)\n"
        f"refund_rate - % of orders refunded\n"
        f"disbursement_date - date the loan was disbursed\n"
        f"financing_status - ACTIVE, PAID, PAUSED\n"
    )

    # ── STEP 1: Classify ──────────────────────────────────────────────────────
    step1 = context + f"""
TASK - STEP 1: CLASSIFY MERCHANTS
Use these exact criteria:

Arturo territory: repayment_pace_ratio < 0.8 OR financing_status = PAUSED
Top Performer (ALL must be true):
  - gross_sales_uplift_pct >= 25%
  - repayment_pace_ratio >= 1.1
  - financing_status in [ACTIVE, PAID]
Neutral: everything else that is healthy

End with a clean summary:
TOP PERFORMERS: [id - name - uplift% - pace ratio]
NEUTRAL (top 10): [id - name]
ARTURO TERRITORY (top 5): [id - name]
"""

    r1 = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=5000,
        thinking={"type": "enabled", "budget_tokens": 3000},
        messages=[{"role": "user", "content": step1}]
    )

    classification_thinking = ""
    classification_text = ""
    for block in r1.content:
        if block.type == "thinking":
            classification_thinking = block.thinking
        elif block.type == "text":
            classification_text = block.text

    # ── STEP 2: Build ICP ─────────────────────────────────────────────────────
    fallback_note = "" if top_performers else (
        "NOTE: No merchants met top performer criteria this week. "
        "Using neutral merchants with positive uplift as ICP proxy."
    )

    step2 = context + f"""
STEP 1 RESULTS:
{classification_text}

TASK - STEP 2: BUILD THE PRE-CREDIT ICP PROFILE
{fallback_note}

Using these merchants as ICP source:
{json.dumps([{{
    "merchant_id": m["merchant_id"],
    "merchant_name": m["merchant_name"],
    "segment": m["segment"],
    "country": m["country"],
    "gross_sales_pre_avg_monthly": m.get("gross_sales_pre_avg_monthly", 0),
    "gross_sales_trend": m.get("gross_sales_trend", 0),
    "avg_order_size": m.get("avg_order_size", 0),
    "refund_rate": m.get("refund_rate", 0),
    "customer_rating": m.get("customer_rating", 0),
    "active_listings": m.get("active_listings", 0),
    "avg_monthly_txn_count": m.get("avg_monthly_txn_count", 0),
    "zero_sales_days_last_90d": m.get("zero_sales_days_last_90d", 0),
    "disbursement_date": m.get("disbursement_date", ""),
    "gross_sales_uplift_pct": m.get("gross_sales_uplift_pct", 0),
}} for m in icp_source[:15]], indent=2)}

Extract what these merchants looked like BEFORE credit.
Give concrete thresholds for each field.
End with:
"Before taking their first R2 loan, your top performers looked like this: [description]"
"""

    r2 = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        thinking={"type": "enabled", "budget_tokens": 1500},
        messages=[{"role": "user", "content": step2}]
    )

    icp_thinking = ""
    icp_text = ""
    for block in r2.content:
        if block.type == "thinking":
            icp_thinking = block.thinking
        elif block.type == "text":
            icp_text = block.text

    # ── STEP 3: Write digest ──────────────────────────────────────────────────
    top_list = "\n".join([
        f"  {i+1}. {m['merchant_name']} ({m['segment'].replace('_',' ')}, {m.get('city','')}, {m['country']}): "
        f"+{m.get('gross_sales_uplift_pct',0):.1f}% sales uplift, "
        f"{m.get('repayment_pace_ratio',0):.2f}x repayment pace"
        for i, m in enumerate(sorted(top_performers, key=lambda x: x.get("gross_sales_uplift_pct", 0), reverse=True)[:5])
    ]) if top_performers else "  (Using historical top performer profiles this week)"

    step3 = f"""Write a weekly digest for {partner_name}'s credit program manager.
This person works in marketing or partnerships - not a data analyst.
Keep it concise - sent via WhatsApp. No markdown formatting with ** or #.

USE ONLY THESE EXACT NUMBERS — DO NOT CALCULATE OR INVENT DIFFERENT ONES:
- Gross sales this week: ${weekly_sales:,.2f}
- Sales consistency: {weekly_consist}%
- Credit approval rate: {approval_rate}%
- New merchants this week: {new_this_week}
- Revenue share earned this week: ${weekly_rev:,.2f}
- Avg sales uplift of top performers: {avg_uplift}%

TOP PERFORMERS THIS WEEK:
{top_list}

PRE-CREDIT ICP SUMMARY:
{icp_text[:600]}

FALLBACK: If fewer than 3 top performers, replace the top performers section with:
"Your top performers so far had an average sales increase of {avg_uplift}% - here is what they looked like:"
Then go straight to WHAT YOUR WINNERS LOOKED LIKE BEFORE CREDIT.

Write EXACTLY this structure — use plain text only, no bold markers:

---
Hey {partner_name} team! Here is your R2 program performance summary for the week of {week_start_fmt}-{week}.

YOUR PROGRAM THIS WEEK - TOP PERFORMERS
- Gross sales across active merchants this week: [use ${weekly_sales:,.2f}]
- Sales consistency: [use {weekly_consist}]% of merchants sold every day this week
- Credit approval rate: [use {approval_rate}]% of applications approved
- New active financing relationships: [use {new_this_week}] new merchants this week
- Revenue share earned this week: [use ${weekly_rev:,.2f}]

THIS WEEK'S TOP PERFORMERS
[List top 3-5. Name, segment, city, uplift %, pace ratio, one human sentence about what makes them stand out]

Your top performers had an average sales increase of {avg_uplift}% compared to their pre-credit baseline.

WHAT YOUR WINNERS LOOKED LIKE BEFORE CREDIT
[4-5 bullet points from ICP. Concrete numbers only. A checklist the partner can use to target similar merchants.]

USE THIS TO GROW YOUR PROGRAM
Target your credit offers to merchants hitting these operational benchmarks - they are already
demonstrating the cashflow consistency and growth trajectory that predicts success with financing.

How can I help you dig deeper into this data and identify the best opportunities to boost your revenue?
---

Output ONLY the digest text. No markdown formatting. No asterisks or hashtags.
"""

    r3 = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1200,
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
