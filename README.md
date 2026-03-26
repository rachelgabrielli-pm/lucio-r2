# Lucio — Partner Intelligence Agent
### A Senior AI PM Case Study for R2

---

## Try the prototype — no installation required

Open this URL in your browser:

### [lucio-r2-mchkpsbvzey2zwo9pyzb4j.streamlit.app](https://lucio-r2-mchkpsbvzey2zwo9pyzb4j.streamlit.app)

Enter a WhatsApp number and click **RUN LUCIO**. The agent analyzes the portfolio, generates the weekly digest, and sends it via WhatsApp. Reply to the message to have a live conversation with Lucio.

The prototype runs fully in the cloud. No setup, no API keys (Application Programming Interface keys), no local installation needed.

> **WhatsApp sandbox limitation:** The prototype uses Twilio's free sandbox, which only delivers messages to numbers that have opted in manually. Before testing, the recipient must open WhatsApp, add **+1 415 523 8886** as a contact, and send the message `join [your-sandbox-word]` (find your exact word at console.twilio.com → Messaging → Try it out → Send a WhatsApp message).
>
> This opt-in is required for every new number. In production with a Twilio-approved account, any number receives messages without this step.

**Repository:** [github.com/rachelgabrielli-pm/lucio-r2](https://github.com/rachelgabrielli-pm/lucio-r2)
**Backend API (Application Programming Interface):** [lucio-r2-production.up.railway.app/health](https://lucio-r2-production.up.railway.app/health)

---

## 1. The use case — why this, why now

### The problem

R2 partners (Uber Eats, Rappi, Clip, inDrive) embed R2's credit product inside their platforms. When a merchant gets approved and receives a loan, R2 earns a revenue share from the partner. When that merchant grows post-credit, the partner earns more transaction fees too. It is a genuinely aligned incentive structure.

The problem: **partners have no visibility into what happens after disbursement.**

They don't log into R2's systems. They have no dashboard. They receive no signal about which merchants are thriving, which are struggling, or, most importantly, which merchants in their platform look like the ones that succeeded. The partner's credit program manager is flying blind when deciding where to direct the next wave of credit offers.

This creates two compounding losses:
1. **Revenue left on the table** — partners under activate their merchant base because they don't know who to target
2. **Missed retention signal** — R2 can't show partners the ROI of the credit program in concrete, actionable terms

### Arturo and Lucio — two agents, one data source, opposite missions

R2 already runs **Arturo**, a collections agent that monitors merchants showing risk signals and intervenes before default. Arturo watches the portfolio for trouble and acts early to protect R2's capital.

**Lucio is Arturo's counterpart.** Both agents read from the same merchant signals data source. They are mutually exclusive by design, no merchant can appear in both agents' territory at the same time.

```
Same data source — zero overlap

Arturo: repayment_pace_ratio < 0.8  →  merchant paying slower than projected
        OR status = PAUSED           →  intervene, protect the portfolio

Lucio:  repayment_pace_ratio ≥ 1.1  →  merchant paying faster than projected
        AND gross_sales_uplift ≥ 25% →  amplify, grow the program

Neutral: everything else             →  monitored, not yet actionable
```

Together, Arturo and Lucio give R2 full coverage of the portfolio: one agent managing risk, one agent driving growth. The partner only ever sees Lucio's output, the good news, the actionable intelligence, the growth signal. Arturo operates silently on R2's side.

---

## 2. The agent — how it works

Every week, Lucio sends the partner's credit program manager a digest via WhatsApp containing:

1. **Weekly program snapshot** — gross sales, consistency, approval rate, new merchants onboarded, revenue share earned this week
2. **Top performers this week** — who is thriving, by how much, and how fast they are repaying
3. **What your winners looked like before credit** — the pre-credit ICP (Ideal Customer Profile), expressed as a concrete checklist the partner can use to filter their merchant base
4. **A call to action** — use this to grow your program

After receiving the digest, the partner can reply on WhatsApp and have a conversation with Lucio, asking for marketing campaign copy, targeting recommendations, or portfolio questions. Lucio responds in real time using the digest as context, without needing to re-query the database.

### Agent architecture — single agent, sequential steps

Lucio is **not** a multi-agent system. One agent, three tasks in sequence:

```
Step 1: Classify every merchant
         → Top Performer / Neutral / Arturo territory
         → Uses extended thinking for transparent reasoning

Step 2: Build the pre-credit ICP (Ideal Customer Profile)
         → Extracts what top performers looked like BEFORE credit
         → The only output the partner can act on to change future behavior

Step 3: Write the weekly digest
         → Combines Step 1 classification + Step 2 ICP
         → Formatted for WhatsApp delivery
         → Includes fallback if no top performers this week
```

Each step builds on the previous output. There is no parallelism and no need for orchestration. A single agent with sequential tasks is simpler, cheaper, and more debuggable than a multi-agent system for this workflow.

---

## 3. Architecture

```
Partner platform
      │
      │  collection_created events (daily sales + repayments)
      ▼
R2 Data Layer (SQLite prototype / PostgreSQL in production)
  ├── merchants          — profile snapshot at application time
  ├── financings         — loan terms, disbursement, repayment progress
  ├── daily_sales        — gross sales + repayment per merchant per day
  └── credit_applications — full funnel, approved and denied

      │
      │  pre-computed weekly metrics (no LLM needed)
      ▼
FastAPI Backend (Railway)
  ├── GET /partner/{id}/snapshot    — KPIs: revenue share, approval rate, consistency
  ├── GET /partner/{id}/merchants   — portfolio with pace ratio calculated on-the-fly
  └── GET /partner/{id}/weekly      — this week's gross sales only

      │
      │  structured context passed to agent
      ▼
Lucio Agent (Claude claude-sonnet-4-20250514)
  ├── Step 1: Classify (extended thinking enabled)
  ├── Step 2: Build ICP (extended thinking enabled)
  └── Step 3: Write digest

      │
      ├── WhatsApp via Twilio  →  partner's credit program manager
      ├── Webhook (Flask)      →  conversational replies from WhatsApp
      └── JSON API             →  partner's own systems (CRM, dashboard)

Streamlit UI (Streamlit Cloud)
  ├── Tab 1: Dashboard — digest + gross sales chart + top performers
  ├── Tab 2: Chain of thought — Lucio's classification reasoning
  ├── Tab 3: ICP Profile — pre-credit profile + hard floor metrics
  ├── Tab 4: Ask Lucio — conversational chat using digest context
  └── Tab 5: API Output — structured JSON (JavaScript Object Notation) payload + integration examples
```

### Key architecture decisions

**Backend pre-computes, Lucio reasons.** Weekly KPIs (Key Performance Indicators) (gross sales, consistency, approval rate) are calculated by the backend from raw data. The LLM never sees raw SQL, it receives structured, pre-aggregated signals. This reduces token usage, improves accuracy, and keeps the AI focused on reasoning rather than arithmetic.

**Slim merchant context.** With 136 merchants in the dataset, passing all merchant data to the LLM would exceed rate limits. Lucio receives only the top 40 merchants by repayment pace ratio, with only the fields relevant to classification and ICP building.

**Extended thinking for classification.** Steps 1 and 2 use Claude's extended thinking mode (`budget_tokens: 3000–4000`). The chain of thought is logged and visible in the Streamlit UI, making Lucio's decisions auditable and debuggable.

**No MCP (Model Context Protocol) for V0.** The digest already contains the context Lucio needs to answer follow-up questions. MCP would only be needed for free-form queries requiring new data lookups at conversation time (V1+ roadmap). For V0, context-in-prompt is sufficient and faster to ship.

**WhatsApp over dashboard.** Partners don't log into R2's systems. They live in WhatsApp. Lucio finds them where they already are, mirroring the delivery model R2 uses for Rita on the merchant side.

---

## 4. Trade-offs

| Decision | What was optimized | What was sacrificed |
|----------|--------------------|---------------------|
| SQLite over PostgreSQL | Zero infrastructure setup, runs anywhere | No concurrent writes, not production-ready |
| Single agent over multi-agent | Simpler, cheaper, more debuggable | ~45s latency from 3 sequential LLM calls |
| WhatsApp sandbox over production | Fast to demo, zero cost | Recipients must pre-register; not scalable |
| Context-in-prompt over MCP | Faster to ship, no extra infrastructure | Conversational mode can't query new data dynamically |
| Weekly digest over real-time | Matches partner's workflow cadence | Can't respond to intraday events |
| Synthetic data over real data | Safe to share publicly, fast to iterate | ICP conclusions are illustrative, not validated |

### Risks

**Hallucination in the digest.** The agent could cite incorrect numbers if the context is ambiguous. Mitigated by: passing pre-computed numbers directly in the prompt, instructing the LLM to use only provided figures, and making the chain of thought visible for auditing.

**Rate limits at scale.** At 136 merchants, token usage per run is near the limit. At production scale (thousands of merchants per partner), the context strategy needs to change — pre-filtering to top 50 by pace ratio before passing to the LLM.

**Partner data privacy.** The digest contains merchant-level performance data. Before production, data sharing agreements with partners need to define what Lucio can surface and to whom.

---

## 5. Production roadmap

### V0 → V1: One real partner, real data

| What changes | How |
|---|---|
| SQLite → PostgreSQL | Standard migration, schema is already clean |
| Synthetic data → real collection events | R2 already receives these — pipe them into the same schema |
| Twilio sandbox → production number | Twilio production upgrade |
| Manual trigger → weekly cron | Simple scheduler (Celery, cron job, or Railway cron) |
| Single partner → configurable | Partner ID already parameterized throughout |

**Evaluation before V1 launch:**
- Human review of 20 consecutive digests before sending to any partner, checking for numeric accuracy and hallucinations
- A/B test (A/B being two variants tested simultaneously): split partners into two groups. Group A receives the Lucio weekly digest. Group B continues with no change to their current experience. After 8 weeks, compare whether Group A's credit program managers started targeting more merchants, and whether their approval rates and revenue share grew relative to Group B. This tells us whether Lucio is actually changing partner behavior, not just being read and forgotten.
- Hallucination audit: compare every numeric claim in digest to backend values

### V1 → V2: ICP engine + lookalike recommendations

- Build a scoring model: given the pre-credit ICP, score every merchant in the partner's platform, including ones that have never applied for credit
- Surface the top candidates in the digest: "Here are 20 merchants already on your platform who match the exact profile of your top performers before credit, they have not applied yet, but they should. Use this list for your next targeted campaign."
- MCP integration so Lucio can query the backend dynamically during conversation

### V2 → V3: Partner shares full merchant base

- Partner pushes their entire merchant roster to R2
- R2 scores all merchants proactively, not just those who applied
- Lucio shifts from reactive (here's what happened) to proactive (here's who to target next week)

### Observability requirements for production

- Log every LLM call: prompt, response, latency, token usage
- Alert if digest numeric values deviate >10% from backend values (hallucination detection)
- Track partner engagement: Did they read it? Did they reply? Did approval rate change?
- Weekly digest quality score: human reviewer rates each digest 1-5 before it becomes fully automated

---

## 6. Impact — how success is measured

### Primary metrics (partner outcomes)

| Metric | Baseline | Target (6 months) |
|--------|----------|-------------------|
| Partner credit approval rate | Current rate | +15% lift for partners receiving Lucio |
| Merchants targeted per week | Unknown — no signal today | Measurable and growing week over week |
| Partner revenue share per month | Current level | +20% for active Lucio partners |

### Secondary metrics (product health)

| Metric | Target |
|--------|--------|
| Digest open rate (WhatsApp read receipts) | >80% |
| Conversational reply rate | >30% of digests receive at least one reply |
| Hallucination rate | <1% of numeric claims in digest |
| Time to generate digest | <60 seconds end-to-end |

### Leading indicator

The most important leading indicator is the simplest: **does the partner's credit program manager reply to the digest?**

A reply means they read it, found it useful, and want to go deeper. That is the signal that Lucio is creating real value, not just sending a report no one reads.

---

## Running locally

### Prerequisites
- Python 3.12+
- Anthropic API key
- Twilio account (WhatsApp sandbox)

### Setup

```bash
git clone https://github.com/rachelgabrielli-pm/lucio-r2
cd lucio-r2
pip install -r requirements.txt
```

Create `.env`:
```
ANTHROPIC_API_KEY=your_key
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
TWILIO_WHATSAPP_TO=whatsapp:+your_number
```

### Initialize the database

```bash
cd backend
python db.py      # creates schema
python seed.py    # seeds 136 merchants + 90 days of daily sales
cd ..
```

### Start services

```bash
# Terminal 1 — Backend API
cd backend && python api.py

# Terminal 2 — Streamlit UI
streamlit run app.py

# Terminal 3 — WhatsApp webhook (optional)
python webhook.py
ngrok http 5000   # set ngrok URL + /webhook as Twilio inbound URL
```

### Simulate a new week

```bash
python simulate_week.py   # new daily sales + new merchant applications
python lucio_trigger.py   # generate digest + send to WhatsApp
```

---

## Repository structure

```
lucio-r2/
├── app.py                  — Streamlit UI (5 tabs)
├── agent.py                — Lucio agent (Claude, 3-step sequential)
├── simulate_week.py        — Inserts new week of data + new merchant applications
├── lucio_trigger.py        — Runs Lucio + sends digest via WhatsApp
├── webhook.py              — Flask webhook for WhatsApp conversation
├── data/
│   └── merchants.json      — Original 25 merchant profiles
├── backend/
│   ├── db.py               — SQLite schema
│   ├── seed.py             — Seeds 136 merchants + 90 days of daily sales
│   ├── api.py              — FastAPI endpoints
│   ├── start.py            — Railway startup (auto-seeds on deploy)
│   └── lucio.db            — SQLite database (generated at runtime)
├── sql/
│   └── lucio_merchant_query.sql
├── railway.json            — Railway deployment config
└── requirements.txt
```

---

*Built by Rachel Gabrielli as a Senior AI PM case study for R2. March 2026.*
*AI dev tools used: Claude (Anthropic) for code generation, architecture review, and document drafting.*
