import streamlit as st
import json
import requests
import re
import os
from datetime import datetime
from agent import run_lucio
from anthropic import Anthropic

API_BASE   = "https://lucio-r2-production.up.railway.app"
PARTNER_ID = 1001

def get_client():
    try:
        import streamlit as _st
        key = _st.secrets.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    except Exception:
        key = os.getenv("ANTHROPIC_API_KEY")
    return Anthropic(api_key=key)

st.set_page_config(
    page_title="Lucio — R2 Partner Intelligence",
    page_icon="L",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@400;500;600;700&family=Playfair+Display:ital,wght@0,400;1,400&display=swap');
html,body,[class*="css"]{font-family:Syne,sans-serif;background:#F4F1EA;color:#1A1814;}
.block-container{padding-top:20px;padding-bottom:40px;}
header{display:none;}

.lh{background:#FFF;border:1px solid #E2DDD4;border-radius:14px;padding:22px 32px;margin-bottom:24px;display:flex;align-items:center;justify-content:space-between;}
.lh h1{font-family:'Playfair Display',serif;font-size:22px;font-weight:400;color:#1A1814;margin:0 0 3px;}
.lh h1 em{font-style:italic;color:#1C3D2A;}
.lh p{font-family:'DM Mono',monospace;font-size:10px;color:#9E9890;margin:0;}
.hr{font-family:'DM Mono',monospace;font-size:10px;color:#9E9890;text-align:right;line-height:1.8;}

.input-card{background:#FFF;border:1px solid #E2DDD4;border-radius:14px;padding:28px 32px;margin-bottom:24px;}
.input-label{font-family:'DM Mono',monospace;font-size:9px;letter-spacing:0.15em;text-transform:uppercase;color:#9E9890;margin-bottom:8px;}
.input-note{font-size:11px;color:#C5C0B8;margin-top:8px;}

.sl{font-family:'DM Mono',monospace;font-size:9px;letter-spacing:0.15em;text-transform:uppercase;color:#9E9890;margin-bottom:10px;padding-bottom:8px;border-bottom:1px solid #E2DDD4;}
.bb{background:#FFF;border:1px solid #E2DDD4;border-radius:12px;padding:22px 24px;font-size:13px;line-height:1.8;color:#3A3530;white-space:pre-wrap;}
.gc{background:#FFF;border:1px solid #E2DDD4;border-radius:12px;padding:20px 22px;margin-bottom:14px;}
.dc{background:#EAF2ED;border:1px solid #C8DDD0;border-radius:10px;padding:14px 18px;margin-bottom:14px;}
.dt{font-family:'DM Mono',monospace;font-size:9px;text-transform:uppercase;color:#3D8C5A;margin-bottom:8px;}
.db{font-size:12px;color:#2A5A3A;line-height:1.65;}
.pc{background:#FFF;border:1px solid #E2DDD4;border-left:3px solid #1C3D2A;border-radius:8px;padding:10px 14px;margin-bottom:7px;}
.pn2{font-size:13px;font-weight:600;color:#1A1814;margin-bottom:2px;}
.pm{font-size:11px;color:#9E9890;margin-bottom:6px;}
.pst2{display:flex;gap:14px;}
.pv{font-family:'DM Mono',monospace;font-size:12px;font-weight:500;}
.pv.g{color:#1C3D2A;}.pv.am{color:#8B5A1A;}.pv.mu{color:#9E9890;}
.pl{font-size:9px;color:#B8B4AC;font-family:'DM Mono',monospace;}
.tb{background:#1A1814;border-radius:10px;padding:18px;font-family:'DM Mono',monospace;font-size:11px;color:rgba(242,239,230,.55);line-height:1.75;white-space:pre-wrap;max-height:480px;overflow-y:auto;}
.ib{background:#FFF;border:1px solid #E2DDD4;border-radius:10px;padding:20px;font-size:12px;line-height:1.75;color:#3A3530;white-space:pre-wrap;max-height:520px;overflow-y:auto;}
.fc{background:#FFF;border:1px solid #E2DDD4;border-left:3px solid #3D8C5A;border-radius:8px;padding:10px 14px;margin-bottom:7px;display:flex;justify-content:space-between;align-items:center;}
.fl{font-size:12px;font-weight:600;color:#1A1814;}
.fn{font-size:10px;color:#9E9890;margin-top:2px;}
.fv{font-family:'DM Mono',monospace;font-size:13px;font-weight:500;color:#1C3D2A;text-align:right;}
.ct{width:100%;border-collapse:collapse;font-size:11px;background:#FFF;}
.ct th{text-align:left;padding:8px 12px;font-family:'DM Mono',monospace;font-size:9px;text-transform:uppercase;color:#9E9890;border-bottom:1px solid #E2DDD4;background:#F7F5F0;}
.ct td{padding:8px 12px;border-bottom:1px solid #F0EDE6;color:#4A4840;}
.bg{display:inline-block;font-family:'DM Mono',monospace;font-size:8px;padding:2px 8px;border-radius:20px;font-weight:500;}
.bg.tp{background:#EAF2ED;color:#1C3D2A;}
.bg.nt{background:#FBF3E8;color:#7A4F1E;}
.bg.at{background:#FAECEC;color:#8B2020;}
.cu{background:#1C3D2A;color:#FFF;border-radius:12px 12px 4px 12px;padding:10px 16px;font-size:13px;line-height:1.6;margin-bottom:10px;max-width:75%;margin-left:auto;}
.cl{background:#FFF;border:1px solid #E2DDD4;border-radius:12px 12px 12px 4px;padding:10px 16px;font-size:13px;line-height:1.65;color:#3A3530;margin-bottom:10px;max-width:85%;white-space:pre-wrap;}
.ae{background:#EAF2ED;border:1px solid #C8DDD0;border-radius:8px;padding:12px 16px;font-family:'DM Mono',monospace;font-size:12px;color:#1C3D2A;margin-bottom:14px;}
.jb{background:#1A1814;border-radius:8px;padding:18px;font-family:'DM Mono',monospace;font-size:10px;color:rgba(242,239,230,.5);line-height:1.65;white-space:pre;overflow-x:auto;max-height:500px;overflow-y:auto;}
.stButton>button{background:#1C3D2A;border:1px solid #1C3D2A;color:#FFF;font-family:'DM Mono',monospace;font-size:12px;letter-spacing:.1em;padding:12px 24px;border-radius:8px;width:100%;}
.stTabs [data-baseweb="tab-list"]{background:#FFF;border:1px solid #E2DDD4;border-radius:10px;padding:4px;gap:4px;}
.stTabs [data-baseweb="tab"]{background:transparent;color:#9E9890;font-family:'DM Mono',monospace;font-size:11px;border-radius:7px;padding:8px 16px;}
.stTabs [aria-selected="true"]{background:#1C3D2A;color:#FFF;border:none;}
</style>
""", unsafe_allow_html=True)


def classify(m):
    p=m.get("repayment_pace_ratio",0); s=m.get("financing_status",""); u=m.get("gross_sales_uplift_pct",0)
    if p<0.8 or s=="PAUSED": return "arturo"
    if p>=1.1 and s in ["ACTIVE","PAID"] and u>=25: return "top"
    return "neutral"

def fetch(endpoint):
    try:
        r=requests.get(f"{API_BASE}{endpoint}",timeout=15)
        r.raise_for_status(); return r.json()
    except Exception as e:
        st.error(f"Backend error: {e}"); st.stop()

def build_input(snapshot,md,weekly):
    return {"partner_id":snapshot["partner_id"],"partner_name":snapshot["partner_name"],
        "rev_share_rate":snapshot["rev_share_rate"],
        "funnel":{"total_applications":snapshot["kpis"]["total_applications"],
            "total_approved":snapshot["kpis"]["total_approved"],
            "total_denied":snapshot["kpis"]["total_denied"],
            "approval_rate_pct":snapshot["kpis"]["approval_rate_pct"],
            "top_denial_reasons":snapshot["top_denial_reasons"]},
        "merchants":md["merchants"],
        "weekly_signals":{"weekly_gross_sales_usd":snapshot["kpis"]["weekly_gross_sales_usd"],
            "weekly_consistency_pct":snapshot["kpis"]["weekly_consistency_pct"],
            "merchants_selling_this_week":snapshot["kpis"]["merchants_selling_this_week"],
            "week_start":weekly["week_start"],"week_end":weekly["week_end"]}}

def build_payload(snapshot,md,result):
    ms=md["merchants"]; top=[m for m in ms if classify(m)=="top"]
    arturo=[m for m in ms if classify(m)=="arturo"]; neutral=[m for m in ms if classify(m)=="neutral"]
    return {"partner_id":snapshot["partner_id"],"partner_name":snapshot["partner_name"],
        "generated_at":datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),"snapshot":snapshot["kpis"],
        "portfolio_partition":{"arturo_territory":len(arturo),"lucio_territory":len(top)+len(neutral),
            "top_performers":len(top),"neutral":len(neutral)},
        "top_performers":[{"merchant_id":m["merchant_id"],"merchant_name":m["merchant_name"],
            "segment":m["segment"],"country":m["country"],
            "gross_sales_uplift_pct":m.get("gross_sales_uplift_pct"),
            "repayment_pace_ratio":m.get("repayment_pace_ratio"),
            "partner_revenue_share":m.get("partner_revenue_share"),
            "financing_status":m.get("financing_status")}
            for m in sorted(top,key=lambda x:x.get("gross_sales_uplift_pct",0),reverse=True)],
        "icp_summary":result["icp_text"][:600]+"...","brief_text":result["brief"]}

def send_whatsapp(digest, whatsapp_to, snapshot):
    try:
        from twilio.rest import Client as TwilioClient
        try:
            sid   = st.secrets.get("TWILIO_ACCOUNT_SID") or os.getenv("TWILIO_ACCOUNT_SID")
            token = st.secrets.get("TWILIO_AUTH_TOKEN")  or os.getenv("TWILIO_AUTH_TOKEN")
            frm   = st.secrets.get("TWILIO_WHATSAPP_FROM") or os.getenv("TWILIO_WHATSAPP_FROM")
        except Exception:
            sid   = os.getenv("TWILIO_ACCOUNT_SID")
            token = os.getenv("TWILIO_AUTH_TOKEN")
            frm   = os.getenv("TWILIO_WHATSAPP_FROM")
        to_num = whatsapp_to if whatsapp_to.startswith("whatsapp:") else f"whatsapp:{whatsapp_to}"
        twilio = TwilioClient(sid, token)
        sentences = re.split(r"(?<=[.!?\n]) +", digest)
        chunks, current = [], ""
        for s in sentences:
            if len(current)+len(s)<1400: current+=(" " if current else "")+s
            else:
                if current: chunks.append(current)
                current=s
        if current: chunks.append(current)
        for chunk in chunks:
            twilio.messages.create(from_=frm, to=to_num, body=chunk)
        return True, len(chunks)
    except Exception as e:
        return False, str(e)


# ── HEADER ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="lh">
  <div>
    <h1>Lucio <em>Partner Intelligence</em></h1>
    <p>R2 &middot; Weekly digest agent &middot; Powered by Claude</p>
  </div>
  <div class="hr">v0 prototype<br>{datetime.now().strftime("%b %d, %Y")}</div>
</div>
""", unsafe_allow_html=True)


# ── INPUT CARD ────────────────────────────────────────────────────────────────
st.markdown('<div class="input-label">Partner WhatsApp number</div>', unsafe_allow_html=True)

col_input, col_btn = st.columns([2, 1], gap="medium")
with col_input:
    whatsapp_to = st.text_input(
        label="whatsapp",
        placeholder="+5521999999999",
        label_visibility="collapsed",
        help="Include country code. The weekly digest will be sent to this number."
    )
    st.markdown('<div class="input-note">Include country code &middot; e.g. +5521999999999 &middot; Number must be active on WhatsApp Sandbox</div>', unsafe_allow_html=True)

with col_btn:
    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
    run_clicked = st.button("RUN LUCIO", type="primary")



# ── RUN ───────────────────────────────────────────────────────────────────────
if run_clicked:
    if not whatsapp_to:
        st.warning("Please enter a WhatsApp number first.")
        st.stop()

    with st.spinner("Lucio is analyzing the portfolio — calling Claude 3 times (~45 seconds)..."):
        snapshot      = fetch(f"/partner/{PARTNER_ID}/snapshot")
        merchant_data = fetch(f"/partner/{PARTNER_ID}/merchants")
        weekly        = fetch(f"/partner/{PARTNER_ID}/weekly")
        result        = run_lucio(build_input(snapshot, merchant_data, weekly))
        result["api_payload"] = build_payload(snapshot, merchant_data, result)

        # Send WhatsApp
        ok, detail = send_whatsapp(result["brief"], whatsapp_to, snapshot)
        if ok:
            st.success(f"Digest sent to {whatsapp_to} via WhatsApp ({detail} message{'s' if detail>1 else ''}).")
        else:
            st.warning(f"WhatsApp not sent: {detail}")

        st.session_state["result"]        = result
        st.session_state["snapshot"]      = snapshot
        st.session_state["merchant_data"] = merchant_data
        st.session_state["weekly"]        = weekly
        st.session_state["chat"]          = [{"role":"assistant","content":result["brief"]}]
        st.session_state["whatsapp_to"]   = whatsapp_to

    st.rerun()


# ── PRE-RUN STATE ─────────────────────────────────────────────────────────────
if "result" not in st.session_state:
    st.markdown("""
    <div style="text-align:center;padding:60px 0;color:#C5C0B8;font-family:'DM Mono',monospace;font-size:12px;letter-spacing:0.08em;line-height:2;">
      Enter a WhatsApp number above and press RUN LUCIO<br>
      Lucio will analyze the portfolio and send the weekly digest
    </div>
    """, unsafe_allow_html=True)
    st.stop()


# ── RESULTS ───────────────────────────────────────────────────────────────────
result        = st.session_state["result"]
snapshot      = st.session_state["snapshot"]
merchant_data = st.session_state["merchant_data"]
weekly        = st.session_state["weekly"]
merchants     = merchant_data["merchants"]
kpis          = snapshot["kpis"]
pname         = snapshot["partner_name"]
rev_rate      = snapshot["rev_share_rate"]

tops     = [m for m in merchants if classify(m)=="top"]
tops_s   = sorted(tops, key=lambda x: x.get("gross_sales_uplift_pct",0), reverse=True)
arturo_c = sum(1 for m in merchants if classify(m)=="arturo")
top_c    = len(tops)
neutral_c= sum(1 for m in merchants if classify(m)=="neutral")
n        = len(merchants)

pre  = sum(m.get("gross_sales_pre_avg_monthly",0) for m in tops)
post = sum(m.get("gross_sales_90d_post",0)/3 for m in tops)
delta= post-pre; dpct=round(delta/pre*100,1) if pre>0 else 0
xrev = sum((m.get("gross_sales_90d_post",0)/3-m.get("gross_sales_pre_avg_monthly",0))*rev_rate
           for m in tops if m.get("gross_sales_90d_post",0)/3>m.get("gross_sales_pre_avg_monthly",0))
bmax = max(pre,post) or 1
ppct = round(pre/bmax*100); opct=round(post/bmax*100)

t1,t2,t3,t4,t5 = st.tabs(["Dashboard","Chain of thought","ICP Profile","Ask Lucio","API Output"])


# ── TAB 1: DASHBOARD ──────────────────────────────────────────────────────────
with t1:
    c1,c2 = st.columns([1.05,0.95], gap="large")
    with c1:
        st.markdown('<div class="sl">Weekly digest</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="bb">{result["brief"]}</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="sl">Top performers - gross sales before vs after credit</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="gc">
          <div style="display:flex;gap:0;margin-bottom:22px;align-items:flex-end;">
            <div style="flex:1;"><div style="font-size:11px;color:#9E9890;margin-bottom:4px;">BEFORE CREDIT</div>
              <div style="font-size:26px;font-weight:500;color:#1A1814;">${pre:,.0f}</div>
              <div style="font-size:10px;color:#9E9890;">avg monthly &middot; {top_c} merchants</div></div>
            <div style="padding:0 16px 8px;color:#C5C0B8;font-size:22px;">&rarr;</div>
            <div style="flex:1;"><div style="font-size:11px;color:#3D8C5A;margin-bottom:4px;">AFTER CREDIT</div>
              <div style="font-size:26px;font-weight:500;color:#1C3D2A;">${post:,.0f}</div>
              <div style="font-size:10px;color:#9E9890;">avg monthly &middot; 90-day window</div></div>
            <div style="text-align:right;flex:0.8;"><div style="font-size:11px;color:#9E9890;margin-bottom:4px;">DELTA</div>
              <div style="font-size:26px;font-weight:500;color:#1C3D2A;">+{dpct:.0f}%</div>
              <div style="font-size:10px;color:#3D8C5A;">+${delta:,.0f}/month</div></div>
          </div>
          <div style="margin-bottom:8px;">
            <div style="font-size:9px;color:#9E9890;margin-bottom:6px;">BEFORE CREDIT</div>
            <div style="background:#F4F1EA;border-radius:6px;height:36px;overflow:hidden;">
              <div style="background:#E2DDD4;height:100%;width:{ppct}%;border-radius:6px;display:flex;align-items:center;padding:0 12px;">
                <span style="font-size:11px;color:#6A6560;">${pre:,.0f}/mo</span></div></div></div>
          <div><div style="font-size:9px;color:#3D8C5A;margin-bottom:6px;">AFTER CREDIT</div>
            <div style="background:#F4F1EA;border-radius:6px;height:36px;overflow:hidden;">
              <div style="background:#1C3D2A;height:100%;width:{opct}%;border-radius:6px;display:flex;align-items:center;padding:0 12px;">
                <span style="font-size:11px;color:rgba(255,255,255,.9);">${post:,.0f}/mo</span></div></div></div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(f"""
        <div class="dc">
          <div class="dt">What this means for {pname}</div>
          <div class="db">Your {top_c} top-performing merchants grew combined monthly gross sales by
            <strong>+${delta:,.0f}</strong> after R2 credit, generating an estimated
            <strong>+${xrev:,.0f}/month</strong> in additional revenue.</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('<div class="sl">Top performers this week</div>', unsafe_allow_html=True)
        for m in tops_s[:5]:
            prior=m.get("total_prior_credits",0)
            st.markdown(f"""
            <div class="pc"><div class="pn2">{m['merchant_name']}</div>
              <div class="pm">{m['segment'].replace('_',' ')} &middot; {m.get('city','')}, {m['country']}
                &middot; {"repeat x"+str(prior) if prior>0 else "first credit"}</div>
              <div class="pst2">
                <div><div class="pv g">+{m.get('gross_sales_uplift_pct',0):.1f}%</div><div class="pl">sales uplift</div></div>
                <div><div class="pv am">{m.get('repayment_pace_ratio',0):.2f}x</div><div class="pl">pace ratio</div></div>
                <div><div class="pv mu">${m.get('partner_revenue_share',0):,.0f}</div><div class="pl">rev share</div></div>
              </div></div>
            """, unsafe_allow_html=True)


# ── TAB 2: CHAIN OF THOUGHT ───────────────────────────────────────────────────
with t2:
    st.markdown("<p style='font-size:12px;color:#9E9890;'>Lucio internal reasoning — logged to observability in production.</p>", unsafe_allow_html=True)
    ca,cb = st.columns(2, gap="large")
    with ca:
        st.markdown('<div class="sl">Step 1 - classification</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="tb">{result["classification_thinking"]}</div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="sl">All merchants - classification table</div>', unsafe_allow_html=True)
        rows=[]
        for m in merchants[:50]:
            c=classify(m); u=m.get("gross_sales_uplift_pct",0)
            b={"top":'<span class="bg tp">Top</span>',"neutral":'<span class="bg nt">Neutral</span>',"arturo":'<span class="bg at">Arturo</span>'}[c]
            rows.append(f'<tr><td style="font-size:9px;color:#9E9890;">{m["merchant_id"]}</td><td style="font-weight:500;">{m["merchant_name"]}</td><td>{m.get("repayment_pace_ratio",0):.2f}</td><td>{"+" if u>0 else ""}{u:.1f}%</td><td>{b}</td></tr>')
        st.markdown(f'<table class="ct"><thead><tr><th>ID</th><th>Merchant</th><th>Pace</th><th>Uplift</th><th>Label</th></tr></thead><tbody>{"".join(rows)}</tbody></table>', unsafe_allow_html=True)
    with cb:
        st.markdown('<div class="sl">Step 2 - ICP reasoning</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="tb">{result["icp_thinking"]}</div>', unsafe_allow_html=True)


# ── TAB 3: ICP PROFILE ───────────────────────────────────────────────────────
with t3:
    ci1,ci2 = st.columns([1,1], gap="large")
    with ci1:
        st.markdown('<div class="sl">Full ICP - what winners looked like before credit</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="ib">{result["icp_text"]}</div>', unsafe_allow_html=True)
    with ci2:
        st.markdown('<div class="sl">Hard floor metrics - use as lead filter</div>', unsafe_allow_html=True)
        for lb,vl,nt in [
            ("Platform tenure","13+ months","Time on platform before credit"),
            ("Monthly gross sales","$8,000+","Proven revenue baseline"),
            ("Sales growth trend","+4% monthly","Already growing before credit"),
            ("Refund rate","3.0% or less","Operational quality"),
            ("Customer rating","4.5 / 5.0+","Customer satisfaction"),
            ("Monthly orders","240+ / month","Sufficient volume"),
            ("Active listings","18+ items","Menu depth"),
            ("Segment","Restaurant / Dark kitchen","Retail underperforms"),
        ]:
            st.markdown(f'<div class="fc"><div><div class="fl">{lb}</div><div class="fn">{nt}</div></div><div class="fv">{vl}</div></div>', unsafe_allow_html=True)
        st.markdown("<div style='margin-top:14px;padding:14px;background:#EAF2ED;border:1px solid #C8DDD0;border-radius:8px;font-size:11px;color:#2A4A34;'><strong>How to use this:</strong> Apply these filters when deciding which merchants to show the R2 credit offer to. Merchants matching 7+ criteria are your highest-probability conversions.</div>", unsafe_allow_html=True)


# ── TAB 4: ASK LUCIO ─────────────────────────────────────────────────────────
with t4:
    st.markdown("<p style='font-size:12px;color:#9E9890;'>Lucio received the weekly digest and is ready to continue the conversation.</p>", unsafe_allow_html=True)
    if "chat" not in st.session_state:
        st.session_state["chat"]=[{"role":"assistant","content":result["brief"]}]
    for msg in st.session_state["chat"]:
        css="cu" if msg["role"]=="user" else "cl"
        st.markdown(f'<div class="{css}">{msg["content"]}</div>', unsafe_allow_html=True)
    ui = st.chat_input("Ask Lucio anything about this week...")
    if ui:
        st.session_state["chat"].append({"role":"user","content":ui})
        top_detail = "\n".join([
            f"  {i+1}. {m['merchant_name']} ({m['segment'].replace('_',' ')}, {m['country']}): "
            f"+{m.get('gross_sales_uplift_pct',0):.1f}% uplift, {m.get('repayment_pace_ratio',0):.2f}x pace, "
            f"${m.get('partner_revenue_share',0):,.0f} rev share"
            for i,m in enumerate(tops_s[:5])
        ])
        sys_p = (
            f"You are Lucio, R2 partner intelligence agent. "
            f"You just sent the weekly digest to {pname} credit manager. "
            f"Portfolio: {top_c} top performers, {arturo_c} Arturo territory, {n} total merchants. "
            f"Weekly gross sales: ${kpis['weekly_gross_sales_usd']:,.0f}. "
            f"Revenue share: ${kpis['total_revenue_share_usd']:,.0f}. "
            f"Approval rate: {kpis['approval_rate_pct']}%.\n\n"
            f"TOP PERFORMERS:\n{top_detail}\n\n"
            f"Rules: never mix segments, ground every answer in real data, "
            f"respond in the same language the user writes in, "
            f"be concise warm and data-driven."
        )
        msgs=[{"role":m["role"],"content":m["content"]} for m in st.session_state["chat"]]
        client = get_client()
        with st.spinner("Lucio is thinking..."):
            resp=client.messages.create(model="claude-sonnet-4-20250514",max_tokens=800,system=sys_p,messages=msgs)
            reply=resp.content[0].text
        st.session_state["chat"].append({"role":"assistant","content":reply})
        st.rerun()


# ── TAB 5: API OUTPUT ─────────────────────────────────────────────────────────
with t5:
    ca1,ca2 = st.columns([1,1], gap="large")
    with ca1:
        st.markdown('<div class="sl">Endpoint</div>', unsafe_allow_html=True)
        st.markdown('<div class="ae">POST /v1/partners/{partner_id}/intelligence/brief</div>', unsafe_allow_html=True)
        st.code('import requests\n\nr = requests.post(\n    "https://api.r2.co/v1/partners/1001/intelligence/brief",\n    headers={"Authorization": "Bearer YOUR_TOKEN"},\n    json={"lookback_days": 7}\n)\nbrief = r.json()\nprint(brief["brief_text"])', language="python")
    with ca2:
        st.markdown('<div class="sl">JSON payload - this run</div>', unsafe_allow_html=True)
        ps=json.dumps(result["api_payload"],indent=2,ensure_ascii=False)
        st.markdown(f'<div class="jb">{ps}</div>', unsafe_allow_html=True)
        st.download_button("Download JSON",ps,f"lucio_{PARTNER_ID}_{datetime.now().strftime('%Y%m%d')}.json","application/json",use_container_width=True)
