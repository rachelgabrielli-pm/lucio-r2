"""
db.py — Database schema and connection
SQLite for prototype. In production: PostgreSQL.
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "lucio.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()

    # ── Partners ─────────────────────────────────────────────
    c.execute("""
    CREATE TABLE IF NOT EXISTS partners (
        partner_id        INTEGER PRIMARY KEY,
        partner_name      TEXT NOT NULL,
        rev_share_rate    REAL NOT NULL DEFAULT 0.025,
        contact_name      TEXT,
        contact_whatsapp  TEXT,
        contact_email     TEXT,
        created_at        TEXT DEFAULT (date('now'))
    )
    """)

    # ── Merchants ─────────────────────────────────────────────
    c.execute("""
    CREATE TABLE IF NOT EXISTS merchants (
        merchant_id           TEXT PRIMARY KEY,
        partner_id            INTEGER NOT NULL,
        merchant_name         TEXT NOT NULL,
        segment               TEXT NOT NULL,
        country               TEXT NOT NULL,
        city                  TEXT NOT NULL,
        business_type         TEXT NOT NULL,
        months_on_platform    INTEGER NOT NULL,
        active_listings       INTEGER,
        customer_rating       REAL,
        avg_txn_size          REAL,
        refund_rate           REAL,
        sales_consistency_score INTEGER,
        zero_sales_days_last_90d INTEGER,
        avg_monthly_txn_count INTEGER,
        gmv_trend_coefficient REAL,
        peak_season_months    TEXT,
        created_at            TEXT DEFAULT (date('now')),
        FOREIGN KEY (partner_id) REFERENCES partners(partner_id)
    )
    """)

    # ── Financings ────────────────────────────────────────────
    c.execute("""
    CREATE TABLE IF NOT EXISTS financings (
        financing_id          TEXT PRIMARY KEY,
        merchant_id           TEXT NOT NULL,
        partner_id            INTEGER NOT NULL,
        loan_amount           REAL NOT NULL,
        total_repayment_amount REAL NOT NULL,
        repayment_rate        REAL NOT NULL,
        fixed_fee             REAL NOT NULL,
        status                TEXT NOT NULL DEFAULT 'ACTIVE',
        disbursement_date     TEXT NOT NULL,
        expected_days         INTEGER NOT NULL,
        days_since_disbursement INTEGER NOT NULL,
        amount_repaid         REAL NOT NULL DEFAULT 0,
        is_first_credit       INTEGER NOT NULL DEFAULT 1,
        total_prior_credits   INTEGER NOT NULL DEFAULT 0,
        first_credit_date     TEXT,
        partner_revenue_share REAL NOT NULL,
        -- Pre-credit gross sales snapshot (sent by partner at application)
        gross_sales_pre_30d   REAL,
        gross_sales_pre_90d   REAL,
        gross_sales_pre_180d  REAL,
        gross_sales_pre_avg_monthly REAL,
        created_at            TEXT DEFAULT (date('now')),
        FOREIGN KEY (merchant_id) REFERENCES merchants(merchant_id),
        FOREIGN KEY (partner_id)  REFERENCES partners(partner_id)
    )
    """)

    # ── Daily Sales ───────────────────────────────────────────
    # One row per merchant per day — the continuous stream
    # that comes from collection_created events.
    # gross_sales: direct if partner sends it, else reverse-calculated
    # has_direct_gross_sales: true if partner reported it directly
    c.execute("""
    CREATE TABLE IF NOT EXISTS daily_sales (
        id                    INTEGER PRIMARY KEY AUTOINCREMENT,
        merchant_id           TEXT NOT NULL,
        partner_id            INTEGER NOT NULL,
        financing_id          TEXT NOT NULL,
        sale_date             TEXT NOT NULL,
        gross_sales           REAL NOT NULL,
        repayment_amount      REAL NOT NULL,
        has_direct_gross_sales INTEGER NOT NULL DEFAULT 0,
        created_at            TEXT DEFAULT (datetime('now')),
        UNIQUE(merchant_id, sale_date),
        FOREIGN KEY (merchant_id)  REFERENCES merchants(merchant_id),
        FOREIGN KEY (financing_id) REFERENCES financings(financing_id)
    )
    """)

    # ── Credit Applications (funnel) ──────────────────────────
    c.execute("""
    CREATE TABLE IF NOT EXISTS credit_applications (
        application_id   INTEGER PRIMARY KEY AUTOINCREMENT,
        partner_id       INTEGER NOT NULL,
        merchant_id      TEXT,
        applied_at       TEXT NOT NULL,
        status           TEXT NOT NULL,
        denial_reason    TEXT,
        FOREIGN KEY (partner_id) REFERENCES partners(partner_id)
    )
    """)

    conn.commit()
    conn.close()
    print("✓ Database schema created.")

if __name__ == "__main__":
    init_db()
