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
    partner_name   = data["partner_name"]
    partner_id     = data["partner_id"]
    rev_share_rate = data["rev_share_rate"]
    funnel         = data["funnel"]
    merchants      = data["merchants"]

    total_rev_share = sum(m["partner_revenue_share"] for m in merchants)
    active_count    = sum(1 for m in merchants if m["financing_status"] == "ACTIVE")

    context = f"""
You are Lucio, a partner intelligence agent built by R2 — a revenue-based
financing company operating across Latin America.

R2 already runs Arturo, a collections agent that monitors merchants showing
risk signals (repayment_pace_ratio < 0.8 or repayment_consistency = low)
and intervenes before default. Arturo owns that segment entirely.

Your role is the opposite. You operate EXCLUSIVELY on merchants that are
healthy and thriving — those Arturo has no reason to touch. Your filter:
  - repayment_pace_ratio >= 1.1  (paying faster than projected)
  - repayment_consistency = high
  - financing_status in [ACTIVE, PAID]

Your job: analyze thriving merchants, identify what makes them succeed
BEFORE they took credit (pre-credit profile), and produce a concise
weekly digest for the partner's credit program manager.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PARTNER CONTEXT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Partner: {partner_name} (ID: {partner_id})
Revenue share rate: {rev_share_rate * 100:.1f}% of each loan amount
Total revenue share earned: ${total_rev_share:,.2f}
Active financing relationships: {active_count}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FUNNEL DATA — last 90 days
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total applications:  {funnel['total_applications']}
Approved:            {funnel['total_approved']} ({funnel['approval_rate_pct']}%)
Denied:              {funnel['total_denied']}
Top denial reasons:
{json.dumps(funnel['top_denial_reasons'], indent=2)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MERCHANT PORTFOLIO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{json.dumps(merchants, indent=2)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FIELD DEFINITIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
gross_sales_pre_avg_monthly  — avg monthly sales BEFORE credit (historical baseline)
gross_sales_90d_post         — total sales in first 90 days AFTER disbursement
gross_sales_uplift_pct_vs_avg — % change: post-credit monthly avg vs pre-credit avg
gross_sales_trend            — slope of monthly sales trend before credit
                               positive = already growing, negative = declining
avg_order_size               — average ticket per order on the platform
repayment_pace_ratio         — actual repayment speed / projected speed
                               > 1.2 = paying much faster (merchant thriving)
                               1.0   = exactly on track
                               < 0.8 = paying slower (Arturo territory)
repayment_consistency        — regularity of daily repayment (high/medium/low)
refund_rate                  — % of orders refunded (>5% is a warning sign)
has_direct_gross_sales       — true = exact sales data from partner
                               false = estimated from repayment amount
total_prior_credits          — fully repaid R2 loans before this one
is_first_credit              — is this their first loan with R2?
active_listings              — number of menu/product items on platform
zero_sales_days_last_90d     — days with no sales in 90d window pre-credit
avg_monthly_txn_count        — number of orders per month
financing_status             — ACTIVE, PAID, PAUSED
"""

    # ── STEP 1: Classify merchants ────────────────────────────
    step1 = f"""
{context}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK — STEP 1: CLASSIFY EVERY MERCHANT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Go through every merchant one by one.

First check Arturo's territory:
  repayment_pace_ratio < 0.8 OR repayment_consistency = low
  OR financing_status = PAUSED → mark ARTURO TERRITORY, skip.

For the rest classify as:

  TOP PERFORMER — all must be true:
    · gross_sales_uplift_pct_vs_avg >= 25%
    · repayment_pace_ratio >= 1.1
    · repayment_consistency = high
    · financing_status in [ACTIVE, PAID]

  NEUTRAL — healthy but not a standout

For each merchant state:
  1. Classification and why
  2. The exact numbers that drove the decision
  3. One standout signal if any

End with a clean summary list:
  TOP PERFORMERS: [merchant_id — name]
  NEUTRAL: [merchant_id — name]
  ARTURO TERRITORY: [merchant_id — name]
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

    # ── STEP 2: Build pre-credit ICP ─────────────────────────
    step2 = f"""
{context}

STEP 1 RESULTS:
{classification_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK — STEP 2: BUILD THE PRE-CREDIT ICP PROFILE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Using ONLY the TOP PERFORMERS from Step 1, extract the profile
these merchants had BEFORE they ever took a loan with R2.

This is critical: the partner needs to find MORE merchants that
look like this BEFORE credit — not after. The goal is to identify
the operational signals that predict success with financing.

Analyze using PRE-CREDIT fields only:
  - gross_sales_pre_avg_monthly, gross_sales_pre_90d, gross_sales_pre_180d
  - gross_sales_trend (was it already growing?)
  - platform_join_date / months_
cat > agent.py << 'EOF'
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
    partner_name   = data["partner_name"]
    partner_id     = data["partner_id"]
    rev_share_rate = data["rev_share_rate"]
    funnel         = data["funnel"]
    merchants      = data["merchants"]

    total_rev_share = sum(m["partner_revenue_share"] for m in merchants)
    active_count    = sum(1 for m in merchants if m["financing_status"] == "ACTIVE")

    context = f"""
You are Lucio, a partner intelligence agent built by R2 — a revenue-based
financing company operating across Latin America.

R2 already runs Arturo, a collections agent that monitors merchants showing
risk signals (repayment_pace_ratio < 0.8 or repayment_consistency = low)
and intervenes before default. Arturo owns that segment entirely.

Your role is the opposite. You operate EXCLUSIVELY on merchants that are
healthy and thriving — those Arturo has no reason to touch. Your filter:
  - repayment_pace_ratio >= 1.1  (paying faster than projected)
  - repayment_consistency = high
  - financing_status in [ACTIVE, PAID]

Your job: analyze thriving merchants, identify what makes them succeed
BEFORE they took credit (pre-credit profile), and produce a concise
weekly digest for the partner's credit program manager.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PARTNER CONTEXT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Partner: {partner_name} (ID: {partner_id})
Revenue share rate: {rev_share_rate * 100:.1f}% of each loan amount
Total revenue share earned: ${total_rev_share:,.2f}
Active financing relationships: {active_count}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FUNNEL DATA — last 90 days
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total applications:  {funnel['total_applications']}
Approved:            {funnel['total_approved']} ({funnel['approval_rate_pct']}%)
Denied:              {funnel['total_denied']}
Top denial reasons:
{json.dumps(funnel['top_denial_reasons'], indent=2)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MERCHANT PORTFOLIO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{json.dumps(merchants, indent=2)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FIELD DEFINITIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
gross_sales_pre_avg_monthly  — avg monthly sales BEFORE credit (historical baseline)
gross_sales_90d_post         — total sales in first 90 days AFTER disbursement
gross_sales_uplift_pct_vs_avg — % change: post-credit monthly avg vs pre-credit avg
gross_sales_trend            — slope of monthly sales trend before credit
                               positive = already growing, negative = declining
avg_order_size               — average ticket per order on the platform
repayment_pace_ratio         — actual repayment speed / projected speed
                               > 1.2 = paying much faster (merchant thriving)
                               1.0   = exactly on track
                               < 0.8 = paying slower (Arturo territory)
repayment_consistency        — regularity of daily repayment (high/medium/low)
refund_rate                  — % of orders refunded (>5% is a warning sign)
has_direct_gross_sales       — true = exact sales data from partner
                               false = estimated from repayment amount
total_prior_credits          — fully repaid R2 loans before this one
is_first_credit              — is this their first loan with R2?
active_listings              — number of menu/product items on platform
zero_sales_days_last_90d     — days with no sales in 90d window pre-credit
avg_monthly_txn_count        — number of orders per month
financing_status             — ACTIVE, PAID, PAUSED
"""

    # ── STEP 1: Classify merchants ────────────────────────────
    step1 = f"""
{context}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK — STEP 1: CLASSIFY EVERY MERCHANT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Go through every merchant one by one.

First check Arturo's territory:
  repayment_pace_ratio < 0.8 OR repayment_consistency = low
  OR financing_status = PAUSED → mark ARTURO TERRITORY, skip.

For the rest classify as:

  TOP PERFORMER — all must be true:
    · gross_sales_uplift_pct_vs_avg >= 25%
    · repayment_pace_ratio >= 1.1
    · repayment_consistency = high
    · financing_status in [ACTIVE, PAID]

  NEUTRAL — healthy but not a standout

For each merchant state:
  1. Classification and why
  2. The exact numbers that drove the decision
  3. One standout signal if any

End with a clean summary list:
  TOP PERFORMERS: [merchant_id — name]
  NEUTRAL: [merchant_id — name]
  ARTURO TERRITORY: [merchant_id — name]
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

    # ── STEP 2: Build pre-credit ICP ─────────────────────────
    step2 = f"""
{context}

STEP 1 RESULTS:
{classification_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK — STEP 2: BUILD THE PRE-CREDIT ICP PROFILE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Using ONLY the TOP PERFORMERS from Step 1, extract the profile
these merchants had BEFORE they ever took a loan with R2.

This is critical: the partner needs to find MORE merchants that
look like this BEFORE credit — not after. The goal is to identify
the operational signals that predict success with financing.

Analyze using PRE-CREDIT fields only:
  - gross_sales_pre_avg_monthly, gross_sales_pre_90d, gross_sales_pre_180d
  - gross_sales_trend (was it already growing?)
  - platform_join_date / months_on_platform
  - active_listings
  - avg_order_size
  - refund_rate
  - zero_sales_days_last_90d
  - avg_monthly_txn_count
  - customer_rating
  - segment, business_type, country
  - total_prior_credits (had they borrowed before?)

For each dimension give:
  - What top performers had in common BEFORE credit
  - The specific threshold that separates them from neutral/underperforming
  - How this differs from merchants that are NOT top performers

End with a SUMMARY ICP in plain language:
"Before taking their first R2 loan, your top performers looked like this: [description]"

This summary will be used directly in the partner digest.
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

    # ── STEP 3: Write the weekly digest ──────────────────────
    step3 = f"""
{context}

STEP 1 RESULTS:
{classification_text}

STEP 2 PRE-CREDIT ICP:
{icp_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK — STEP 3: WRITE THE WEEKLY DIGEST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Write the weekly digest Lucio sends to {partner_name}'s credit
program manager. This person works in marketing or partnerships —
not a data analyst. The digest must be concise, direct, and
motivate one clear action.

FALLBACK RULE: If there are fewer than 3 top performers this week,
do NOT say "it was a slow week." Instead use the section:
"Your best performers so far look like this — find more like them"
and show the historical ICP profile.

Follow this exact structure:

---
LUCIO WEEKLY DIGEST — {partner_name}
Week of {__import__('datetime').datetime.now().strftime('%B %d, %Y')}

📊 YOUR PROGRAM THIS WEEK
- Approval rate: {funnel['approval_rate_pct']}% of credit requests approved
- Total revenue share earned: ${total_rev_share:,.2f}
- Active financing relationships: {active_count} merchants
- [Weekly gross sales: use the sum of gross_sales_90d_post/3 for active merchants as proxy]
- [Weekly sales consistency: % of top performers with repayment_consistency = high]

🌟 THIS WEEK'S TOP PERFORMERS
[List top 3-5 performers. For each:
  - Name, segment, city
  - Gross sales uplift % vs their pre-credit average
  - Repayment pace ratio — paying Xx faster than projected
  - One human sentence on what makes them stand out]

[IF fewer than 3 top performers use fallback:]
YOUR BEST PERFORMERS SO FAR LOOK LIKE THIS — FIND MORE LIKE THEM
[Show historical top performers with same format]

🧬 WHAT YOUR WINNERS LOOKED LIKE BEFORE CREDIT
[4-5 bullet points from the PRE-CREDIT ICP — concrete and specific.
Numbers only. "14+ months on platform" not "established merchants".
Make it a checklist a marketing manager can use to filter merchants.]

💡 USE THIS TO GROW YOUR PROGRAM
Target your credit offers to merchants hitting these operational
benchmarks — they're the ones already demonstrating the cashflow
consistency and growth trajectory that predicts success with
financing. Dark kitchens meeting these criteria should be your
first priority, followed by established restaurants with 15+ months
tenure. Skip merchants with recent inconsistent sales patterns or
ratings below 4.5 stars.

Ready to identify these merchants in your platform?
Reach out to your R2 account manager.
---

Tone: professional but warm. Written for a marketing/partnerships
person — not a data analyst. In English. Output ONLY the digest.
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
    print("Loading merchant data...")
    data = load_data()
    print(f"Running Lucio for {data['partner_name']}...")
    print("Calling Claude API 3 times (~45 seconds)\n")
    result = run_lucio(data)
    SEP = "═" * 60
    print(f"\n{SEP}\nSTEP 1 — CHAIN OF THOUGHT\n{SEP}")
    print(result["classification_thinking"])
    print(f"\n{SEP}\nSTEP 1 — CLASSIFICATION\n{SEP}")
    print(result["classification_text"])
    print(f"\n{SEP}\nSTEP 2 — ICP REASONING\n{SEP}")
    print(result["icp_thinking"])
    print(f"\n{SEP}\nSTEP 2 — PRE-CREDIT ICP\n{SEP}")
    print(result["icp_text"])
    print(f"\n{SEP}\nSTEP 3 — WEEKLY DIGEST\n{SEP}")
    print(result["brief"])
