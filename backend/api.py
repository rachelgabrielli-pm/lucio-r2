from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import json, sys, os

sys.path.append(os.path.dirname(__file__))
from db import get_conn

app = FastAPI(title="Lucio Backend", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

TODAY      = datetime.now().date()
WEEK_START = TODAY - timedelta(days=7)

def row_to_dict(row): return dict(row) if row else None
def rows_to_list(rows): return [dict(r) for r in rows]


@app.get("/health")
def health():
    return {"status": "ok", "generated_at": TODAY.isoformat()}


@app.get("/partner/{partner_id}/snapshot")
def get_snapshot(partner_id: int):
    conn = get_conn()
    try:
        partner = row_to_dict(conn.execute(
            "SELECT * FROM partners WHERE partner_id = ?", (partner_id,)
        ).fetchone())
        if not partner:
            raise HTTPException(status_code=404, detail="Partner not found")

        total_rev = conn.execute("""
            SELECT COALESCE(SUM(partner_revenue_share), 0) as total
            FROM financings WHERE partner_id = ? AND status IN ('ACTIVE','PAID')
        """, (partner_id,)).fetchone()["total"]

        funnel = conn.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status='APPROVED' THEN 1 ELSE 0 END) as approved,
                SUM(CASE WHEN status='DENIED'   THEN 1 ELSE 0 END) as denied
            FROM credit_applications WHERE partner_id = ?
        """, (partner_id,)).fetchone()

        approval_rate = round(funnel["approved"] / funnel["total"] * 100, 1) if funnel["total"] > 0 else 0

        denial_reasons = rows_to_list(conn.execute("""
            SELECT denial_reason as reason, COUNT(*) as count
            FROM credit_applications
            WHERE partner_id = ? AND status = 'DENIED' AND denial_reason IS NOT NULL
            GROUP BY denial_reason ORDER BY count DESC LIMIT 4
        """, (partner_id,)).fetchall())

        active_count = conn.execute("""
            SELECT COUNT(*) as n FROM financings
            WHERE partner_id = ? AND status = 'ACTIVE'
        """, (partner_id,)).fetchone()["n"]

        weekly_sales = conn.execute("""
            SELECT
                COUNT(DISTINCT ds.merchant_id) as merchants_selling,
                COALESCE(SUM(ds.gross_sales), 0) as total_gross_sales
            FROM daily_sales ds
            JOIN financings f ON f.financing_id = ds.financing_id
            WHERE ds.partner_id = ? AND ds.sale_date >= ?
              AND f.status IN ('ACTIVE','PAID')
        """, (partner_id, WEEK_START.isoformat())).fetchone()

        days_in_week = (TODAY - WEEK_START).days or 1
        consistent = conn.execute("""
            SELECT COUNT(*) as n FROM (
                SELECT merchant_id FROM daily_sales
                WHERE partner_id = ? AND sale_date >= ? AND gross_sales > 0
                GROUP BY merchant_id HAVING COUNT(DISTINCT sale_date) >= ?
            )
        """, (partner_id, WEEK_START.isoformat(), days_in_week)).fetchone()["n"]

        consistency_rate = round(min(consistent / active_count * 100, 100.0), 1) if active_count > 0 else 0

        return {
            "partner_id":       partner_id,
            "partner_name":     partner["partner_name"],
            "contact_name":     partner["contact_name"],
            "contact_whatsapp": partner["contact_whatsapp"],
            "contact_email":    partner["contact_email"],
            "rev_share_rate":   partner["rev_share_rate"],
            "generated_at":     TODAY.isoformat(),
            "kpis": {
                "total_revenue_share_usd":     round(total_rev, 2),
                "approval_rate_pct":           approval_rate,
                "total_applications":          funnel["total"],
                "total_approved":              funnel["approved"],
                "total_denied":                funnel["denied"],
                "active_merchants":            active_count,
                "weekly_gross_sales_usd":      round(weekly_sales["total_gross_sales"], 2),
                "weekly_consistency_pct":      consistency_rate,
                "merchants_selling_this_week": weekly_sales["merchants_selling"],
            },
            "top_denial_reasons": denial_reasons
        }
    finally:
        conn.close()


@app.get("/partner/{partner_id}/merchants")
def get_merchants(partner_id: int):
    conn = get_conn()
    try:
        merchants = rows_to_list(conn.execute("""
            SELECT
                m.merchant_id, m.merchant_name, m.segment,
                m.country, m.city, m.business_type,
                m.platform_join_date, m.active_listings,
                m.customer_rating, m.avg_order_size,
                m.refund_rate, m.zero_sales_days_last_90d,
                m.avg_monthly_txn_count, m.gross_sales_trend,
                m.peak_season_months,
                f.financing_id, f.loan_amount, f.total_repayment_amount,
                f.expected_days, f.days_since_disbursement, f.amount_repaid,
                f.status as financing_status, f.disbursement_date,
                f.is_first_credit, f.total_prior_credits, f.first_credit_date,
                f.partner_revenue_share,
                f.gross_sales_pre_30d, f.gross_sales_pre_90d,
                f.gross_sales_pre_180d, f.gross_sales_pre_avg_monthly,
                COALESCE(post.gs_30d, 0)        as gross_sales_30d_post,
                COALESCE(post.gs_90d, 0)        as gross_sales_90d_post,
                COALESCE(post.active_days, 0)   as active_sales_days_post,
                COALESCE(post.has_direct, 0)    as has_direct_gross_sales,
                CASE
                    WHEN f.expected_days > 0 AND f.days_since_disbursement > 0
                    THEN ROUND(
                        (f.amount_repaid / f.days_since_disbursement) /
                        (f.total_repayment_amount / f.expected_days), 2)
                    ELSE 0
                END as repayment_pace_ratio
            FROM merchants m
            JOIN financings f ON f.merchant_id = m.merchant_id
            LEFT JOIN (
                SELECT
                    ds2.merchant_id,
                    SUM(CASE WHEN ds2.sale_date <= date(f2.disbursement_date,'+30 days')
                        THEN ds2.gross_sales ELSE 0 END) as gs_30d,
                    SUM(ds2.gross_sales)          as gs_90d,
                    COUNT(DISTINCT ds2.sale_date) as active_days,
                    MAX(ds2.has_direct_gross_sales) as has_direct
                FROM daily_sales ds2
                JOIN financings f2 ON f2.financing_id = ds2.financing_id
                WHERE ds2.sale_date >= f2.disbursement_date
                GROUP BY ds2.merchant_id
            ) post ON post.merchant_id = m.merchant_id
            WHERE m.partner_id = ?
            ORDER BY repayment_pace_ratio DESC
        """, (partner_id,)).fetchall())

        for m in merchants:
            try:
                m["peak_season_months"] = json.loads(m["peak_season_months"] or "[]")
            except:
                m["peak_season_months"] = []
            pre = m["gross_sales_pre_avg_monthly"] or 1
            post_monthly = m["gross_sales_90d_post"] / 3 if m["gross_sales_90d_post"] else 0
            m["gross_sales_uplift_pct"] = round((post_monthly - pre) / pre * 100, 1)

        return {"partner_id": partner_id, "total_merchants": len(merchants), "merchants": merchants}
    finally:
        conn.close()


@app.get("/partner/{partner_id}/weekly")
def get_weekly(partner_id: int):
    conn = get_conn()
    try:
        weekly = rows_to_list(conn.execute("""
            SELECT
                ds.merchant_id, m.merchant_name, m.segment, m.country,
                SUM(ds.gross_sales)          as weekly_gross_sales,
                COUNT(DISTINCT ds.sale_date) as days_with_sales,
                f.gross_sales_pre_avg_monthly,
                f.status as financing_status,
                CASE
                    WHEN f.expected_days > 0 AND f.days_since_disbursement > 0
                    THEN ROUND(
                        (f.amount_repaid / f.days_since_disbursement) /
                        (f.total_repayment_amount / f.expected_days), 2)
                    ELSE 0
                END as repayment_pace_ratio
            FROM daily_sales ds
            JOIN merchants m  ON m.merchant_id  = ds.merchant_id
            JOIN financings f ON f.financing_id = ds.financing_id
            WHERE ds.partner_id = ? AND ds.sale_date >= ?
              AND f.status IN ('ACTIVE','PAID')
            GROUP BY ds.merchant_id
            ORDER BY weekly_gross_sales DESC
        """, (partner_id, WEEK_START.isoformat())).fetchall())

        days_in_week = (TODAY - WEEK_START).days or 1
        for row in weekly:
            pre_weekly = (row["gross_sales_pre_avg_monthly"] or 0) / 4
            row["weekly_baseline"]   = round(pre_weekly, 2)
            row["weekly_uplift_pct"] = round(
                (row["weekly_gross_sales"] - pre_weekly) / pre_weekly * 100, 1
            ) if pre_weekly > 0 else 0
            row["sold_every_day"] = row["days_with_sales"] >= days_in_week

        return {
            "partner_id": partner_id,
            "week_start": WEEK_START.isoformat(),
            "week_end":   TODAY.isoformat(),
            "merchants":  weekly
        }
    finally:
        conn.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
