-- ============================================================
-- Lucio Agent — Merchant Performance Query
-- ============================================================
-- This query runs weekly against R2's data warehouse for a
-- given partner. The Data Fetcher passes :partner_id and
-- :lookback_days as parameters.
--
-- DATA MODEL — TWO MOMENTS:
--
-- MOMENT 1 — Credit application snapshot:
--   Partner pushes full merchant context to R2 when merchant
--   enters the credit form. This includes:
--
--   TRANSACTIONAL HISTORY (from partner platform):
--     - Full GMV history (6-12 months) — not just last 30d
--     - Average monthly GMV
--     - GMV trend coefficient (slope of sales over time)
--     - Monthly transaction count (volume, not just value)
--     - Average transaction size
--     - Sales consistency score (gaps, volatility)
--     - Refund rate (refunds / total transactions)
--     - Peak season indicators
--
--   PLATFORM BEHAVIOR:
--     - Time active on platform (months)
--     - Segment (restaurant / retail / dark_kitchen / gig)
--     - Number of active listings (marketplaces)
--     - Customer rating (where available)
--     - Geographic location
--
--   PII (after TCS_ACCEPTED event):
--     - Legal name, tax ID, business type (Natural/Juridico)
--     - Owner identity, bank account
--
--   NOTE: The public API docs only confirm business_type and
--   external_merchant_id in the TCS_ACCEPTED event payload.
--   The full field set above is inferred from R2's stated
--   underwriting methodology ("transactional and behavioral
--   data", "revenue consistency", "platform engagement").
--
-- MOMENT 2 — Post-disbursement continuous stream:
--   Partner reports each repayment deduction as it occurs.
--   collection_created events contain:
--
--   CONFIRMED fields:
--     - repayment_amount (always present)
--     - remaining_balance (always present)
--     - collected_at (timestamp)
--
--   OPTIONAL field (LUCIO-ROADMAP-001):
--     - gmv_reported: actual daily gross sales from partner.
--       When present: used directly (exact).
--       When absent: estimated as repayment_amount / rate.
--       Make this required for all new partner integrations.
--
-- ARTURO vs LUCIO — shared data source, different filters:
--   Both agents read from the same merchant_signals view.
--   Arturo filters for risk signals (low consistency, GMV drop).
--   Lucio filters for success signals (high consistency, GMV up).
--   No duplicated pipelines. One materialized view, two lenses.
-- ============================================================

WITH

-- Step 1: Active/paid financings for this partner
partner_financings AS (
    SELECT
        f.financing_id,
        f.external_merchant_id        AS merchant_id,
        f.disbursed_amount            AS loan_amount,
        f.total_repayment_amount,
        f.repayment_rate,
        f.fixed_fee,
        f.currency,
        f.status                      AS financing_status,
        f.created_at                  AS disbursement_date,
        f.due_date,
        f.expected_weeks
    FROM financings f
    WHERE f.partner_id = :partner_id
      AND f.status IN ('ACTIVE', 'PAID')
      AND f.created_at >= NOW() - INTERVAL ':lookback_days days'
),

-- Step 2: Merchant profile + full application snapshot
-- All fields populated from data sent by partner at application time
merchant_info AS (
    SELECT
        mp.external_merchant_id       AS merchant_id,
        mp.name                       AS merchant_name,
        mp.segment,
        mp.country,
        mp.city,
        mp.business_type,             -- Natural / Juridico

        -- Platform tenure
        mp.months_on_platform,

        -- Full GMV history (sent by partner at application)
        mp.gmv_avg_monthly,           -- average over full history
        mp.gmv_last_30d,              -- last 30 days pre-application
        mp.gmv_last_90d,              -- last 90 days pre-application
        mp.gmv_last_180d,             -- last 180 days pre-application
        mp.gmv_trend_coefficient,     -- slope: positive = growing

        -- Transaction behavior
        mp.avg_monthly_txn_count,     -- number of transactions/month
        mp.avg_txn_size,              -- average ticket size
        mp.refund_rate,               -- refunds / total txns (0-1)
        mp.sales_consistency_score,   -- 0-100, higher = more regular
        mp.zero_sales_days_last_90d,  -- days with no sales in 90d window

        -- Platform engagement
        mp.active_listings,           -- products/menu items listed
        mp.customer_rating,           -- platform rating (nullable)
        mp.peak_season_months         -- e.g. [11, 12] for Dec merchants

    FROM merchant_profiles mp
    WHERE mp.partner_id = :partner_id
),

-- Step 3: GMV BEFORE disbursement
-- Source: snapshot sent at application — always a direct partner report
gmv_pre AS (
    SELECT
        pf.merchant_id,
        mi.gmv_last_30d               AS gmv_pre_30d,
        mi.gmv_last_90d               AS gmv_pre_90d,
        mi.gmv_last_180d              AS gmv_pre_180d,
        mi.gmv_avg_monthly            AS gmv_pre_avg_monthly
    FROM partner_financings pf
    JOIN merchant_info mi ON mi.merchant_id = pf.merchant_id
),

-- Step 4: GMV AFTER disbursement
-- Source: daily collection events
-- Priority: gmv_reported (direct) > reverse-calculated (estimated)
-- See LUCIO-ROADMAP-001 to make gmv_reported mandatory
gmv_post AS (
    SELECT
        pf.merchant_id,
        SUM(CASE
            WHEN c.collected_at BETWEEN pf.disbursement_date
                                    AND (pf.disbursement_date + INTERVAL '30 days')
            THEN COALESCE(
                c.gmv_reported,
                c.repayment_amount / NULLIF(pf.repayment_rate / 100.0, 0)
            ) END)                        AS gmv_30d_post,
        SUM(CASE
            WHEN c.collected_at BETWEEN pf.disbursement_date
                                    AND (pf.disbursement_date + INTERVAL '90 days')
            THEN COALESCE(
                c.gmv_reported,
                c.repayment_amount / NULLIF(pf.repayment_rate / 100.0, 0)
            ) END)                        AS gmv_90d_post,
        -- Count of days with sales post-disbursement (activity signal)
        COUNT(DISTINCT DATE(c.collected_at))  AS active_sales_days_post,
        -- Flag: is this merchant's GMV exact or estimated?
        BOOL_OR(c.gmv_reported IS NOT NULL)   AS has_direct_gmv
    FROM partner_financings pf
    JOIN collections c
      ON c.financing_id = pf.financing_id
     AND c.collected_at >= pf.disbursement_date
    GROUP BY pf.merchant_id
),

-- Step 5: Repayment health
-- Shared signal with Arturo — same computation, different use
-- Arturo: low consistency = intervention trigger
-- Lucio:  high consistency = success signal for ICP
repayment_health AS (
    SELECT
        c.financing_id,
        AVG(
            c.repayment_amount /
            NULLIF(pf.total_repayment_amount /
                   NULLIF(pf.expected_weeks, 0), 0) * 100
        )                                 AS repayment_rate_avg,
        CASE
            WHEN STDDEV(c.repayment_amount) /
                 NULLIF(AVG(c.repayment_amount), 0) < 0.2  THEN 'high'
            WHEN STDDEV(c.repayment_amount) /
                 NULLIF(AVG(c.repayment_amount), 0) < 0.5  THEN 'medium'
            ELSE                                                'low'
        END                               AS repayment_consistency,
        -- Weeks since last missed or partial payment
        MAX(CASE
            WHEN c.repayment_amount >= (
                pf.total_repayment_amount / NULLIF(pf.expected_weeks, 0) * 0.9
            ) THEN EXTRACT(WEEK FROM c.collected_at)
            ELSE NULL
        END)                              AS last_healthy_payment_week
    FROM collections c
    JOIN partner_financings pf
      ON pf.financing_id = c.financing_id
    GROUP BY c.financing_id, pf.total_repayment_amount, pf.expected_weeks
),

-- Step 6: Partner revenue from this merchant
partner_revenue AS (
    SELECT
        pf.merchant_id,
        pf.loan_amount * pc.rev_share_rate  AS partner_revenue_share
    FROM partner_financings pf
    JOIN partner_config pc ON pc.partner_id = :partner_id
)

-- ============================================================
-- Final output — one row per merchant, all signals combined
-- Ordered by GMV uplift desc so top performers appear first
-- ============================================================
SELECT
    -- Identity
    mi.merchant_id,
    mi.merchant_name,
    mi.segment,
    mi.country,
    mi.city,
    mi.business_type,
    mi.months_on_platform,

    -- Loan
    pf.loan_amount,
    pf.disbursement_date,
    pf.financing_status,

    -- Pre-credit GMV baseline (full history)
    ROUND(gp.gmv_pre_30d, 2)              AS gmv_pre_30d,
    ROUND(gp.gmv_pre_90d, 2)             AS gmv_pre_90d,
    ROUND(gp.gmv_pre_180d, 2)            AS gmv_pre_180d,
    ROUND(gp.gmv_pre_avg_monthly, 2)     AS gmv_pre_avg_monthly,

    -- Pre-credit behavioral signals
    mi.gmv_trend_coefficient,
    mi.avg_monthly_txn_count,
    mi.avg_txn_size,
    mi.refund_rate,
    mi.sales_consistency_score,
    mi.zero_sales_days_last_90d,
    mi.active_listings,
    mi.customer_rating,
    mi.peak_season_months,

    -- Post-credit GMV (from collection stream)
    ROUND(gpost.gmv_30d_post, 2)         AS gmv_30d_post,
    ROUND(gpost.gmv_90d_post, 2)         AS gmv_90d_post,
    gpost.active_sales_days_post,
    gpost.has_direct_gmv,

    -- Repayment health
    ROUND(rh.repayment_rate_avg, 2)      AS repayment_rate_avg,
    rh.repayment_consistency,
    rh.last_healthy_payment_week,

    -- Partner economics
    ROUND(pr.partner_revenue_share, 2)   AS partner_revenue_share,

    -- Computed uplifts (Lucio's core signals)
    ROUND(
        (gpost.gmv_90d_post - gp.gmv_pre_30d)
        / NULLIF(gp.gmv_pre_30d, 0) * 100
    , 1)                                 AS gmv_uplift_pct_vs_30d,
    ROUND(
        (gpost.gmv_90d_post / 3.0 - gp.gmv_pre_avg_monthly)
        / NULLIF(gp.gmv_pre_avg_monthly, 0) * 100
    , 1)                                 AS gmv_uplift_pct_vs_avg

FROM partner_financings pf
JOIN merchant_info      mi    ON mi.merchant_id    = pf.merchant_id
JOIN gmv_pre            gp    ON gp.merchant_id    = pf.merchant_id
JOIN gmv_post           gpost ON gpost.merchant_id = pf.merchant_id
JOIN repayment_health   rh    ON rh.financing_id   = pf.financing_id
JOIN partner_revenue    pr    ON pr.merchant_id    = pf.merchant_id
ORDER BY gmv_uplift_pct_vs_avg DESC;
