import streamlit as st
import json
import requests
from datetime import datetime
from agent import run_lucio
from anthropic import Anthropic

API_BASE   = "http://localhost:8000"
PARTNER_ID = 1001
client     = Anthropic()

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
.delta-callout { background:#EAF2ED; border:1px solid #C8DDD0; border-radius:10px; padding:14px 18px; margin-bottom:14px; }
.delta-callout-title { font-family:'DM Mono',monospace; font-size:9px; letter-spacing:0.12em; text-transform:uppercase; color:#3D8C5A; margin-bottom:8px; }
.delta-callout-body { font-size:12px; color:#2A5A3A; line-height:1.65; }
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
.badge { display:inline-block; font-family:'DM Mono',monospace; font-size:8px; padding:2px 8px; border-radius:20px; font-weight:500; letter-spacing:0.06em; }
.badge-top { background:#EAF2ED; color:#1C3D2A; }
.badge-neutral { background:#FBF3E8; color:#7A4F1E; }
.badge-arturo { background:#FAECEC; color:#8B2020; }
.chat-msg-user { background:#1C3D2A; color:#FFFFFF; border-radius:12px 12px 4px 12px; padding:10px 16px; font-size:13px; line-height:1.6; margin-bottom:10px; max-width:75%; margin-left:auto; }
.chat-msg-lucio { background:#FFFFFF; border:1px solid #E2DDD4; border-radius:12px 12px 12px 4px; padding:10px 16px; font-size:13px; line-height:1.65; color:#3A3530; margin-bottom:10px; max-width:85%; }
.chat-msg-lucio strong { color:#1C3D2A; }
.api-endpoint { background:#EAF2ED; border:1px solid #C8DDD0; border-radius:8px; padding:12px 16px; font-family:'DM Mono',monospace; font-size:12px; color:#1C3D2A; margin-bottom:14px; }
.code-box { background:#1A1814; border-radius:8px; padding:18px; font-family:'DM Mono',monospace; font-size:11px; color:rg
cat > /workspaces/lucio-r2/app.py << 'PYEOF'
import streamlit as st
import json
import requests
from datetime import datetime
from agent import run_lucio
from anthropic import Anthropic

API_BASE   = "http://localhost:8000"
PARTNER_ID = 1001
client     = Anthropic()

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
.delta-callout { background:#EAF2ED; border:1px solid #C8DDD0; border-radius:10px; padding:14px 18px; margin-bottom:14px; }
.delta-callout-title { font-family:'DM Mono',monospace; font-size:9px; letter-spacing:0.12em; text-transform:uppercase; color:#3D8C5A; margin-bottom:8px; }
.delta-callout-body { font-size:12px; color:#2A5A3A; line-height:1.65; }
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
.badge { display:inline-block; font-family:'DM Mono',monospace; font-size:8px; padding:2px 8px; border-radius:20px; font-weight:500; letter-spacing:0.06em; }
.badge-top { background:#EAF2ED; color:#1C3D2A; }
.badge-neutral { background:#FBF3E8; color:#7A4F1E; }
.badge-arturo { background:#FAECEC; color:#8B2020; }
.chat-msg-user { background:#1C3D2A; color:#FFFFFF; border-radius:12px 12px 4px 12px; padding:10px 16px; font-size:13px; line-height:1.6; margin-bottom:10px; max-width:75%; margin-left:auto; }
.chat-msg-lucio { background:#FFFFFF; border:1px solid #E2DDD4; border-radius:12px 12px 12px 4px; padding:10px 16px; font-size:13px; line-height:1.65; color:#3A3530; margin-bottom:10px; max-width:85%; }
.chat-msg-lucio strong { color:#1C3D2A; }
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


# ── Helpers ──────────────────────────────────────────────────────────────────
def classify(m):
    p = m.get("repayment_pace_ratio", 0)
    s = m.get("financing_status", "")
    u = m.get("gross_sales_uplift_pct", 0)
    if p < 0.8 or s == "PAUSED": return "arturo"
    if p >= 1.1 and s in ["ACTIVE","PAID"] and u >= 25: return "top"
    return "neutral"

def fetch(endpoint):
    try:
        r = requests.get(f"{API_BASE}{endpoint}", timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Backend error: {e}. Make sure the API is running: cd backend && python api.py &")
        st.stop()

def build_lucio_input(snapshot, merchant_data, weekly):
    return {
        "partner_id":   snapshot["partner_id"],
        "partner_name": snapshot["partner_name"],
        "rev_share_rate": snapshot["rev_share_rate"],
        "funnel": {
            "total_applications": snapshot["kpis"]["total_applications"],
            "total_approved":     snapshot["kpis"]["total_approved"],
            "total_denied":       snapshot["kpis"]["total_denied"],
            "approval_rate_pct":  snapshot["kpis"]["approval_rate_pct"],
            "top_denial_reasons": snapshot["top_denial_reasons"]
        },
        "merchants": merchant_data["merchants"],
        "weekly_signals": {
            "weekly_gross_sales_usd":      snapshot["kpis"]["weekly_gross_sales_usd"],
            "weekly_consistency_pct":      snapshot["kpis"]["weekly_consistency_pct"],
            "merchants_selling_this_week": snapshot["kpis"]["merchants_selling_this_week"],
            "week_start": weekly["week_start"],
            "week_end":   weekly["week_end"],
        }
    }

def build_api_payload(snapshot, merchant_data, result):
    merchants = merchant_data["merchants"]
    top    = [m for m in merchants if classify(m) == "top"]
    arturo = [m for m in merchants if classify(m) == "arturo"]
    neutral= [m for m in merchants if classify(m) == "neutral"]
    return {
        "partner_id":   snapshot["partner_id"],
        "partner_name": snapshot["partner_name"],
        "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "snapshot":     snapshot["kpis"],
        "portfolio_partition": {
            "arturo_territory": len(arturo),
            "lucio_territory":  len(top)+len(neutral),
            "top_performers":   len(top),
            "neutral":          len(neutral),
        },
        "top_performers": [
            {"merchant_id": m["merchant_id"],
             "merchant_name": m["merchant_name"],
             "segment": m["segment"],
             "country": m["country"],
             "gross_sales_uplift_pct": m.get("gross_sales_uplift_pct"),
             "repayment_pace_ratio":   m.get("repayment_pace_ratio"),
             "partner_revenue_share":  m.get("partner_revenue_share"),
             "financing_status":       m.get("financing_status")}
            for m in sorted(top, key=lambda x: x.get("gross_sales_uplift_pct",0), reverse=True)
        ],
        "icp_summary":  result["icp_text"][:600]+"...",
        "brief_text":   result["brief"],
    }


# ── Load from backend ────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_backend_data():
    snapshot      = fetch(f"/partner/{PARTNER_ID}/snapshot")
    merchant_data = fetch(f"/partner/{PARTNER_ID}/merchants")
    weekly        = fetch(f"/partner/{PARTNER_ID}/weekly")
    return snapshot, merchant_data, weekly

snapshot, merchant_data, weekly = load_backend_data()
merchants     = merchant_data["merchants"]
kpis          = snapshot["kpis"]
n             = len(merchants)
rev_rate      = snapshot["rev_share_rate"]
partner_name  = snapshot["partner_name"]

arturo_count  = sum(1 for m in merchants if classify(m)=="arturo")
top_count     = sum(1 for m in merchants if classify(m)=="top")
neutral_count = sum(1 for m in merchants if classify(m)=="neutral")
ap,np_,lp     = arturo_count/n, neutral_count/n, top_count/n

top_merchants = [m for m in merchants if classify(m)=="top"]
top_sorted    = sorted(top_merchants, key=lambda x: x.get("gross_sales_uplift_pct",0), reverse=True)

top_gs_pre   = sum(m.get("gross_sales_pre_avg_monthly",0) for m in top_merchants)
top_gs_post  = sum(m.get("gross_sales_90d_post",0)/3 for m in top_merchants)
top_gs_delta = top_gs_post - top_gs_pre
top_gs_pct   = round(top_gs_delta/top_gs_pre*100,1) if top_gs_pre > 0 else 0
extra_rev    = sum(
    (m.get("gross_sales_90d_post",0)/3 - m.get("gross_sales_pre_avg_monthly",0)) * rev_rate
    for m in top_merchants
    if m.get("gross_sales_90d_post",0)/3 > m.get("gross_sales_pre_avg_monthly",0)
)
bar_max  = max(top_gs_pre, top_gs_post) or 1
pre_pct  = round(top_gs_pre/bar_max*100)
post_pct = round(top_gs_post/bar_max*100)


# ── HEADER ───────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="lucio-header">
  <div>
    <h1>✦ <em>Lucio</em> — Partner Intelligence</h1>
    <p>R2 · {partner_name} · Partner {PARTNER_ID} · {n} merchants · live data</p>
  </div>
  <div class="header-right">Generated {datetime.now().strftime("%b %d, %Y")}<br>v0 prototype · Claude claude-sonnet-4-20250514</div>
</div>
""", unsafe_allow_html=True)

# ── KPIS ─────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="kpi-row">
  <div class="kpi-card accent">
    <div class="kpi-label">Revenue share earned</div>
    <div class="kpi-value">${kpis['total_revenue_share_usd']:,.0f}</div>
    <div class="kpi-note">from {n} financed merchants</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Approval rate</div>
    <div class="kpi-value">{kpis['approval_rate_pct']}%</div>
    <div class="kpi-note">{kpis['total_approved']} of {kpis['total_applications']}</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Weekly gross sales</div>
    <div class="kpi-value">${kpis['weekly_gross_sales_usd']:,.0f}</div>
    <div class="kpi-note">{kpis['merchants_selling_this_week']} merchants selling</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Top performers</div>
    <div class="kpi-value">{top_count}</div>
    <div class="kpi-note">thriving post-credit</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Gross sales uplift</div>
    <div class="kpi-value">+{top_gs_pct:.0f}%</div>
    <div class="kpi-note">top performers vs. pre-credit</div>
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
      <span style="font-family:'DM Mono',monospace;font-size:9px;color:#B8B4AC;">pace&lt;0.8 or PAUSED</span>
      <span style="font-family:'DM Mono',monospace;font-size:9px;color:#C5C0B8;">neutral</span>
      <span style="font-family:'DM Mono',monospace;font-size:9px;color:#3D8C5A;">pace≥1.1 + uplift≥25%</span>
    </div>
  </div>
  <div class="partition-stat">
    <div class="ps-num lucio">{top_count}</div>
    <div class="ps-desc">Lucio top performers</div>
  </div>
  <div class="partition-rule">Same data source · Zero overlap<br>Arturo protects · Lucio grows</div>
</div>
""", unsafe_allow_html=True)

# ── RUN BUTTON ────────────────────────────────────────────────────────────────
if st.button("✦  RUN LUCIO — GENERATE WEEKLY DIGEST", type="primary"):
    with st.spinner("Lucio is analyzing the portfolio (~45 seconds)..."):
        lucio_input = build_lucio_input(snapshot, merchant_data, weekly)
        result = run_lucio(lucio_input)
        result["api_payload"] = build_api_payload(snapshot, merchant_data, result)
        # Initialize chat history with digest as first message
        st.session_state["chat_history"] = [
            {"role": "assistant", "content": result["brief"]}
        ]
    st.session_state["result"] = result
    st.rerun()

if "result" not in st.session_state:
    st.markdown('<div style="text-align:center;padding:40px 0;color:#C5C0B8;font-family:\'DM Mono\',monospace;font-size:12px;letter-spacing:0.08em;">Press RUN LUCIO to generate the weekly digest</div>', unsafe_allow_html=True)
    st.stop()

result = st.session_state["result"]

tab_dash, tab_cot, tab_icp, tab_chat, tab_api = st.tabs([
    "📊  Dashboard",
    "🧠  Chain of thought",
    "🧬  ICP Profile",
    "💬  Ask Lucio",
    "🔌  API Output"
])


# ══════════════════════════════════════════════════════════════
# TAB 1 — DASHBOARD
# ══════════════════════════════════════════════════════════════
with tab_dash:
    col_left, col_right = st.columns([1.05, 0.95], gap="large")

    with col_left:
        st.markdown('<div class="section-label">Weekly digest</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="brief-box">{result["brief"]}</div>', unsafe_allow_html=True)

    with col_right:
        st.markdown('<div class="section-label">Top performers — gross sales before vs. after credit</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="gmv-chart-box">
          <div style="display:flex;gap:0;margin-bottom:22px;align-items:flex-end;">
            <div style="flex:1;">
              <div style="font-family:'DM Mono',monospace;font-size:11px;color:#9E9890;margin-bottom:4px;">BEFORE CREDIT</div>
              <div style="font-family:'DM Mono',monospace;font-size:26px;font-weight:500;color:#1A1814;">${top_gs_pre:,.0f}</div>
              <div style="font-size:10px;color:#9E9890;margin-top:3px;">avg monthly · {top_count} merchants</div>
            </div>
            <div style="padding:0 16px 8px;color:#C5C0B8;font-size:22px;">→</div>
            <div style="flex:1;">
              <div style="font-family:'DM Mono',monospace;font-size:11px;color:#3D8C5A;margin-bottom:4px;">AFTER CREDIT</div>
              <div style="font-family:'DM Mono',monospace;font-size:26px;font-weight:500;color:#1C3D2A;">${top_gs_post:,.0f}</div>
              <div style="font-size:10px;color:#9E9890;margin-top:3px;">avg monthly · 90-day window</div>
            </div>
            <div style="text-align:right;flex:0.8;">
              <div style="font-family:'DM Mono',monospace;font-size:11px;color:#9E9890;margin-bottom:4px;">DELTA</div>
              <div style="font-family:'DM Mono',monospace;font-size:26px;font-weight:500;color:#1C3D2A;">+{top_gs_pct:.0f}%</div>
              <div style="font-size:10px;color:#3D8C5A;margin-top:3px;">+${top_gs_delta:,.0f}/month</div>
            </div>
          </div>
          <div style="margin-bottom:8px;">
            <div style="font-family:'DM Mono',monospace;font-size:9px;color:#9E9890;letter-spacing:0.08em;margin-bottom:6px;">BEFORE CREDIT</div>
            <div style="background:#F4F1EA;border-radius:6px;height:36px;overflow:hidden;">
              <div style="background:#E2DDD4;height:100%;width:{pre_pct}%;border-radius:6px;display:flex;align-items:center;padding:0 12px;">
                <span style="font-family:'DM Mono',monospace;font-size:11px;font-weight:500;color:#6A6560;">${top_gs_pre:,.0f}/mo</span>
              </div>
            </div>
          </div>
          <div>
            <div style="font-family:'DM Mono',monospace;font-size:9px;color:#3D8C5A;letter-spacing:0.08em;margin-bottom:6px;">AFTER CREDIT</div>
            <div style="background:#F4F1EA;border-radius:6px;height:36px;overflow:hidden;">
              <div style="background:#1C3D2A;height:100%;width:{post_pct}%;border-radius:6px;display:flex;align-items:center;padding:0 12px;">
                <span style="font-family:'DM Mono',monospace;font-size:11px;font-weight:500;color:rgba(255,255,255,0.9);">${top_gs_post:,.0f}/mo</span>
              </div>
            </div>
          </div>
          <div style="margin-top:14px;display:flex;align-items:center;gap:10px;">
            <div style="flex:1;height:1px;background:#E2DDD4;"></div>
            <div style="font-family:'DM Mono',monospace;font-size:10px;color:#3D8C5A;background:#EAF2ED;border:1px solid #C8DDD0;border-radius:4px;padding:3px 10px;white-space:nowrap;">
              +${top_gs_delta:,.0f}/month incremental gross sales from credit
            </div>
            <div style="flex:1;height:1px;background:#E2DDD4;"></div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="delta-callout">
          <div class="delta-callout-title">What this means for {partner_name}</div>
          <div class="delta-callout-body">
            Your {top_count} top-performing merchants grew their combined monthly gross sales by
            <strong>+${top_gs_delta:,.0f}</strong> after receiving R2 credit.
            That growth generates an estimated <strong>+${extra_rev:,.0f}/month</strong>
            in additional revenue — on top of the <strong>${kpis['total_revenue_share_usd']:,.0f}</strong>
            already earned in base revenue share.
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="section-label">Top performers this week</div>', unsafe_allow_html=True)
        for m in top_sorted[:5]:
            prior = m.get("total_prior_credits", 0)
            st.markdown(f"""
            <div class="performer-card">
              <div class="pc-name">{m['merchant_name']}</div>
              <div class="pc-meta">{m['segment'].replace('_',' ')} · {m.get('city','')}, {m['country']} · {"repeat ×"+str(prior) if prior>0 else "first credit"}</div>
              <div class="pc-stats">
                <div><div class="pc-val green">+{m.get('gross_sales_uplift_pct',0)}%</div><div class="pc-lbl">gross sales uplift</div></div>
                <div><div class="pc-val amber">{m.get('repayment_pace_ratio',0)}x</div><div class="pc-lbl">pace ratio</div></div>
                <div><div class="pc-val muted">${m.get('partner_revenue_share',0):,.0f}</div><div class="pc-lbl">rev share</div></div>
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
        st.markdown('<div class="section-label">All merchants — classification table</div>', unsafe_allow_html=True)
        rows = []
        for m in merchants:
            c = classify(m)
            badge = {"top":'<span class="badge badge-top">Top Performer</span>',"neutral":'<span class="badge badge-neutral">Neutral</span>',"arturo":'<span class="badge badge-arturo">Arturo</span>'}[c]
            u = m.get("gross_sales_uplift_pct", 0)
            rows.append(f'<tr><td style="font-family:\'DM Mono\',monospace;font-size:9px;color:#9E9890;">{m["merchant_id"]}</td><td style="font-weight:500;">{m["merchant_name"]}</td><td style="font-family:\'DM Mono\',monospace;">{m.get("repayment_pace_ratio",0)}</td><td style="font-family:\'DM Mono\',monospace;">{"+" if u>0 else ""}{u}%</td><td>{badge}</td></tr>')
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
        st.markdown('<div class="section-label">Full ICP analysis — what winners looked like before credit</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="icp-box">{result["icp_text"]}</div>', unsafe_allow_html=True)
    with col_i2:
        st.markdown('<div class="section-label">Hard floor metrics — use as lead filter</div>', unsafe_allow_html=True)
        for label, value, note in [
            ("Platform tenure","≥ 13 months","Time on platform before credit"),
            ("Monthly gross sales","≥ $6,800","Proven revenue baseline"),
            ("Sales growth trend","≥ +4% monthly","Already growing before credit"),
            ("Refund rate","≤ 3.0%","Operational quality signal"),
            ("Customer rating","≥ 4.5 / 5.0","Customer satisfaction"),
            ("Monthly orders","≥ 240 / month","Sufficient transaction volume"),
            ("Active listings","≥ 18 items","Menu or product depth"),
            ("Segment","Restaurant / Dark kitchen","Retail underperforms significantly"),
        ]:
            st.markdown(f'<div class="floor-card"><div><div class="floor-label">{label}</div><div class="floor-note">{note}</div></div><div class="floor-value">{value}</div></div>', unsafe_allow_html=True)
        st.markdown('<div style="margin-top:14px;padding:14px 16px;background:#EAF2ED;border:1px solid #C8DDD0;border-radius:8px;font-size:11px;color:#2A4A34;line-height:1.65;"><strong>How to use this:</strong> Apply these filters when deciding which merchants to show the R2 credit offer to. Merchants matching 7+ criteria are your highest-probability conversions.</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# TAB 4 — ASK LUCIO
# ══════════════════════════════════════════════════════════════
with tab_chat:
    st.markdown("""
    <div style="font-size:12px;color:#9E9890;margin-bottom:16px;line-height:1.7;">
      Lucio received the weekly digest and is ready to continue the conversation.
      Ask anything based on this week's data — campaign ideas, merchant profiles,
      next steps for your credit program.
    </div>
    """, unsafe_allow_html=True)

    # Initialize chat history if needed
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = [
            {"role": "assistant", "content": result["brief"]}
        ]

    # Display chat history
    for msg in st.session_state["chat_history"]:
        if msg["role"] == "user":
            st.markdown(f'<div class="chat-msg-user">{msg["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="chat-msg-lucio">{msg["content"]}</div>', unsafe_allow_html=True)

    # Input
    user_input = st.chat_input("Ask Lucio anything about this week's digest...")

    if user_input:
        # Add user message to history
        st.session_state["chat_history"].append({"role": "user", "content": user_input})

        # Build messages for Claude — full conversation history
        # System prompt gives Lucio its persona and the full digest context
        system_prompt = f"""You are Lucio, R2's partner intelligence agent.
You just sent the weekly digest to {partner_name}'s credit program manager.
The digest is the first message in this conversation.

You have full context of:
- The partner's portfolio: {top_count} top performers, {arturo_count} in Arturo's territory
- Weekly gross sales: ${kpis['weekly_gross_sales_usd']:,.0f}
- Revenue share earned: ${kpis['total_revenue_share_usd']:,.0f}
- Approval rate: {kpis['approval_rate_pct']}%
- Top performers gross sales uplift: +{top_gs_pct:.0f}% vs pre-credit average

You can help with:
- Marketing campaign copy and strategy based on the ICP
- Explaining which merchant segments to prioritize
- Answering questions about the portfolio data
- Suggesting next steps for the credit program

Be concise, warm, and data-driven. You are talking to a marketing or
partnerships professional — not a data analyst. Always ground your
answers in the actual data from the digest."""

        messages = [{"role": m["role"], "content": m["content"]}
                    for m in st.session_state["chat_history"]]

        with st.spinner("Lucio is thinking..."):
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                system=system_prompt,
                messages=messages
            )
            lucio_reply = response.content[0].text

        st.session_state["chat_history"].append({"role": "assistant", "content": lucio_reply})
        st.rerun()


# ══════════════════════════════════════════════════════════════
# TAB 5 — API OUTPUT
# ══════════════════════════════════════════════════════════════
with tab_api:
    st.markdown('<div style="font-size:12px;color:#9E9890;margin-bottom:16px;line-height:1.7;">Lucio\'s output is structured JSON from the start. The dashboard reads from this same payload. Your engineering team can pipe this into your CRM, internal dashboard, or data warehouse.</div>', unsafe_allow_html=True)
    col_a1, col_a2 = st.columns([1,1], gap="large")

    with col_a1:
        st.markdown('<div class="section-label">Endpoint</div>', unsafe_allow_html=True)
        st.markdown('<div class="api-endpoint">POST /v1/partners/{partner_id}/intelligence/brief</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-label">Python</div>', unsafe_allow_html=True)
        st.markdown("""<div class="code-box">import requests

r = requests.post(
    "https://api.r2.co/v1/partners/1001/intelligence/brief",
    headers={"Authorization": "Bearer YOUR_R2_TOKEN"},
    json={"lookback_days": 90}
)
brief = r.json()

print(brief["snapshot"]["approval_rate_pct"])
print(brief["top_performers"][0]["gross_sales_uplift_pct"])
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
renderTopPerformers(brief.top_performers);</div>""", unsafe_allow_html=True)

    with col_a2:
        st.markdown('<div class="section-label">Structured JSON payload — this run</div>', unsafe_allow_html=True)
        payload_str = json.dumps(result["api_payload"], indent=2, ensure_ascii=False)
        st.markdown(f'<div class="json-box">{payload_str}</div>', unsafe_allow_html=True)
        st.download_button(
            label="⬇  Download JSON payload",
            data=payload_str,
            file_name=f"lucio_digest_{PARTNER_ID}_{datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json",
            use_container_width=True
        )
