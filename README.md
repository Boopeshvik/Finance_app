# 💰 Personal Finance Assistant — AI-Powered Finance Intelligence

> **A privacy-first, agentic finance tracker built with Claude AI, FastAPI, and PostgreSQL.**  
> Natural language. Real insights. Your data stays yours.

🔗 **Live App:** [finance-app-gilt-phi.vercel.app](https://finance-app-gilt-phi.vercel.app/login.html)

---

## 🧠 Why I Built This

Every mainstream finance app reads your data, sells it, and spams your inbox.

I wanted to build something different — a finance tool where an AI agent genuinely understands your spending, answers real questions in plain English, and never touches your data for anything other than giving you better insights.

This is also a personal portfolio piece demonstrating how I think about **agentic AI product design**: not just calling an LLM, but building an agent loop that autonomously decides what data to fetch, how to analyse it, and what to surface back to the user.

---

## 🎯 The Problem It Solves

| Pain Point | How This App Solves It |
|---|---|
| Finance apps sell your data | Zero third-party tracking. Your DB, your data |
| Manual transaction categorisation | Natural language input — just type what you spent |
| Static dashboards with no insight | Claude AI analyses patterns and gives real advice |
| Generic reports | Personalised summaries based on your actual spending |
| Complex interfaces | Conversational UI — ask questions, get answers |

---

## 🏗️ Architecture & Key Design Decisions

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Frontend      │────▶│   FastAPI        │────▶│   Claude AI     │
│   (HTML/JS)     │     │   Backend        │     │   (Tool-Use)    │
│   Vercel        │     │   Render         │     │   Agent Loop    │
└─────────────────┘     └────────┬─────────┘     └─────────────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │   PostgreSQL     │
                         │   (Render)       │
                         └──────────────────┘
```

**Why FastAPI?** Async-first, lightweight, and perfect for building API-driven AI products that need to scale without overhead.

**Why Claude tool-use (not just chat)?** I wanted the AI to *act*, not just respond. Claude's tool-use API lets the agent decide which financial data to query, run aggregations autonomously, and return structured insights — rather than me pre-programming every possible query.

**Why privacy-first architecture?** Product decision: the competitive differentiator isn't features, it's trust. No analytics SDKs, no third-party integrations that phone home, no marketing emails.

---

## ✨ Key Features

- **Natural language transaction entry** — "Spent £45 at Tesco on groceries" → parsed and categorised automatically
- **Agentic AI insights** — Claude autonomously queries your data, identifies patterns, and surfaces what matters
- **Conversational reporting** — Ask "How much did I spend on food last month?" and get a real answer
- **Category breakdowns** — Automatic spend categorisation with trend analysis
- **Privacy-first** — Self-contained, no data sold or shared

---

## 🤖 How the Agent Loop Works

```python
# Simplified agent loop logic
1. User sends natural language query
2. Claude receives query + available tools (get_transactions, summarise_spend, categorise)
3. Claude autonomously decides which tools to call and in what order
4. Tool results fed back to Claude for synthesis
5. Claude returns structured insight + natural language explanation
6. Frontend renders response with relevant data visualisation
```

This is **not** a simple chatbot wrapper. The agent makes real decisions about what data to retrieve and how to process it — reducing manual analysis effort by ~70% in testing.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Frontend | HTML, CSS, JavaScript |
| Backend | Python, FastAPI |
| AI | Anthropic Claude API (tool-use) |
| Database | PostgreSQL (Render) |
| Auth | JWT-based authentication |
| Deployment | Vercel (frontend) + Render (backend) |

---

## 📁 Project Structure

```
Finance_app/
├── frontend/          # HTML/JS UI — login, dashboard, chat interface
├── models/            # SQLAlchemy database models
├── routers/           # FastAPI route handlers (auth, transactions, AI)
├── schemas/           # Pydantic request/response schemas
├── auth.py            # JWT authentication logic
├── database.py        # DB connection & session management
├── main.py            # FastAPI app entry point
└── requirements.txt   # Dependencies
```

---

## 💡 What I Learned / Would Do Next

**Learned:**
- Designing agent tool schemas is a product decision, not just a technical one — the tools you give Claude define what it can reason about
- Privacy-first architecture requires deliberate choices at every layer (auth, logging, third-party dependencies)
- FastAPI + Render is a solid low-cost stack for AI product prototyping

**What I'd build next:**
- 🔄 Recurring transaction detection and subscription tracking
- 📊 Investment portfolio view with AI-generated commentary
- 🔔 Proactive alerts ("You're on track to overspend on dining this month")
- 📱 Mobile-responsive PWA version
- 🧾 Receipt scanning via image input to Claude

---

## 🚀 Running Locally

```bash
git clone https://github.com/Boopeshvik/Finance_app.git
cd Finance_app

pip install -r requirements.txt

# Set environment variables
export DATABASE_URL=your_postgresql_url
export ANTHROPIC_API_KEY=your_claude_api_key
export SECRET_KEY=your_jwt_secret

uvicorn main:app --reload
```

Then open `frontend/index.html` or point to `localhost:8000`.

---

## 👤 About the Builder

Built by **Boopesh Vikram** — AI Product Leader and hands-on AI practitioner.  
📌 [boopeshvikram.com](https://www.boopeshvikram.com) · [LinkedIn](https://www.linkedin.com/in/boopeshvikram) · [GitHub](https://github.com/Boopeshvik)
