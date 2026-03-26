import os
import json
from flask import Flask, request
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
anthropic_client = Anthropic()
twilio_client    = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))

CONTEXT_FILE  = "/workspaces/lucio-r2/lucio_context.json"
HISTORY_FILE  = "/workspaces/lucio-r2/lucio_chat_history.json"

def load_context():
    if os.path.exists(CONTEXT_FILE):
        with open(CONTEXT_FILE) as f:
            return json.load(f)
    return None

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE) as f:
            return json.load(f)
    return []

def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

def build_system_prompt(context):
    top_detail = "\n".join([
        f"  {i+1}. {m['merchant_name']} ({m['segment'].replace('_',' ')}, {m['country']}): "
        f"+{m.get('gross_sales_uplift_pct',0)}% sales uplift, "
        f"{m.get('repayment_pace_ratio',0)}x repayment pace, "
        f"${m.get('partner_revenue_share',0):,.0f} rev share"
        for i,m in enumerate(context.get("top_performers", [])[:5])
    ])

    return (
        f"You are Lucio, R2 partner intelligence agent. "
        f"You sent the weekly digest to {context['partner_name']} credit program manager. "
        f"You are now having a WhatsApp conversation with them.\n\n"
        f"PORTFOLIO CONTEXT:\n"
        f"- Weekly gross sales: ${context['kpis']['weekly_gross_sales_usd']:,.0f}\n"
        f"- Revenue share earned: ${context['kpis']['total_revenue_share_usd']:,.0f}\n"
        f"- Approval rate: {context['kpis']['approval_rate_pct']}%\n"
        f"- Active merchants: {context['kpis']['active_merchants']}\n\n"
        f"TOP PERFORMERS THIS WEEK:\n{top_detail}\n\n"
        f"RULES:\n"
        f"- Be concise - this is WhatsApp, keep responses under 300 words\n"
        f"- Never mix data between portfolio segments\n"
        f"- Ground every answer in the actual data above\n"
        f"- Help with: marketing campaigns, targeting, portfolio questions\n"
        f"- Talk to a marketing manager, not a data analyst\n"
        f"- Use emojis sparingly to keep it warm and human\n"
        f"- CRITICAL: Always respond in the SAME language the user writes in. Portuguese reply in Portuguese. Spanish reply in Spanish. English reply in English. Never switch languages."
    )

@app.route("/webhook", methods=["POST"])
def webhook():
    incoming_msg = request.values.get("Body", "").strip()
    from_number  = request.values.get("From", "")

    print(f"\nMessage from {from_number}: {incoming_msg}")

    context = load_context()
    if not context:
        resp = MessagingResponse()
        resp.message("Lucio is not active yet. Please trigger the weekly digest first.")
        return str(resp)

    # Load conversation history
    history = load_history()

    # Add user message
    history.append({"role": "user", "content": incoming_msg})

    # Keep last 10 messages to avoid token limits
    if len(history) > 10:
        history = history[-10:]

    # Call Claude
    response = anthropic_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        system=build_system_prompt(context),
        messages=history
    )

    reply = response.content[0].text

    # Add assistant reply to history
    history.append({"role": "assistant", "content": reply})
    save_history(history)

    # Send reply via Twilio
    twilio_client.messages.create(
        from_=os.getenv("TWILIO_WHATSAPP_FROM"),
        to=from_number,
        body=reply
    )

    # Return TwiML response
    resp = MessagingResponse()
    return str(resp)

@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok", "lucio": "ready"}

if __name__ == "__main__":
    print("Starting Lucio WhatsApp webhook on port 5000...")
    app.run(host="0.0.0.0", port=5000, debug=False)
