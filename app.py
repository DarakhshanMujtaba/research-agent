import re
import html

import streamlit as st
from agent import run_agent

# ----------------------------------------------------------------------------
# Custom avatars (raw SVG - Streamlit converts these to data-URI images).
# Colors match the app's theme (see .streamlit/config.toml).
# ----------------------------------------------------------------------------
USER_AVATAR = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <circle cx="32" cy="32" r="32" fill="#BFDBFE"/>
  <path d="M10 57c3-13.5 11-21 22-21s19 7.5 22 21" fill="#FFFFFF"/>
  <circle cx="32" cy="27" r="15" fill="#FFFFFF"/>
  <path d="M17.5 23c1-8.5 7-14 14.5-14s13.5 5.5 14.5 14c-4-3-9-4.5-14.5-4.5s-10.5 1.5-14.5 4.5z" fill="#0F172A"/>
  <circle cx="26.5" cy="28" r="2.6" fill="#0F172A"/>
  <circle cx="37.5" cy="28" r="2.6" fill="#0F172A"/>
  <path d="M25.5 34.5c2.8 2.6 10.2 2.6 13 0" stroke="#0F172A" stroke-width="2.4" fill="none" stroke-linecap="round"/>
</svg>
"""

ASSISTANT_AVATAR = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <circle cx="32" cy="32" r="32" fill="#1E3A8A"/>
  <line x1="32" y1="10" x2="32" y2="18" stroke="#93C5FD" stroke-width="3" stroke-linecap="round"/>
  <circle cx="32" cy="8" r="4" fill="#93C5FD"/>
  <rect x="6" y="27" width="6" height="12" rx="3" fill="#93C5FD"/>
  <rect x="52" y="27" width="6" height="12" rx="3" fill="#93C5FD"/>
  <rect x="14" y="18" width="36" height="30" rx="11" fill="#93C5FD"/>
  <rect x="20" y="27" width="10" height="10" rx="3" fill="#1E3A8A"/>
  <rect x="34" y="27" width="10" height="10" rx="3" fill="#1E3A8A"/>
  <circle cx="25" cy="32" r="2.3" fill="#FFFFFF"/>
  <circle cx="39" cy="32" r="2.3" fill="#FFFFFF"/>
  <rect x="23" y="41" width="18" height="4" rx="2" fill="#1E3A8A"/>
</svg>
"""

st.set_page_config(page_title="Research Agent", page_icon="🔎", layout="centered")

# ----------------------------------------------------------------------------
# Custom CSS - intentionally minimal. Overall colors, fonts, and contrast
# come from .streamlit/config.toml (Streamlit's native theming, which
# correctly pairs text/background colors for both light and dark OS
# preferences). The rules below only style elements this app fully owns
# (the header banner, thinking-step lines, sources/confidence cards) and
# never touch Streamlit's own text-color rules, so there's nothing left
# for custom CSS to fight.
# ----------------------------------------------------------------------------
CUSTOM_CSS = """
<style>
/* ---------- Header banner (self-contained: white text on a blue
   gradient always has good contrast, so it needs no light/dark variant) ---------- */
.app-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  background: linear-gradient(135deg, #2563EB 0%, #1E3A8A 100%);
  border-radius: 1rem;
  padding: 1.4rem 1.6rem;
  box-shadow: 0 6px 20px rgba(37, 99, 235, 0.25);
  margin-bottom: 1.5rem;
}
.app-header-badge {
  flex-shrink: 0;
  width: 52px;
  height: 52px;
  border-radius: 14px;
  background: rgba(255,255,255,0.16);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.6rem;
  border: 1px solid rgba(255,255,255,0.28);
}
.app-title {
  color: #FFFFFF;
  font-size: 1.4rem;
  font-weight: 700;
  margin: 0;
}
.app-subtitle {
  color: #DCE8FB;
  font-size: 0.92rem;
  margin-top: 0.2rem;
  line-height: 1.4;
}

img[alt="user avatar"], img[alt="assistant avatar"] {
  border-radius: 50% !important;
}

/* ---------- Thinking steps: a tinted accent line. No explicit text
   color is set, so it inherits Streamlit's own (theme-correct) text
   color instead of guessing at one. ---------- */
.think-line {
  border-left: 3px solid #2563EB;
  background: rgba(37, 99, 235, 0.07);
  border-radius: 0 10px 10px 0;
  padding: 0.45rem 0.75rem;
  margin: 0.35rem 0;
  font-size: 0.92rem;
}
.think-line.think-search {
  border-left-color: #1E3A8A;
}
.think-line code {
  background: rgba(37, 99, 235, 0.14);
  padding: 0.05rem 0.4rem;
  border-radius: 6px;
}

/* ---------- Answer card: border only, no background/text override,
   so the answer text always matches Streamlit's active theme. ---------- */
div[class*="st-key-answer-card"] {
  border: 1px solid rgba(37, 99, 235, 0.18);
  border-radius: 1rem;
  padding: 1rem 1.2rem;
  margin-top: 0.4rem;
}

/* ---------- Sources: tinted card. Titles/links inherit theme text
   color; only the badge and link color are explicit self-contained
   pairs (blue background + white text), which stay readable
   regardless of light/dark mode. ---------- */
div[class*="st-key-sources-card"] {
  background: rgba(37, 99, 235, 0.05);
  border: 1px dashed rgba(37, 99, 235, 0.35);
  border-radius: 1rem;
  padding: 0.9rem 1.1rem;
  margin-top: 0.8rem;
}
.sources-heading {
  font-weight: 700;
  font-size: 0.95rem;
  margin-bottom: 0.5rem;
}
.source-list {
  list-style: none;
  margin: 0;
  padding: 0;
}
.source-row {
  display: flex;
  align-items: flex-start;
  gap: 0.6rem;
  padding: 0.35rem 0;
  border-top: 1px solid rgba(37, 99, 235, 0.14);
}
.source-row:first-child { border-top: none; }
.source-badge {
  flex-shrink: 0;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #2563EB;
  color: #FFFFFF;
  font-size: 0.72rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 0.1rem;
}
.source-body { display: flex; flex-direction: column; min-width: 0; }
.source-title { font-weight: 600; font-size: 0.9rem; }
.source-link {
  color: #2563EB;
  font-size: 0.78rem;
  text-decoration: none;
  word-break: break-all;
}
.source-link:hover { text-decoration: underline; }
.source-link--plain { opacity: 0.7; }

/* ---------- Confidence: pills are self-contained (solid color +
   white text), so they're readable in both themes without change. ---------- */
div[class*="st-key-confidence-row"] {
  margin-top: 0.8rem;
}
.confidence-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.3rem 0.85rem;
  border-radius: 999px;
  font-size: 0.82rem;
  font-weight: 700;
  color: #FFFFFF;
}
.confidence-pill.tier-high { background: #1E3A8A; }
.confidence-pill.tier-mid { background: #2563EB; }
.confidence-pill.tier-low { background: #64748B; }
.confidence-bar-track {
  height: 6px;
  border-radius: 999px;
  background: rgba(37, 99, 235, 0.15);
  margin-top: 0.5rem;
  overflow: hidden;
}
.confidence-bar-fill {
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, #60A5FA, #1E3A8A);
}
.confidence-reason {
  opacity: 0.75;
  font-size: 0.85rem;
  margin-top: 0.4rem;
  line-height: 1.4;
}

/*
 * stBottom is the sticky wrapper Streamlit pins to the viewport bottom
 * around the chat input. Its own background is transparent by default
 * (only the input pill inside it is opaque), so scrolled content shows
 * through the padding around the pill. This backs it with the same
 * backgroundColor as the active theme (light/dark) so nothing bleeds
 * through, and reserves matching space at the bottom of the page so the
 * last message is never tucked underneath it.
 */
[data-testid="stBottom"] {
  background: #FFFFFF;
  z-index: 999;
}
@media (prefers-color-scheme: dark) {
  [data-testid="stBottom"] { background: #0E1420; }
}
.block-container {
  padding-bottom: 180px;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

st.markdown(
    """
    <div class="app-header">
      <div class="app-header-badge">🔎</div>
      <div>
        <p class="app-title">Research Agent</p>
        <p class="app-subtitle">An AI agent that decides on its own when to search and when to answer.
        Ask follow-up questions — it remembers the conversation.</p>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []


def split_final_answer(final_answer: str):
    """Strip the appended Sources/Confidence blocks off the answer text
    so each piece can be styled separately. The confidence value/reason
    is only ever embedded in this text, so it's parsed out with a regex;
    sources are rendered from the structured list the agent already
    provides, not from this text.
    """
    main_text = re.split(r"\n\n\*\*Sources:\*\*\n", final_answer, maxsplit=1)[0]
    main_text = re.split(r"\n\n\*\*Confidence: \d+/10\*\* — ", main_text, maxsplit=1)[0]
    main_text = main_text.strip()

    confidence = None
    confidence_reason = ""
    match = re.search(r"\*\*Confidence: (\d+)/10\*\* — (.+?)\s*$", final_answer, re.S)
    if match:
        confidence = int(match.group(1))
        confidence_reason = match.group(2).strip()

    return main_text, confidence, confidence_reason


def render_sources(sources: list, key: str):
    if not sources:
        return

    rows = []
    for s in sources:
        title = html.escape(str(s.get("title", "")).strip() or "Untitled source")
        url = str(s.get("url", "")).strip()
        source_id = html.escape(str(s.get("id", "")))
        safe_url = html.escape(url, quote=True)

        if re.match(r"^https?://", url):
            link_html = (
                f'<a class="source-link" href="{safe_url}" '
                f'target="_blank" rel="noopener noreferrer">{safe_url}</a>'
            )
        else:
            link_html = f'<span class="source-link source-link--plain">{safe_url}</span>'

        rows.append(
            f'<li class="source-row">'
            f'<span class="source-badge">{source_id}</span>'
            f'<span class="source-body"><span class="source-title">{title}</span>{link_html}</span>'
            f"</li>"
        )

    with st.container(key=f"sources-card-{key}"):
        st.markdown(
            f'<div class="sources-heading">📚 Sources</div>'
            f'<ul class="source-list">{"".join(rows)}</ul>',
            unsafe_allow_html=True,
        )


def render_confidence(confidence, confidence_reason: str, key: str):
    if confidence is None:
        return

    if confidence >= 8:
        tier, label = "tier-high", "Strong confidence"
    elif confidence >= 5:
        tier, label = "tier-mid", "Moderate confidence"
    else:
        tier, label = "tier-low", "Low confidence"

    pct = max(0, min(100, confidence * 10))
    reason = html.escape(confidence_reason)

    with st.container(key=f"confidence-row-{key}"):
        st.markdown(
            f'<span class="confidence-pill {tier}">{label} — {confidence}/10</span>'
            f'<div class="confidence-bar-track"><div class="confidence-bar-fill" '
            f'style="width:{pct}%"></div></div>'
            + (f'<div class="confidence-reason">{reason}</div>' if reason else ""),
            unsafe_allow_html=True,
        )


def render_answer(final_answer: str, sources: list, key: str):
    main_text, confidence, confidence_reason = split_final_answer(final_answer)
    with st.container(key=f"answer-card-{key}"):
        st.markdown(main_text)
    render_sources(sources, key)
    render_confidence(confidence, confidence_reason, key)


# Show previous turns of the conversation
for i, turn in enumerate(st.session_state.chat_history):
    with st.chat_message("user", avatar=USER_AVATAR):
        st.write(turn["question"])
    with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
        render_answer(turn["answer"], turn.get("sources", []), key=f"hist-{i}")

question = st.chat_input("Ask a research question, or a follow-up...")

if question:
    with st.chat_message("user", avatar=USER_AVATAR):
        st.write(question)

    with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
        final_answer = ""
        sources = []

        with st.status("🧠 Agent is thinking...", expanded=True) as status:
            for step in run_agent(question, st.session_state.chat_history):
                for node_name, node_output in step.items():

                    if node_name == "planner":
                        action = node_output.get("next_action")
                        if action == "search":
                            query = html.escape(node_output.get("next_query", ""))
                            st.markdown(
                                f'<div class="think-line think-plan">🧭 Planning — decided to '
                                f'search for <code>{query}</code></div>',
                                unsafe_allow_html=True,
                            )
                        else:
                            st.markdown(
                                '<div class="think-line think-plan">🧭 Planning — enough info '
                                "gathered, drafting the answer</div>",
                                unsafe_allow_html=True,
                            )

                    elif node_name == "search":
                        last_query = html.escape(node_output["queries_used"][-1])
                        st.markdown(
                            f'<div class="think-line think-search">🔍 Searched '
                            f'<code>{last_query}</code></div>',
                            unsafe_allow_html=True,
                        )
                        with st.expander("View search result"):
                            st.text(node_output["search_history"][-1])

                    elif node_name == "answer":
                        final_answer = node_output["final_answer"]
                        sources = node_output.get("sources", [])

            status.update(label="✅ Research complete", state="complete", expanded=False)

        render_answer(final_answer, sources, key="live")

    # Save this turn to the session's memory, so future questions
    # can refer back to it.
    st.session_state.chat_history.append({
        "question": question,
        "answer": final_answer,
        "sources": sources,
    })
