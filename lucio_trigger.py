import os
import sys
import re
import requests
from dotenv import load_dotenv
from twilio.rest import Client

load_dotenv()

API_BASE   = "http://localhost:8000"
PARTNER_ID = 1001

def fetch(endpoint):
    r = requests.get(f"{API_BASE}{endpoint}", timeout=10)
    r.raise_for_status()
    return r.json()

def split_digest(digest, max_len=1400):
    """Split digest at sentence boundaries to avoid cutting mid-sentence."""
    sentences = re.split(r'(?<=[.!?\n]) +', digest)
    chunks = []
    current = ""
    for s in sentences:
        if len(current) + len(s) < max_len:
            current += (" " if current else "") + s
        else:
            if current:
                chunks.append(current)
            current = s
    if current:
        chunks.append(current)
    return chunks

def run_lucio_and_send():
    print("Fetching data from backend...")
    snapshot      = fetch(f"/partner/{PARTNER_ID}/snapshot")
    merchant_data = fetch(f"/partner/{PARTNER_ID}/merchants")
    weekly        = fetch(f"/partner/{PARTNER_ID}/weekly")

    partner_name = snapshot["partner_name"]
    kpis         = snapshot["kpis"]

    print(f"Running Lucio for {partner_name}...")

    sys.path.append(os.path.dirname(__file__))
    from agent import run_lucio

    lucio_input = {
        "partner_id":     snapshot["partner_id"],
        "partner_name":   partner_name,
        "rev_share_rate": snapshot["rev_share_rate"],
        "funnel": {
            "total_applications": kpis["total_applications"],
            "total_approved":     kpis["total_approved"],
            "total_denied":       kpis["total_denied"],
            "approval_rate_pct":  kpis["approval_rate_pct"],
            "top_denial_reasons": snapshot["top_denial_reasons"]
        },
        "merchants": merchant_data["merchants"],
        "weekly_signals": {
            "weekly_gross_sales_usd":      kpis["weekly_gross_sales_usd"],
            "weekly_consistency_pct":      kpis["weekly_consistency_pct"],
            "merchants_selling_this_week": kpis["merchants_selling_this_week"],
            "week_start": weekly["week_start"],
            "week_end":   weekly["week_end"],
        }
    }

    result = run_lucio(lucio_input)
    digest = result["brief"]

    print("\nDigest generated. Sending via WhatsApp...")

    twilio_client = Client(
        os.getenv("TWILIO_ACCOUNT_SID"),
        os.getenv("TWILIO_AUTH_TOKEN")
    )
    from_number = os.getenv("TWILIO_WHATSAPP_FROM")
    to_number   = os.getenv("TWILIO_WHATSAPP_TO")

    chunks = split_digest(digest)

    for i, chunk in enumerate(chunks):
        msg = twilio_client.messages.create(
            from_=from_number,
            to=to_number,
            body=chunk
        )
        print(f"  Message {i+1}/{len(chunks)} sent: {msg.sid}")
        if i < len(chunks) - 1:
            import time; time.sleep(3)

    print(f"\nDigest sent to {to_number} via WhatsApp.")
    print("Reply to start a conversation with Lucio.")

    # Save context for webhook conversation
    import json
    context = {
        "digest":       digest,
        "icp_text":     result["icp_text"],
        "partner_name": partner_name,
        "kpis":         kpis,
        "top_performers": [
            m for m in merchant_data["merchants"]
            if m.get("repayment_pace_ratio", 0) >= 1.1
            and m.get("financing_status") in ["ACTIVE", "PAID"]
            and m.get("gross_sales_uplift_pct", 0) >= 25
        ]
    }
    with open("/workspaces/lucio-r2/lucio_context.json", "w") as f:
        json.dump(context, f, indent=2, ensure_ascii=False)
    print("Context saved for WhatsApp conversation.")

if __name__ == "__main__":
    run_lucio_and_send()
