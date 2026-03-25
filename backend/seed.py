"""
seed.py — Populates the database with 90 days of realistic data.
Simulates the R2 data warehouse: merchants, financings, and daily
collection events updated as merchants sell on the partner platform.
Run once to set up. Run again to reset.
"""
import sqlite3
import json
import os
import random
from datetime import datetime, timedelta
from db import get_conn, init_db, DB_PATH

random.seed(42)

TODAY = datetime.now().date()
START = TODAY - timedelta(days=90)

# ── Load merchant profiles from existing JSON ─────────────────────────────
JSON_PATH = os.path.join(os.path.dirname(__file__), "../data/merchants.json")

def load_source():
    with open(JSON_PATH) as f:
        return json.load(f)

def reset_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("✓ Old database removed.")
    init_db()

def seed_partner(conn, data):
    conn.execute("""
    INSERT OR REPLACE INTO partners
        (partner_id, partner_name, rev_share_rate,
         contact_name, contact_whatsapp, contact_email)
    VALUES (?,?,?,?,?,?)
    """, (
        data["partner_id"],
        data["partner_name"],
        data["rev_share_rate"],
        "Ana Rodrigues",
        "+5511999990001",
        "ana.rodrigues@ubereats.com"
    ))
    print(f"✓ Partner seeded: {data['partner_name']}")

def seed_merchants(conn, merchants):
    for m in merchants:
        conn.execute("""
        INSERT OR REPLACE INTO merchants (
            merchant_id, partner_id, merchant_name, segment,
            country, city, business_type, months_on_platform,
            active_listings, customer_rating, avg_txn_size,
            refund_rate, sales_consistency_score,
            zero_sales_days_last_90d, avg_monthly_txn_count,
            gmv_trend_coefficient, peak_season_months
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            m["merchant_id"], m["partner_id"], m["merchant_name"],
            m["segment"], m["country"], m["city"], m["business_type"],
            m["months_on_platform"], m.get("active_listings"),
            m.get("customer_rating"), m.get("avg_txn_size"),
            m.get("refund_rate"), m.get("sales_consistency_score"),
            m.get("zero_sales_days_last_90d"), m.get("avg_monthly_txn_count"),
            m.get("gmv_trend_coefficient"),
            json.dumps(m.get("peak_season_months", []))
        ))
    print(f"✓ {len(merchants)} merchants seeded.")

def seed_financings(conn, merchants, partner_id):
    for m in merchants:
        financing_id = f"FIN-{m['merchant_id']}"
        conn.execute("""
        INSERT OR REPLACE INTO financings (
            financing_id, merchant_id, partner_id,
            loan_amount, total_repayment_amount, repayment_rate,
            fixed_fee, status, disbursement_date, expected_days,
            days_since_disbursement, amount_repaid,
            is_first_credit, total_prior_credits, first_credit_date,
            partner_revenue_share,
            gross_sales_pre_30d, gross_sales_pre_90d,
            gross_sales_pre_180d, gross_sales_pre_avg_monthly
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            financing_id, m["merchant_id"], partner_id,
            m["loan_amount"], m["total_repayment_amount"],
            0.14,  # repayment rate — % of daily sales
            m["loan_amount"] * 0.17,  # fixed fee ~17%
            m["financing_status"],
            m["disbursement_date"],
            m["expected_days"],
            m["days_since_disbursement"],
            m["amount_repaid"],
            1 if m["is_first_credit"] else 0,
            m["total_prior_credits"],
            m["first_credit_date"],
            m["partner_revenue_share"],
            m["gmv_pre_30d"],
            m["gmv_pre_90d"],
            m["gmv_pre_180d"],
            m["gmv_pre_avg_monthly"]
        ))
    print(f"✓ {len(merchants)} financings seeded.")

def seed_daily_sales(conn, merchants, partner_id):
    """
    Generate 90 days of daily sales for each merchant.
    Uses the merchant's pre-credit avg as baseline, then applies
    their actual uplift trajectory post-disbursement.
    Simulates realistic variance — not every day is the same.
    """
    rows_inserted = 0

    for m in merchants:
        financing_id    = f"FIN-{m['merchant_id']}"
        disbursement    = datetime.strptime(m["disbursement_date"], "%Y-%m-%d").date()
        base_daily      = m["gmv_pre_avg_monthly"] / 30
        post_monthly_avg= m["gmv_90d_post"] / 3  # avg monthly post
        post_daily_avg  = post_monthly_avg / 30
        consistency     = m["sales_consistency_score"] / 100
        zero_days       = m["zero_sales_days_last_90d"]
        has_direct      = m["has_direct_gmv"]
        repayment_rate  = 0.14
        pace            = m["repayment_pace_ratio"]

        # Decide which days have zero sales (based on zero_sales_days profile)
        all_days = [START + timedelta(days=i) for i in range(91)]
        # Only zero-sales days AFTER disbursement are realistic for post-credit
        post_days = [d for d in all_days if d >= disbursement]
        pre_days  = [d for d in all_days if d < disbursement]

        # Sample zero-sales days proportionally
        zero_count = max(0, int(zero_days * (len(post_days) / 90)))
        zero_day_set = set(random.sample(post_days, min(zero_count, len(post_days))))

        for day in all_days:
            # Skip future dates
            if day > TODAY:
                continue

            is_post = day >= disbursement

            if is_post and day in zero_day_set:
                # Zero sales day
                continue

            if is_post:
                # Post-credit: ramp up from base to post_daily_avg
                days_post = (day - disbursement).days
                progress  = min(days_post / m["expected_days"], 1.0)
                target    = base_daily + (post_daily_avg - base_daily) * progress
                # Add realistic daily variance (±20%)
                variance  = random.uniform(0.80, 1.20)
                gross_sales = max(0, target * variance)
            else:
                # Pre-credit: use baseline with variance
                variance    = random.uniform(0.75, 1.25)
                gross_sales = max(0, base_daily * variance)

            gross_sales     = round(gross_sales, 2)
            repayment_amount= round(gross_sales * repayment_rate, 2) if is_post else 0.0

            try:
                conn.execute("""
                INSERT OR IGNORE INTO daily_sales
                    (merchant_id, partner_id, financing_id,
                     sale_date, gross_sales, repayment_amount,
                     has_direct_gross_sales)
                VALUES (?,?,?,?,?,?,?)
                """, (
                    m["merchant_id"], partner_id, financing_id,
                    day.isoformat(), gross_sales, repayment_amount,
                    1 if has_direct else 0
                ))
                rows_inserted += 1
            except Exception as e:
                pass  # UNIQUE constraint — skip duplicates

    print(f"✓ {rows_inserted} daily sales rows seeded.")

def seed_applications(conn, partner_id, funnel):
    """
    Seed credit application history from funnel data.
    Distributes applications over the last 90 days.
    """
    denial_reasons = funnel["top_denial_reasons"]
    total_approved = funnel["total_approved"]
    total_denied   = funnel["total_denied"]

    for i in range(total_approved):
        days_ago = random.randint(0, 90)
        applied_at = (TODAY - timedelta(days=days_ago)).isoformat()
        conn.execute("""
        INSERT INTO credit_applications
            (partner_id, applied_at, status, denial_reason)
        VALUES (?,?,'APPROVED', NULL)
        """, (partner_id, applied_at))

    for i in range(total_denied):
        days_ago = random.randint(0, 90)
        applied_at = (TODAY - timedelta(days=days_ago)).isoformat()
        # Weight denial reasons by their pct
        reasons     = [r["reason"] for r in denial_reasons]
        weights     = [r["pct"] for r in denial_reasons]
        reason      = random.choices(reasons, weights=weights)[0]
        conn.execute("""
        INSERT INTO credit_applications
            (partner_id, applied_at, status, denial_reason)
        VALUES (?,?,'DENIED', ?)
        """, (partner_id, applied_at, reason))

    print(f"✓ {total_approved + total_denied} credit applications seeded.")

def main():
    print("\n🌱 Seeding Lucio database...\n")
    data      = load_source()
    merchants = data["merchants"]
    partner_id= data["partner_id"]
    funnel    = data["funnel"]

    reset_db()
    conn = get_conn()

    try:
        seed_partner(conn, data)
        seed_merchants(conn, merchants)
        seed_financings(conn, merchants, partner_id)
        seed_daily_sales(conn, merchants, partner_id)
        seed_applications(conn, partner_id, funnel)
        conn.commit()
        print("\n✅ Database ready at backend/lucio.db\n")
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    main()
