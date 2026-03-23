import streamlit as st
import json
from datetime import datetime
import pandas as pd
from agent import load_data, run_lucio

st.set_page_config(
    page_title="Lucio — R2 Partner Intelligence",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@400;500;600;700&family=Playfair+Display:ital,wght@0,400;1,400&display=swap');

html, body, [class*="css"] { font-family:'Syne',sans-serif; background:#F4F1EA; color:#1A1814; }
.block-container { padding-top:20px !important; padding-bottom:40px !important; }
header { display:none !important; }

.lucio-header { background:#FFFFFF; border:1px solid #E2DDD4; border-radius:14px; padding:22px 32px; margin-bottom:16px; display:flex; align-items:center; justify-content:space-between; }
.lucio-header h1 { font-family:'Playfair Display',serif; font-size:22px; font-weight:400; color:#1A1814; margin:0 0 3px; }
.lucio-header h1 em { font-style:italic; color:#1C3D2A; }
.lucio-header p { font-family:'DM Mono',monospace; font-size:10px; color:#9E9890; letter-spacing:0.08em; margin:0; }
.header-right { font-family:'DM Mono',monospace; font-size:10px; color:#9E9890; text-align:right; line-height:1.8; }

.kpi-row { display:grid; grid-template-columns:repeat(5,1fr); gap:10px; margin-bottom:14px; }
.kpi-card { background:#FFFFFF; border:1px solid #E2DDD4; border-radius:12px; padding:14px 16px; }
.kpi-card.accent { background:#1C3D2A; border-color:#1C3D2A; }
.kpi-label { font-family:'DM Mono',monospace; font-size:9px; letter-spacing:0.12em; text-transform:uppercase; color:#9E9890; margin-bottom:5px; }
.kpi-card.accent .kpi-label { color:rgba(255,255,255,0.5); }
.kpi-value { font-family:'DM Mono',monospace; font-size:24px; font-weight:500; color:#1A1814; line-height:1; margin-bottom:3px; }
.kpi-card.accent .kpi-value { color:#FFFFFF; }
.kpi-note { font-size:11px; color:#9E9890; }
.kpi-card.accent .kpi-note { color:rgba(255,255,255,0.45); }

.partition-strip { background:#FFFFFF; border:1px solid #E2DDD4; border-radius:12px; padding:12px 22px; margin-bottom:14px; display:flex; align-items:center; gap:20px; }
.partition-strip-label { font-family:'DM Mono',monospace; font-size:9px; letter-spacing:0.1em; text-transform:uppercase; color:#C5C0B8; white-space:nowrap; }
.partition-track { flex:1; height:6px; border-radius:3px; overflow:hidden; display:flex; gap:2px; }
.pt-arturo { background:#D4897A; } .pt-neutral { background:#E2DDD4; } .pt-lucio { background:#3D8C5A; }
.partition-stat { text-align:center; min-width:55px; }
.ps-num { font-family:'DM Mono',monospace; font-size:18px; font-weight:500; line-height:1; }
.ps-num.arturo { color:#8B3020; } .ps-num.lucio { color:#1C3D2A; }
.ps-desc { font-size:10px; color:#9E9890; margin-top:2px; }
.partition-rule { font-family:'DM Mono',monospace; font-size:9px; color:#C5C0B8; text-align:right; line-height:1.8; }

.section-label { font-family:'DM Mono',monospace; font-size:9px; letter-spacing:0.15em; text-transform:uppercase; color:#9E9890; margin-bottom:10px; padding-bottom:8px; border-bottom:1px solid #E2DDD4; }

.brief-box { background:#FFFFFF; border:1px solid #E2DDD4; border-radius:12px; padding:22px 24px; font-size:13px; line-height:1.8; color:#3A3530; white-space:pre-wrap; }

.gmv-chart-box { background:#FFFFFF; border:1px solid #E2DDD4; border-radius:12px; padding:20px 22px; margin-bottom:14px; }

.gmv-summary-row { display:flex; gap:0; margin-bottom:20px; }
.gmv-stat { flex:1; }
.gmv-stat-num { font-family:'DM Mono',monospace; font-size:22px; font-weight:500; color:#1A1814; line-height:1; margin-bottom:3px; }
.gmv-stat-num.green { color:#1C3D2A; }
.gmv-stat-num.delta { color:#1C3D2A; font-size:26px; }
.gmv-stat-label { font-size:10px; color:#9E9890; font-family:'DM Mono',monospace; letter-spacing:0.05em; }
.gmv-divider { width:1px; background:#E2DDD4; margin:0 20px; }
.gmv-arrow { display:flex; align-items:center; padding:0 12px; color:#C5C0B8; font-size:18px; }

.bar-track { height:32px; border-radius:6px; overflow:hidden; margin-bottom:8px; display:flex; align-items:center; }
.bar-fill { height:100%; border-radius:6px; display:flex; align-items:center; padding:0 10px; transition:width 0.4s ease; }
.bar-label { font-family:'DM Mono',monospace; font-size:10px; font-weight:500; color:#FFFFFF; white-space:nowrap; }
.bar-row-label { font-family:'DM Mono',monospace; font-size:10px; color:#9E9890; margin-bottom:4px; letter-spacing:0.06em; }

.delta-callout { background:#EAF2ED; border:1px solid #C8DDD0; border-radius:10px; padding:14px 18px; margin-top:4px; }
.delta-callout-title { font-family:'DM Mono',monospace; font-size:9px; letter-spacing:0.12em; text-transform:uppercase; color:#3D8C5A; margin-bottom:8px; }
.delta-callout-body { font-size:12px; color:#2A5A3A; line-height:1.65; }
.delta-callout-body strong { color:#1C3D2A; }

.performer-card { background:#FFFFFF; border:1px solid #E2DDD4; border-left:3px solid #1C3D2A; border-radius:8px; padding:10px 14px; margin-bottom:7px; }
.pc-name { font-size:13px; font-weight:600; color:#1A1814; margin-bottom:2px; }
.pc-meta { font-size:11px; color:#9E9890; margin-bottom:6px; }
.pc-stats { display:flex; gap:14px; }
.pc-val { font-family:'DM Mono',monospace; font-size:12px; font-weight:500; }
.pc-val.green { color:#1C3D2A; } .pc-val.amber { color:#8B5A1A; } .pc-val.muted { color:#9E9890; }
.pc-lbl { font-size:9px; color:#B8B4AC; font-family:'DM Mono',monospace; letter-spacing:0.06em; }

.thinking-box { background:#1A1814; border-radius:10px; padding:18px; font-family:'DM Mono',monospace; font-size:11px; color:rgba(242,239,230,0.55); line-height:1.75; white-space:pre-wrap; max-height:480px; overflow-y:auto; }
.icp-box { background:#FFFFFF; border:1px solid #E2DDD4; border-radius:10px; padding:20px; font-size:12px; line-height:1.75; color:#3A3530; white-space:pre-wrap; max-height:520px; overflow-y:auto; }
.floor-card { background:#FFFFFF; border:1px solid #E2DDD4; border-left:3px solid #3D8C5A; border-radius:8px; padding:10px 14px; margin-bottom:7px; display:flex; justify-content:space-between; align-items:center; }
.floor-label { font-size:12px; font-weight:600; color:#1A1814; }
.floor-note { font-size:10px; color:#9E9890; margin-top:2px; }
.floor-value { font-family:'DM Mono',monospace; font-size:13px; font-weight:500; color:#1C3D2A; text-align:right; }
.class-table { width:100%; border-collapse:collapse; font-size:11px; background:#FFFFFF; border-radius:10px; overflow:hidden; }
.class-table th { text-align:left; padding:8px 12px; font-family:'DM Mono',monospace; font-size:9px; letter-spacing:0.08em; text-transform:uppercase; color:#9E9890; border-bottom:1px solid #E2DDD4; background:#F7F5F0; }
.class-table td { padding:8px 12px; border-bottom:1px solid #F0EDE6; color:#4A4840; vertical-align:middle; }
.class-table tr:hover td { background:#FAFAF8; }
.badge { display:inline-block; font-family:'DM Mono',monospace; font-size:8px; padding:2px 8px; border-radius:20px; font-weight:500; letter-spacing:0.06em; }
.badge-top { background:#EAF2ED; color:#1C3D2A; } .badge-neutral { background:#FBF3E8; color:#7A4F1E; } .badge-arturo { background:#FAECEC; color:#8B2020; }
.api-endpoint { background:#EAF2ED; border:1px solid #C8DDD0; border-radius:8px; padding:12px 16px; font-family:'DM Mono',monospace; font-size:12px; color:#1C3D2A; margin-bottom:14px; }
.code-box { background:#1A1814; border-radius:8px; padding:18px; font-family:'DM Mono',monospace; font-size:11px; color:rgba(242,239,230,0.6); line-height:1.7; white-space:pre; overflow-x:auto; margin-bottom:14px; }
.json-box { background:#1A1814; border-radius:8px; padding:18px; font-family:'DM Mono',monospace; font-size:10px; color:rgba(242,239,230,0.5); line-height:1.65; white-space:pre; overflow-x:auto; max-height:500px; overflow-y:auto; }

.stButton > button { background:#1C3D2A !important; border:1px solid #1C3D2A !important; color:#FFFFFF !important; font-family:'DM Mono',monospace !important; font-size:12px !important; letter-spacing:0.1em !important; padding:12px 24px !important; border-radius:8px !important; }
.stButton > button:hover { background:#2A5C3F !important; }
.stTabs [data-baseweb="tab-list"] { background:#FFFFFF !important; border:1px solid #E2DDD4 !important; border-radius:10px !important; padding:4px !important; gap:4px !important; }
.stTabs [data-baseweb="tab"] { background:transparent !important; color:#9E9890 !important; font-family:'DM Mono',monospace !important; font-size:11px !important; letter-spacing:0.06em !important; border-radius:7px !important; padding:8px 16px !important; }
.stTabs [aria-selected="true"] { background:#1C3D2A !important; color:#FFFFFF !important; border:none !important; }
.stTabs [data-baseweb="tab-panel"] { padding-top:20px !important; }
hr { border-color:#E2DDD4 !important; }
</style>
""", unsafe_allow_html=True)


# ── Helpers ─────────────────────────────────────────────────────────────────
def classify(m):
    p,c,s,u = m["repayment_pace_ratio"],m["repayment_consistency"],m["financing_status"],m["gmv_uplift_pct_vs_avg"]
    if p < 0.8 or c == "low" or s == "PAUSED": return "arturo"
    if p >= 1.1 and c == "high" and s in ["ACTIVE","PAID"] and u >= 25: return "top"
    return "neutral"

def build_api_payload(data, result):
    ms = data["merchants"]
    top=[m for m in ms if classify(m)=="top"]
    arturo=[m for m in ms if classify(m)=="arturo"]
    neutral=[m for m in ms if classify(m)=="neutral"]
    return {
        "partner_id":data["partner_id"],"partner_name":data["partner_name"],
        "generated_at":datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "lookback_days":data["lookback_days"],
        "snapshot":{
            "approval_rate_pct":data["funnel"]["approval_rate_pct"],
            "total_applications":data["funnel"]["total_applications"],
            "total_approved":data["funnel"]["total_approved"],
            "total_denied":data["funnel"]["total_denied"],
            "total_revenue_share_usd":round(result["total_rev_share"],2),
            "active_merchants":result["active_count"],
            "total_merchants_analyzed":len(ms)
        },
        "portfolio_partition":{
            "arturo_territory":len(arturo),"lucio_territory":len(top)+len(neutral),
            "top_performers":len(top),"neutral":len(neutral),
            "filter_note":"arturo: pace<0.8 OR consistency=low OR PAUSED | top: pace>=1.1 AND consistency=high AND uplift>=25%"
        },
        "top_performers":[
            {"merchant_id":m["merchant_id"],"merchant_name":m["merchant_name"],
             "segment":m["segment"],"country":m["country"],"city":m["city"],
             "gmv_uplift_pct_vs_avg":m["gmv_uplift_pct_vs_avg"],
             "repayment_pace_ratio":m["repayment_pace_ratio"],
             "partner_revenue_share_usd":m["partner_revenue_share"],
             "months_on_platform":m["months_on_platform"],
             "total_prior_credits":m["total_prior_credits"],
             "financing_status":m["financing_status"]}
            for m in sorted(top,key=lambda x:x["gmv_uplift_pct_vs_avg"],reverse=True)
        ],
        "icp_summary":result["icp_text"][:800]+"...",
        "brief_text":result["brief"],
        "denial_reasons":data["funnel"]["top_denial_reasons"]
    }


# ── Load data ────────────────────────────────────────────────────────────────
@st.cache_data
def get_data(): return load_data()

data      = get_data()
merchants = data["merchants"]
funnel    = data["funnel"]
n         = len(merchants)
rev_share_rate = data["rev_share_rate"]

total_rev    = sum(m["partner_revenue_share"] for m in merchants)
active_count = sum(1 for m in merchants if m["financing_status"]=="ACTIVE")
arturo_count = sum(1 for m in merchants if classify(m)=="arturo")
top_count    = sum(1 for m in merchants if classify(m)=="top")
neutral_count= sum(1 for m in merchants if classify(m)=="neutral")
ap,np_,lp   = arturo_count/n, neutral_count/n, top_count/n

# GMV stats — top performers only
top_merchants = [m for m in merchants if classify(m)=="top"]
top_gmv_pre   = sum(m["gmv_pre_avg_monthly"] for m in top_merchants)
top_gmv_post  = sum(m["gmv_90d_post"]/3 for m in top_merchants)
top_gmv_delta = top_gmv_post - top_gmv_pre
top_gmv_pct   = (top_gmv_delta/top_gmv_pre*100) if top_gmv_pre > 0 else 0

# Additional rev share from GMV uplift of top performers
# (illustrative: incremental GMV × rev_share_rate as proxy for future loan volume benefit)
extra_rev = sum(
    (m["gmv_90d_post"]/3 - m["gmv_pre_avg_monthly"]) * rev_share_rate
    for m in top_merchants
    if m["gmv_90d_post"]/3 > m["gmv_pre_avg_monthly"]
)

# For bar widths (percentage of max for scaling)
bar_max = max(top_gmv_pre, top_gmv_post)
pre_pct  = round(top_gmv_pre  / bar_max * 100)
post_pct = round(top_gmv_post / bar_max * 100)


# ── HEADER ───────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="lucio-header">
  <div>
    <h1>✦ <em>Lucio</em> — Partner Intelligence</h1>
    <p>R2 · {data['partner_name']} · Partner {data['partner_id']} · {n} merchants · {data['lookback_days']}-day lookback</p>
  </div>
  <div class="header-right">Generated {datetime.now().strftime("%b %d, %Y")}<br>v0 prototype · Claude claude-sonnet-4-20250514</div>
</div>
""", unsafe_allow_html=True)


# ── KPI ROW ──────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="kpi-row">
  <div class="kpi-card accent">
    <div class="kpi-label">Revenue share earned</div>
    <div class="kpi-value">${total_rev:,.0f}</div>
    <div class="kpi-note">from {n} financed merchants</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Approval rate</div>
    <div class="kpi-value">{funnel['approval_rate_pct']}%</div>
    <div class="kpi-note">{funnel['total_approved']} of {funnel['total_applications']}</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Active relationships</div>
    <div class="kpi-value">{active_count}</div>
    <div class="kpi-note">financing active today</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Top performers</div>
    <div class="kpi-value">{top_count}</div>
    <div class="kpi-note">thriving post-credit</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">GMV uplift — top performers</div>
    <div class="kpi-value">+{top_gmv_pct:.0f}%</div>
    <div class="kpi-note">+${top_gmv_delta:,.0f}/mo incremental</div>
  </div>
</div>
""", unsafe_allow_html=True)


# ── PARTITION STRIP ───────────────────────────────────────────────────────────
st.markdown(f"""
<div class="partition-strip">
  <div class="partition-strip-label">Portfolio<br>partition</div>
  <div class="partition-stat">
    <div class="ps-num arturo">{arturo_count}</div>
    <div class="ps-desc">Arturo territory</div>
  </div>
  <div style="flex:2">
    <div class="partition-track">
      <div class="pt-arturo" style="flex:{ap}"></div>
      <div class="pt-neutral" style="flex:{np_}"></div>
      <div class="pt-lucio"   style="flex:{lp}"></div>
    </div>
    <div style="display:flex;justify-content:space-between;margin-top:5px;">
      <span style="font-family:'DM Mono',monospace;font-size:9px;color:#B8B4AC;">pace&lt;0.8 or consistency=low</span>
      <span style="font-family:'DM Mono',monospace;font-size:9px;color:#C5C0B8;">neutral</span>
      <span style="font-family:'DM Mono',monospace;font-size:9px;color:#3D8C5A;">pace≥1.1 + high consistency</span>
    </div>
  </div>
  <div class="partition-stat">
    <div class="ps-num lucio">{top_count}</div>
    <div class="ps-desc">Lucio top performers</div>
  </div>
  <div class="partition-rule">Same data source · Zero overlap<br>Mutually exclusive filters<br>Arturo protects · Lucio grows</div>
</div>
""", unsafe_allow_html=True)


# ── RUN BUTTON ────────────────────────────────────────────────────────────────
if st.button("✦  RUN LUCIO — GENERATE PARTNER BRIEF", type="primary"):
    with st.spinner("Analyzing portfolio — calling Claude 3 times (~45 seconds)..."):
        result = run_lucio(data)
        result["api_payload"] = build_api_payload(data, result)
    st.session_state["result"] = result
    st.rerun()

if "result" not in st.session_state:
    st.markdown('<div style="text-align:center;padding:40px 0;color:#C5C0B8;font-family:\'DM Mono\',monospace;font-size:12px;letter-spacing:0.08em;">Press RUN LUCIO to generate the partner intelligence brief</div>', unsafe_allow_html=True)
    st.stop()

result    = st.session_state["result"]
top_sorted= sorted(top_merchants, key=lambda x: x["gmv_uplift_pct_vs_avg"], reverse=True)

tab_dash, tab_cot, tab_icp, tab_api = st.tabs([
    "📊  Dashboard", "🧠  Chain of thought", "🧬  ICP Profile", "🔌  API Output"
])


# ══════════════════════════════════════════════════════════════
# TAB 1 — DASHBOARD
# ══════════════════════════════════════════════════════════════
with tab_dash:
    col_left, col_right = st.columns([1.05, 0.95], gap="large")

    # ── LEFT: Brief ───────────────────────────────────────────
    with col_left:
        st.markdown('<div class="section-label">Weekly partner brief</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="brief-box">{result["brief"]}</div>', unsafe_allow_html=True)

    # ── RIGHT: GMV chart + delta callout + performers ──────────
    with col_right:

        # ── GMV summary chart ────────────────────────────────
        st.markdown('<div class="section-label">Top performers — GMV before vs. after credit</div>', unsafe_allow_html=True)

        st.markdown(f"""
        <div class="gmv-chart-box">

          <!-- Summary numbers -->
          <div style="display:flex;gap:0;margin-bottom:22px;align-items:flex-end;">
            <div style="flex:1;">
              <div style="font-family:'DM Mono',monospace;font-size:11px;color:#9E9890;margin-bottom:4px;letter-spacing:0.06em;">BEFORE CREDIT</div>
              <div style="font-family:'DM Mono',monospace;font-size:26px;font-weight:500;color:#1A1814;line-height:1;">${top_gmv_pre:,.0f}</div>
              <div style="font-size:10px;color:#9E9890;margin-top:3px;">avg monthly GMV · {top_count} merchants</div>
            </div>
            <div style="padding:0 16px 8px;color:#C5C0B8;font-size:22px;">→</div>
            <div style="flex:1;">
              <div style="font-family:'DM Mono',monospace;font-size:11px;color:#3D8C5A;margin-bottom:4px;letter-spacing:0.06em;">AFTER CREDIT</div>
              <div style="font-family:'DM Mono',monospace;font-size:26px;font-weight:500;color:#1C3D2A;line-height:1;">${top_gmv_post:,.0f}</div>
              <div style="font-size:10px;color:#9E9890;margin-top:3px;">avg monthly GMV · 90-day window</div>
            </div>
            <div style="text-align:right;flex:0.8;">
              <div style="font-family:'DM Mono',monospace;font-size:11px;color:#9E9890;margin-bottom:4px;letter-spacing:0.06em;">DELTA</div>
              <div style="font-family:'DM Mono',monospace;font-size:26px;font-weight:500;color:#1C3D2A;line-height:1;">+{top_gmv_pct:.0f}%</div>
              <div style="font-size:10px;color:#3D8C5A;margin-top:3px;">+${top_gmv_delta:,.0f}/month</div>
            </div>
          </div>

          <!-- Bar chart -->
          <div style="margin-bottom:6px;">
            <div style="font-family:'DM Mono',monospace;font-size:9px;color:#9E9890;letter-spacing:0.08em;margin-bottom:6px;">BEFORE CREDIT</div>
            <div style="background:#F4F1EA;border-radius:6px;height:36px;overflow:hidden;position:relative;">
              <div style="background:#E2DDD4;height:100%;width:{pre_pct}%;border-radius:6px;display:flex;align-items:center;padding:0 12px;">
                <span style="font-family:'DM Mono',monospace;font-size:11px;font-weight:500;color:#6A6560;">${top_gmv_pre:,.0f}/mo</span>
              </div>
            </div>
          </div>
          <div>
            <div style="font-family:'DM Mono',monospace;font-size:9px;color:#3D8C5A;letter-spacing:0.08em;margin-bottom:6px;">AFTER CREDIT</div>
            <div style="background:#F4F1EA;border-radius:6px;height:36px;overflow:hidden;position:relative;">
              <div style="background:#1C3D2A;height:100%;width:{post_pct}%;border-radius:6px;display:flex;align-items:center;padding:0 12px;">
                <span style="font-family:'DM Mono',monospace;font-size:11px;font-weight:500;color:rgba(255,255,255,0.9);">${top_gmv_post:,.0f}/mo</span>
              </div>
            </div>
          </div>

          <!-- Delta annotation -->
          <div style="margin-top:14px;display:flex;align-items:center;gap:10px;">
            <div style="flex:1;height:1px;background:#E2DDD4;"></div>
            <div style="font-family:'DM Mono',monospace;font-size:10px;color:#3D8C5A;
                        background:#EAF2ED;border:1px solid #C8DDD0;border-radius:4px;
                        padding:3px 10px;white-space:nowrap;">
              +${top_gmv_delta:,.0f}/month incremental GMV from credit
            </div>
            <div style="flex:1;height:1px;background:#E2DDD4;"></div>
          </div>

        </div>
        """, unsafe_allow_html=True)

        # ── Revenue delta callout ────────────────────────────
        st.markdown(f"""
        <div class="delta-callout">
          <div class="delta-callout-title">What this means for {data['partner_name']}</div>
          <div class="delta-callout-body">
            Your {top_count} top-performing merchants grew their combined monthly GMV by
            <strong>+${top_gmv_delta:,.0f}</strong> after receiving R2 credit.
            That growth generates an estimated <strong>+${extra_rev:.0f}/month</strong>
            in additional revenue for {data['partner_name']} — on top of the
            <strong>${total_rev:,.0f}</strong> already earned in base revenue share.
            The more merchants that match this success profile, the larger this number grows.
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

        # ── Top performers ───────────────────────────────────
        st.markdown('<div class="section-label">Top performers this week</div>', unsafe_allow_html=True)
        for m in top_sorted[:5]:
            st.markdown(f"""
            <div class="performer-card">
              <div class="pc-name">{m['merchant_name']}</div>
              <div class="pc-meta">
                {m['segment'].replace('_',' ')} · {m['city']}, {m['country']}
                · {m['months_on_platform']}mo
                · {"repeat ×"+str(m['total_prior_credits']) if m['total_prior_credits']>0 else "first credit"}
              </div>
              <div class="pc-stats">
                <div><div class="pc-val green">+{m['gmv_uplift_pct_vs_avg']}%</div><div class="pc-lbl">GMV uplift</div></div>
                <div><div class="pc-val amber">{m['repayment_pace_ratio']}x</div><div class="pc-lbl">pace ratio</div></div>
                <div><div class="pc-val muted">${m['partner_revenue_share']:,.0f}</div><div class="pc-lbl">rev share</div></div>
              </div>
            </div>
            """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# TAB 2 — CHAIN OF THOUGHT
# ══════════════════════════════════════════════════════════════
with tab_cot:
    st.markdown('<div style="font-size:12px;color:#9E9890;margin-bottom:16px;line-height:1.7;">Lucio\'s internal reasoning — every classification decision shown explicitly. In production this is logged to the observability layer, not shown to the partner.</div>', unsafe_allow_html=True)
    col_t1, col_t2 = st.columns(2, gap="large")

    with col_t1:
        st.markdown('<div class="section-label">Step 1 — classification reasoning</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="thinking-box">{result["classification_thinking"]}</div>', unsafe_allow_html=True)
        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
        st.markdown('<div class="section-label">All 25 merchants — classification table</div>', unsafe_allow_html=True)
        rows = []
        for m in merchants:
            c = classify(m)
            badge = {"top":'<span class="badge badge-top">Top Performer</span>',"neutral":'<span class="badge badge-neutral">Neutral</span>',"arturo":'<span class="badge badge-arturo">Arturo</span>'}[c]
            u = m["gmv_uplift_pct_vs_avg"]
            rows.append(f'<tr><td style="font-family:\'DM Mono\',monospace;font-size:9px;color:#9E9890;">{m["merchant_id"]}</td><td style="font-weight:500;">{m["merchant_name"]}</td><td style="font-family:\'DM Mono\',monospace;">{m["repayment_pace_ratio"]}</td><td style="font-family:\'DM Mono\',monospace;">{"+" if u>0 else ""}{u}%</td><td>{badge}</td></tr>')
        st.markdown(f'<table class="class-table"><thead><tr><th>ID</th><th>Merchant</th><th>Pace</th><th>Uplift</th><th>Label</th></tr></thead><tbody>{"".join(rows)}</tbody></table>', unsafe_allow_html=True)

    with col_t2:
        st.markdown('<div class="section-label">Step 2 — ICP building reasoning</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="thinking-box">{result["icp_thinking"]}</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# TAB 3 — ICP PROFILE
# ══════════════════════════════════════════════════════════════
with tab_icp:
    col_i1, col_i2 = st.columns([1,1], gap="large")
    with col_i1:
        st.markdown('<div class="section-label">Full ICP analysis — top performers vs. rest</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="icp-box">{result["icp_text"]}</div>', unsafe_allow_html=True)
    with col_i2:
        st.markdown('<div class="section-label">Hard floor metrics — use as lead filter</div>', unsafe_allow_html=True)
        for label, value, note in [
            ("Platform tenure","≥ 13 months","Established merchants only"),
            ("Monthly GMV baseline","≥ $6,800","Proven revenue before credit"),
            ("GMV growth trend","≥ +4% coefficient","Already growing before credit"),
            ("Sales consistency","≥ 80 / 100","Regular daily sales pattern"),
            ("Refund rate","≤ 3.0%","Operational quality signal"),
            ("Customer rating","≥ 4.5 / 5.0","Customer satisfaction"),
            ("Monthly transactions","≥ 240 / month","Sufficient volume"),
            ("Active listings","≥ 18 items","Menu or product depth"),
            ("Segment","Restaurant / Dark kitchen","Retail underperforms significantly"),
        ]:
            st.markdown(f'<div class="floor-card"><div><div class="floor-label">{label}</div><div class="floor-note">{note}</div></div><div class="floor-value">{value}</div></div>', unsafe_allow_html=True)
        st.markdown('<div style="margin-top:14px;padding:14px 16px;background:#EAF2ED;border:1px solid #C8DDD0;border-radius:8px;font-size:11px;color:#2A4A34;line-height:1.65;"><strong>How to use this:</strong> Apply these filters when deciding which merchants to show the R2 credit offer to. Merchants matching 7+ criteria are your highest-probability conversions.</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# TAB 4 — API OUTPUT
# ══════════════════════════════════════════════════════════════
with tab_api:
    st.markdown('<div style="font-size:12px;color:#9E9890;margin-bottom:16px;line-height:1.7;">Lucio\'s output is structured JSON from the start — the dashboard reads from this same payload. Your engineering team can pipe this into your CRM, internal dashboard, or data warehouse.</div>', unsafe_allow_html=True)
    col_a1, col_a2 = st.columns([1,1], gap="large")

    with col_a1:
        st.markdown('<div class="section-label">Endpoint</div>', unsafe_allow_html=True)
        st.markdown('<div class="api-endpoint">POST /v1/partners/{partner_id}/intelligence/brief</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-label">Python</div>', unsafe_allow_html=True)
        st.markdown("""<div class="code-box">import requests

response = requests.post(
    "https://api.r2.co/v1/partners/1001/intelligence/brief",
    headers={"Authorization": "Bearer YOUR_R2_TOKEN"},
    json={"lookback_days": 90}
)
brief = response.json()

print(brief["snapshot"]["approval_rate_pct"])
print(brief["top_performers"][0]["gmv_uplift_pct_vs_avg"])
print(brief["icp_summary"])
print(brief["brief_text"])</div>""", unsafe_allow_html=True)
        st.markdown('<div class="section-label">JavaScript</div>', unsafe_allow_html=True)
        st.markdown("""<div class="code-box">const brief = await fetch(
  'https://api.r2.co/v1/partners/1001/intelligence/brief',
  { method: 'POST',
    headers: { 'Authorization': 'Bearer YOUR_R2_TOKEN',
               'Content-Type': 'application/json' },
    body: JSON.stringify({ lookback_days: 90 })
  }).then(r => r.json());

renderKPIs(brief.snapshot);
renderTopPerformers(brief.top_performers);
renderICPFilter(brief.icp_summary);</div>""", unsafe_allow_html=True)

    with col_a2:
        st.markdown('<div class="section-label">Structured JSON payload — this run</div>', unsafe_allow_html=True)
        payload_str = json.dumps(result["api_payload"], indent=2, ensure_ascii=False)
        st.markdown(f'<div class="json-box">{payload_str}</div>', unsafe_allow_html=True)
        st.download_button(
            label="⬇  Download JSON payload",
            data=payload_str,
            file_name=f"lucio_brief_{data['partner_id']}_{datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json",
            use_container_width=True
        )
