[README.md](https://github.com/user-attachments/files/30134606/README.md)
# research-agent
An AI research agent that decides when to search and when to answer, built with LangGraph and Groq
<div align="center">

# 🔎 Research Agent

**An AI agent that decides *on its own* when to search the web — and when it already knows enough to answer.**

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-Agent%20Orchestration-1C3C3C?style=flat-square)](https://www.langchain.com/langgraph)
[![Groq](https://img.shields.io/badge/Groq-Llama%203.3%2070B-F55036?style=flat-square)](https://groq.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-UI-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)](https://streamlit.io)
[![License](https://img.shields.io/badge/License-MIT-A379D9?style=flat-square)](#)

*Not another RAG chatbot. A multi-step agent that plans, searches, self-checks, and cites its sources.*

</div>

---

## 🧠 What makes this different

Most portfolio RAG projects do **one** retrieval pass and generate an answer. This agent runs a genuine **reasoning loop** — it plans, searches, evaluates whether it actually has enough information, and repeats until confident (or hits a safety limit).

```
START → 🧠 planner → has enough info?
                        ├── NO  → 🔍 search → back to planner (loop)
                        └── YES → ✅ answer → END
```

## ✨ Features

| Feature | What it does |
|---|---|
| 🧠 **Multi-step planning** | LLM decides *each turn* whether to search again or answer — structured JSON output, not guesswork |
| 🧹 **Result quality filtering** | Discards keyword-spam snippets and corrupted/merged page titles before they reach the LLM |
| 🔁 **Query deduplication** | Jaccard-similarity check stops the agent from wastefully re-searching near-identical queries |
| 🔗 **Numbered citations** | Clean inline `[1]` `[2]` citations mapped to a verified Sources list — URLs come from real search data, never hallucinated |
| ⚖️ **Contradiction detection** | When sources disagree, the agent says so explicitly instead of silently picking one number |
| 📈 **Trend vs. conflict reasoning** | Tells the difference between "sources disagree" and "this value changed over time" |
| 🚫 **No self-invented math** | Never averages/combines numbers across sources — only reports what's actually there |
| 🎯 **Confidence scoring** | Every answer ships with a 1–10 confidence score *and* a reason, generated in the same LLM call |
| 💬 **Conversation memory** | Understands follow-ups in context, and skips redundant searches when it already knows enough |

## 🛠️ Tech Stack

- **[LangGraph](https://www.langchain.com/langgraph)** — orchestrates the planner → search → answer loop as a state graph
- **[Groq API](https://groq.com)** (Llama 3.3 70B) — fast inference for planning, filtering, and synthesis
- **[DDGS](https://pypi.org/project/ddgs/)** — free web search, no API key required
- **[Streamlit](https://streamlit.io)** — chat UI with live "agent thinking" trace and light/dark theme support
- **Python** — `TypedDict` state modeling, JSON-mode prompting with safe fallback parsing

## 📂 Project Structure

```
research-agent/
├── agent.py          # Core LangGraph logic — state, planner/search/answer nodes, graph
├── tools.py          # Web search + result quality filtering
├── app.py             # Streamlit chat UI with conversation memory
├── requirements.txt
└── .streamlit/
    └── config.toml    # Light/dark theme configuration
```

## 🚀 Setup

```bash
git clone https://github.com/DarakhshanMujtaba/research-agent.git
cd research-agent

python -m venv venv
venv\Scripts\Activate.ps1        # Windows PowerShell
# source venv/bin/activate       # Mac/Linux

pip install -r requirements.txt
```

Create a `.env` file in the project root:
```
GROQ_API_KEY=your_groq_api_key_here
```
> Get a free key at [console.groq.com](https://console.groq.com)

Run it:
```bash
streamlit run app.py
```

## 💡 Example

> **"What percentage of Pakistan's electricity currently comes from renewable energy?"**

The agent finds sources citing **7%**, **10.57%**, and a **53.7%** figure that includes hydro/nuclear — and instead of picking one, it explains *why* the numbers differ (different definitions of "renewable," different reporting periods), rates its own confidence accordingly, and traces every claim back to a numbered source.

## 🔭 What I'd add next

- [ ] Cross-encoder reranking on top of the current filtering, for better relevance on ambiguous queries
- [ ] Persistent conversation storage (currently resets on page refresh)
- [ ] Additional tool types beyond web search (calculator, Wikipedia-specific lookup)

---

<div align="center">

*Built as a hands-on deep-dive into agentic LLM systems — planning loops, structured tool use, and the reliability techniques (citation grounding, contradiction handling, confidence calibration) that separate a demo from something trustworthy.*

</div>
