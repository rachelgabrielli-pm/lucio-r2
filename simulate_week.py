"""
simulate_week.py
Simulates one new week of data:
1. Inserts new daily_sales + repayments for active merchants
2. Updates amount_repaid in financings
3. Creates 2-3 new credit applications (some approved, some denied)
4. For approved applications, creates new financing disbursements
"""
import sqlite3
import random
import json
import os
import sys
from datetime import datetime, timedelta

sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))
from db import get_conn

random.seed()
TODAY = datetime.now().date()

# Segments and cities for new synthetic merchants
NEW_MERCHANT_POOL = [
    {"name": "Taqueria El Patron", "segment": "restaurant", "city": "Ciudad de Mexico", "country": "MX", "business_type": "natural"},
    {"name": "Dark Kitchen CDMX", "segment": "dark_kitchen", "city": "Ciudad de Mexico", "country": "MX", "business_type": "juridico"},
    {"name": "Pizzeria Bella Roma", "segment": "restaurant", "city": "Guadalajara", "country": "MX", "business_type": "natural"},
    {"name": "Burger Lab Monterrey", "segment": "dark_kitchen", "city": "Monterrey", "country": "MX", "business_type": "juridico"},
    {"name": "Sushi Express Bogota", "segment": "restaurant", "city": "Bogota", "country": "CO", "business_type": "juridico"},
    {"name": "Dark Kitchen Santiago", "segment": "dark_kitchen", "city": "Santiago", "country": "CL", "business_type": "juridico"},
    {"name": "Cevicheria Lima", "segment": "restaurant", "city": "Lima", "country": "PE", "business_type": "natural"},
    {"name": "Arepas Don Pedro", "segment": "restaurant", "city": "Medellin", "country": "CO", "business_type": "natural"},
]

DENIAL_REASONS = ["insufficient_sales_history", "high_refund_rate", "irregular_sales_pattern", "kyc_incomplete"]

def simulate_new_week():
    conn = get_conn()
    print(f"\nSimulating new week of data ending {TODAY}...\n")

    # ── 1. Insert daily sales for active merchants ────────────────────────
    financings = conn.execute("""
        SELECT f.financing_id, f.merchant_id, f.partner_id,
               f.repayment_rate, f.total_repayment_amount,
               f.amount_repaid, f.expected_days, f.disbursement_date,
               f.gross_sales_pre_avg_monthly
        FROM financings f
        WHERE f.status = 'ACTIVE'
    """).fetchall()

    rows_inserted   = 0
    total_repayment = 0

    for f in financings:
        merchant_id    = f["merchant_id"]
        financing_id   = f["financing_id"]
        partner_id     = f["partner_id"]
        repayment_rate = f["repayment_rate"]
        pre_avg        = f["gross_sales_pre_avg_monthly"] or 5000
        base_daily     = pre_avg / 30 * 1.3

        has_direct = conn.execute(
            "SELECT MAX(has_direct_gross_sales) as hd FROM daily_sales WHERE merchant_id = ?",
            (merchant_id,)
        ).fetchone()["hd"] or 0

        for i in range(7):
            sale_date = TODAY - timedelta(days=6-i)
            exists = conn.execute(
                "SELECT 1 FROM daily_sales WHERE merchant_id = ? AND sale_date = ?",
                (merchant_id, sale_date.isoformat())
            ).fetchone()
            if exists:
                continue

            variance    = random.uniform(0.85, 1.20)
            gross_sales = round(base_daily * variance, 2)
            repayment   = round(gross_sales * repayment_rate, 2)

            conn.execute("""
                INSERT OR IGNORE INTO daily_sales
                    (merchant_id, partner_id, financing_id,
                     sale_date, gross_sales, repayment_amount,
                     has_direct_gross_sales)
                VALUES (?,?,?,?,?,?,?)
            """, (merchant_id, partner_id, financing_id,
                  sale_date.isoformat(), gross_sales, repayment, has_direct))

            total_repayment += repayment
            rows_inserted += 1

        # Update financings
        disbursement = datetime.strptime(f["disbursement_date"], "%Y-%m-%d").date()
        days_since   = (TODAY - disbursement).days

        new_amount_repaid = conn.execute(
            "SELECT COALESCE(SUM(repayment_amount), 0) as total FROM daily_sales WHERE financing_id = ?",
            (financing_id,)
        ).fetchone()["total"]

        new_status = "PAID" if new_amount_repaid >= f["total_repayment_amount"] else "ACTIVE"

        conn.execute("""
            UPDATE financings
            SET amount_repaid = ?, days_since_disbursement = ?, status = ?
            WHERE financing_id = ?
        """, (round(new_amount_repaid, 2), days_since, new_status, financing_id))

    print(f"  Inserted {rows_inserted} new daily sales rows")
    print(f"  Total new repayments processed: ${total_repayment:,.2f}")

    # ── 2. Create 2-3 new credit applications ────────────────────────────
    partner = conn.execute("SELECT * FROM partners WHERE partner_id = 1001").fetchone()
    partner_id     = partner["partner_id"]
    rev_share_rate = partner["rev_share_rate"]

    # How many existing merchants
    existing_count = conn.execute("SELECT COUNT(*) as n FROM merchants").fetchone()["n"]

    n_new = random.randint(2, 3)
    approved_count = 0
    denied_count   = 0

    for i in range(n_new):
        # Pick a random merchant profile from the pool
        pool_item = random.choice(NEW_MERCHANT_POOL)

        # Generate new merchant ID
        new_mid = f"1001-{existing_count + i + 1:03d}"

        # Check if already exists
        exists = conn.execute(
            "SELECT 1 FROM merchants WHERE merchant_id = ?", (new_mid,)
        ).fetchone()
        if exists:
            continue

        # Generate realistic pre-credit profile
        months_on_platform = random.randint(8, 24)
        join_date = (TODAY - timedelta(days=months_on_platform * 30)).isoformat()
        gross_sales_pre_monthly = random.uniform(4000, 18000)
        gross_sales_trend       = random.uniform(-0.02, 0.12)
        avg_order_size          = random.uniform(18, 65)
        refund_rate             = random.uniform(0.01, 0.06)
        customer_rating         = random.uniform(3.8, 5.0)
        active_listings         = random.randint(8, 35)
        avg_monthly_txn_count   = random.randint(80, 400)
        zero_sales_days         = random.randint(0, 12)

        # Decide approval based on profile quality
        # Guarantee at least 1 approval per simulation run
        force_approve = (approved_count == 0 and i == n_new - 1)
        approved = force_approve or (
            months_on_platform >= 10
            and gross_sales_pre_monthly >= 5000
            and refund_rate <= 0.05
            and customer_rating >= 4.0
            and zero_sales_days <= 8
        )

        # Insert merchant
        conn.execute("""
            INSERT OR IGNORE INTO merchants (
                merchant_id, partner_id, merchant_name, segment,
                country, city, business_type, platform_join_date,
                active_listings, customer_rating, avg_order_size,
                refund_rate, zero_sales_days_last_90d,
                avg_monthly_txn_count, gross_sales_trend, peak_season_months
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            new_mid, partner_id, pool_item["name"], pool_item["segment"],
            pool_item["country"], pool_item["city"], pool_item["business_type"],
            join_date, active_listings, round(customer_rating, 1),
            round(avg_order_size, 2), round(refund_rate, 3),
            zero_sales_days, avg_monthly_txn_count,
            round(gross_sales_trend, 4), json.dumps([])
        ))

        # Insert credit application
        status        = "APPROVED" if approved else "DENIED"
        denial_reason = None if approved else random.choice(DENIAL_REASONS)

        conn.execute("""
            INSERT INTO credit_applications
                (partner_id, merchant_id, applied_at, status, denial_reason)
            VALUES (?,?,?,?,?)
        """, (partner_id, new_mid, TODAY.isoformat(), status, denial_reason))

        if approved:
            # Create financing disbursement
            loan_amount    = round(gross_sales_pre_monthly * random.uniform(0.8, 1.5), 2)
            fixed_fee      = round(loan_amount * 0.17, 2)
            total_repay    = round(loan_amount + fixed_fee, 2)
            repayment_rate = 0.14
            expected_days  = random.randint(60, 120)
            rev_share      = round(loan_amount * rev_share_rate, 2)

            financing_id = f"FIN-{new_mid}"
            conn.execute("""
                INSERT OR IGNORE INTO financings (
                    financing_id, merchant_id, partner_id,
                    loan_amount, total_repayment_amount, repayment_rate,
                    fixed_fee, status, disbursement_date, expected_days,
                    days_since_disbursement, amount_repaid,
                    is_first_credit, total_prior_credits,
                    partner_revenue_share,
                    gross_sales_pre_30d, gross_sales_pre_90d,
                    gross_sales_pre_180d, gross_sales_pre_avg_monthly
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                financing_id, new_mid, partner_id,
                loan_amount, total_repay, repayment_rate,
                fixed_fee, "ACTIVE", TODAY.isoformat(), expected_days,
                0, 0.0, 1, 0, rev_share,
                round(gross_sales_pre_monthly * 0.95, 2),
                round(gross_sales_pre_monthly * 2.9, 2),
                round(gross_sales_pre_monthly * 5.8, 2),
                round(gross_sales_pre_monthly, 2)
            ))
            approved_count += 1
            print(f"  New merchant approved: {pool_item['name']} ({new_mid}) — loan ${loan_amount:,.2f}, rev share ${rev_share:,.2f}")
        else:
            denied_count += 1
            print(f"  New merchant denied: {pool_item['name']} ({new_mid}) — reason: {denial_reason}")

    conn.commit()
    conn.close()

    print(f"\n  New applications: {n_new} ({approved_count} approved, {denied_count} denied)")
    print(f"  Database updated through {TODAY}")
    print("\nNew week simulated successfully.")

if __name__ == "__main__":
    simulate_new_week()
