import json
import os
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

client = Anthropic()

def load_data(filepath="data/merchants.json"):
    with open(filepath, "r") as f:
        return json.load(f)

def run_lucio(data: dict) -> dict:
    """
    Runs the Lucio agent against a partner dataset.
    Returns a structured result with:
    - classification_thinking: chain of thought for step 1 (visible in demo)
    - classification_text: merchant-by-merchant classification
    - icp_thinking: chain of thought for step 2 (visible in demo)
    - icp_text: the emerging ICP profile
    - brief: the final partner-facing message
    """

    partner_name   = data["partner_name"]
    partner_id     = data["partner_id"]
    rev_share_rate = data["rev_share_rate"]
    funnel         = data["funnel"]
    merchants      = data["merchants"]

    total_rev_share = sum(m["partner_revenue_share"] for m in merchants)
    active_count    = sum(1 for m in merchants if m["financing_status"] == "ACTIVE")

    # ── Shared context injected into every prompt ─────────────────────────
    context = f"""
You are Lucio, a partner intelligence agent built by R2 — a revenue-based 
financing company operating across Latin America.

R2 already runs Arturo, a collections agent that monitors merchants showing 
risk signals (repayment_pace_ratio < 0.8 or repayment_consistency = low) and 
intervenes before default. Arturo owns that segment of the portfolio entirely.

Your role is the opposite end of the spectrum. You operate EXCLUSIVELY on 
merchants that are healthy and thriving — those that Arturo has no reason to 
touch. You never overlap with Arturo's territory. Your filter is:
  - repayment_pace_ratio >= 1.1  (paying faster than projected at underwriting)
  - repayment_consistency = high (regular, predictable daily repayment)
  - financing_status in [ACTIVE, PAID] (not paused)

Your job: analyze these thriving merchants, identify what makes them succeed, 
extract the common profile, and produce a concise intelligence brief for the 
partner's credit program manager — so they know exactly who to offer credit to 
next in order to replicate these results.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PARTNER CONTEXT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Partner: {partner_name} (ID: {partner_id})
Revenue share rate: {rev_share_rate * 100:.1f}% of each loan amount
Total revenue share earned from this portfolio: ${total_rev_share:,.2f}
Active financing relationships: {active_count}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FUNNEL DATA — last 90 days
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total credit applications:  {funnel['total_applications']}
Approved:                   {funnel['total_approved']} ({funnel['approval_rate_pct']}%)
Denied:                     {funnel['total_denied']}
Top denial reasons:
{json.dumps(funnel['top_denial_reasons'], indent=2)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MERCHANT PORTFOLIO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{json.dumps(merchants, indent=2)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FIELD DEFINITIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
gmv_pre_avg_monthly     — average monthly sales BEFORE credit (historical baseline)
gmv_90d_post            — total sales in first 90 days AFTER disbursement
gmv_uplift_pct_vs_avg   — % change: post-credit monthly avg vs pre-credit avg
                          This is the primary growth signal. Use this, not vs_30d.

repayment_pace_ratio    — actual repayment speed / projected speed at underwriting
                          > 1.2 = paying much faster than projected (merchant thriving)
                          1.0   = exactly on track
                          < 0.8 = paying slower (Arturo's territory — ignore these)

repayment_consistency   — regularity of daily repayment (high / medium / low)
sales_consistency_score — 0–100, how regularly the merchant sells day to day
refund_rate             — % of transactions refunded (>5% is a warning sign)
has_direct_gmv          — true = GMV exact (partner reports directly)
                          false = GMV estimated from repayment ÷ rate
total_prior_credits     — fully repaid R2 loans before this one
is_first_credit         — is this their first loan with R2?
active_listings         — number of menu/product items active on platform
financing_status        — ACTIVE, PAID, PAUSED
"""

    # ─────────────────────────────────────────────────────────────────────
    # STEP 1 — Classify merchants, show reasoning
    # ─────────────────────────────────────────────────────────────────────
    step1_prompt = f"""
{context}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK — STEP 1: CLASSIFY EVERY MERCHANT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Go through every merchant in the portfolio one by one.

First, check if the merchant falls into Arturo's territory:
  - repayment_pace_ratio < 0.8 OR repayment_consistency = low OR 
    financing_status = PAUSED → mark as ARTURO TERRITORY, skip.

For the remaining merchants, classify as:

  TOP PERFORMER — all of the following must be true:
    · gmv_uplift_pct_vs_avg >= 25%
    · repayment_pace_ratio >= 1.1
    · repayment_consistency = high
    · financing_status in [ACTIVE, PAID]

  NEUTRAL — healthy but not a standout:
    · paying on track but growth is modest
    · or first-credit merchant too early to evaluate

  For each merchant state:
    1. Classification and why
    2. The exact numbers that drove the decision
    3. One standout signal if any (positive or cautionary)

End with a clean summary list:
  TOP PERFORMERS: [merchant_id — merchant_name]
  NEUTRAL: [merchant_id — merchant_name]
  ARTURO TERRITORY: [merchant_id — merchant_name]
"""

    r1 = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8000,
        thinking={"type": "enabled", "budget_tokens": 5000},
        messages=[{"role": "user", "content": step1_prompt}]
    )

    classification_thinking = ""
    classification_text = ""
    for block in r1.content:
        if block.type == "thinking":
            classification_thinking = block.thinking
        elif block.type == "text":
            classification_text = block.text

    # ─────────────────────────────────────────────────────────────────────
    # STEP 2 — Build ICP from top performers
    # ─────────────────────────────────────────────────────────────────────
    step2_prompt = f"""
{context}

STEP 1 RESULTS:
{classification_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK — STEP 2: BUILD THE ICP PROFILE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Using ONLY the TOP PERFORMERS from Step 1, extract the Ideal Customer Profile —
the traits that distinguish thriving merchants from neutral ones.

Analyze each dimension and state what top performers share vs. the rest:

1. BUSINESS PROFILE
   segment, business_type, country, city patterns

2. PLATFORM MATURITY
   months_on_platform range, active_listings range

3. PRE-CREDIT SIGNALS
   gmv_pre_avg_monthly range, gmv_trend_coefficient,
   sales_consistency_score, refund_rate, zero_sales_days_last_90d

4. CREDIT HISTORY
   is_first_credit patterns, total_prior_credits

5. BEHAVIORAL SIGNALS
   avg_monthly_txn_count, avg_txn_size, customer_rating

For each dimension name the threshold or pattern that separates 
top performers from the rest. Be specific — give numbers, not just directions.

Close with a plain-language SUMMARY ICP that a partner's credit program 
manager could use as a practical filter:
"The merchants most likely to succeed with R2 credit are: [description]"
"""

    r2 = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=5000,
        thinking={"type": "enabled", "budget_tokens": 3000},
        messages=[{"role": "user", "content": step2_prompt}]
    )

    icp_thinking = ""
    icp_text = ""
    for block in r2.content:
        if block.type == "thinking":
            icp_thinking = block.thinking
        elif block.type == "text":
            icp_text = block.text

    # ─────────────────────────────────────────────────────────────────────
    # STEP 3 — Write the partner brief
    # ─────────────────────────────────────────────────────────────────────
    step3_prompt = f"""
{context}

STEP 1 RESULTS:
{classification_text}

STEP 2 ICP PROFILE:
{icp_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK — STEP 3: WRITE THE PARTNER BRIEF
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Write the weekly intelligence brief Lucio sends to {partner_name}'s 
credit program manager. Follow this structure exactly:

---
LUCIO WEEKLY BRIEF — {partner_name}
Week of March 23, 2026

📊 THIS WEEK'S SNAPSHOT
- Approval rate: {funnel['approval_rate_pct']}% of credit requests approved
- Revenue share earned from active portfolio: ${total_rev_share:,.2f}
- Active financing relationships: {active_count} merchants

🌟 YOUR TOP PERFORMERS THIS WEEK
[List the top 3–5 performers. For each: name, GMV uplift %, 
repayment pace, and one human sentence on what makes them stand out.
Reference real merchants from the data — make it feel like the Francisco story.]

🧬 WHAT YOUR WINNERS HAVE IN COMMON
[4–5 bullet points from the ICP — concrete and actionable.
Give numbers. "12+ months on platform" not "established merchants".]

💡 USE THIS TO GROW YOUR PROGRAM
[2–3 sentences telling the partner how to use this profile as a filter
when deciding which merchants to show the credit offer to next.
Specific and direct — not generic advice.]
---

Tone: professional but warm. Data-driven but human. Write in English.
Output ONLY the brief — nothing before or after it.
"""

    r3 = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": step3_prompt}]
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


# ── Run directly from terminal ────────────────────────────────────────────
if __name__ == "__main__":
    print("Loading merchant data...")
    data = load_data()
    print(f"Running Lucio for {data['partner_name']}...")
    print("This will take 30–60 seconds — calling Claude API 3 times.\n")

    result = run_lucio(data)

    SEP = "═" * 60

    print(f"\n{SEP}")
    print("STEP 1 — CHAIN OF THOUGHT: CLASSIFICATION")
    print(SEP)
    print(result["classification_thinking"])

    print(f"\n{SEP}")
    print("STEP 1 — CLASSIFICATION RESULTS")
    print(SEP)
    print(result["classification_text"])

    print(f"\n{SEP}")
    print("STEP 2 — CHAIN OF THOUGHT: ICP BUILDING")
    print(SEP)
    print(result["icp_thinking"])

    print(f"\n{SEP}")
    print("STEP 2 — ICP PROFILE")
    print(SEP)
    print(result["icp_text"])

    print(f"\n{SEP}")
    print("STEP 3 — PARTNER BRIEF")
    print(SEP)
    print(result["brief"])
