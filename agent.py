import os
import json
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from dotenv import load_dotenv

from tools import web_search_structured

load_dotenv()

MAX_SEARCH_STEPS = 4


class AgentState(TypedDict):
    question: str
    conversation_context: str
    search_history: List[str]
    queries_used: List[str]
    next_action: str
    next_query: str
    final_answer: str
    sources: List[dict]


def get_llm():
    return ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0.2,
        api_key=os.environ.get("GROQ_API_KEY"),
    )


def is_duplicate_query(new_query: str, previous_queries: list, threshold: float = 0.6) -> bool:
    new_words = set(new_query.lower().split())

    for prev_query in previous_queries:
        prev_words = set(prev_query.lower().split())

        if not new_words or not prev_words:
            continue

        overlap = new_words.intersection(prev_words)
        union = new_words.union(prev_words)
        similarity = len(overlap) / len(union)

        if similarity >= threshold:
            return True

    return False


def planner_node(state: AgentState) -> AgentState:
    llm = get_llm()

    history_text = "\n\n".join(state["search_history"]) if state["search_history"] else "(no searches done yet)"
    queries_text = ", ".join(state["queries_used"]) if state["queries_used"] else "(none)"
    context_text = state["conversation_context"] if state["conversation_context"] else "(this is the first question, no prior conversation)"

    if len(state["queries_used"]) >= MAX_SEARCH_STEPS:
        state["next_action"] = "answer"
        return state

    prompt = f"""You are a research agent. 

Prior conversation with this user (for context - the current question
may be a follow-up that refers back to this):
{context_text}

The user's CURRENT question is: "{state['question']}"

Queries searched so far for this question: {queries_text}

Information gathered so far for this question:
{history_text}

Decide: do you have enough information to give a complete, accurate
answer to the current question? If YES, respond "answer".
If NO, respond "search" and provide one specific new search query that
would fill in the missing information (must be different from previous queries).
If the current question refers back to the prior conversation (e.g. "what about solar?"
following an earlier question about energy targets), make sure your search query
includes that context (e.g. "Pakistan solar energy" not just "solar").

STRICT: Reply ONLY in this JSON format, nothing else:
{{"action": "search" or "answer", "query": "the search query if action is search, else empty string"}}
"""

    response = llm.invoke(prompt)
    raw = response.content.strip()

    try:
        start = raw.index("{")
        end = raw.rindex("}") + 1
        parsed = json.loads(raw[start:end])
    except (ValueError, json.JSONDecodeError):
        parsed = {"action": "answer", "query": ""}

    action = parsed.get("action", "answer")
    query = parsed.get("query", "")

    if action == "search" and is_duplicate_query(query, state["queries_used"]):
        action = "answer"
        query = ""

    state["next_action"] = action
    state["next_query"] = query
    return state


def search_node(state: AgentState) -> AgentState:
    query = state["next_query"]
    results = web_search_structured(query)

    # Build a quick lookup of URL -> existing ID, so we can detect
    # duplicates across different searches (not just within one search).
    url_to_id = {s["url"]: s["id"] for s in state["sources"]}

    formatted_chunks = []
    for r in results:
        url = r["url"]

        if url in url_to_id:
            # We've already seen this source in a previous search -
            # reuse its existing ID instead of creating a duplicate.
            source_id = url_to_id[url]
        else:
            source_id = len(state["sources"]) + 1
            state["sources"].append({
                "id": source_id,
                "title": r["title"],
                "url": url,
            })
            url_to_id[url] = source_id  # remember it for the rest of this loop too

        formatted_chunks.append(
            f"[{source_id}] Title: {r['title']}\nSnippet: {r['snippet']}"
        )

    result_text = "\n\n".join(formatted_chunks) if formatted_chunks else "No good results found."

    state["search_history"].append(f"Query: {query}\nResults:\n{result_text}")
    state["queries_used"].append(query)
    return state


def answer_node(state: AgentState) -> AgentState:
    llm = get_llm()

    history_text = "\n\n".join(state["search_history"]) if state["search_history"] else "(no research done)"
    context_text = state["conversation_context"] if state["conversation_context"] else "(this is the first question)"

    prompt = f"""Prior conversation with this user:
{context_text}

The user's CURRENT question was: "{state['question']}"

Based on the research below, write a clear, well-organized, accurate answer
to the current question. If the current question is a follow-up, make sure
your answer connects naturally to the prior conversation.

CITATION FORMAT: Each piece of research is labeled with a number in
brackets, like [1] or [2]. When you use information from a source,
cite it using that same number in brackets right after the claim -
for example: "Pakistan aims for 60% renewable energy by 2030 [3]."
Do NOT write out full URLs in your answer - just use the [number] format.

IMPORTANT: If different sources give conflicting numbers or facts (e.g. different
percentages, different dates, or different figures for the same thing), do NOT
silently pick one. Instead, explicitly mention the disagreement - state what each
source says (with their [number] citations) and note that the figures vary.

NOTE: Before calling something a "contradiction," check if it might
just be a change over time (e.g. a value from an earlier date vs a
later date from the same or different source). If two numbers are
clearly tracking growth/change over time rather than disagreeing about
the same point in time, describe it as a trend, not a conflict.

DO NOT perform your own math or estimates by combining numbers from
different sources (e.g. do not add percentages together to invent a
new figure). Only report numbers exactly as they appear in the research.
If the research doesn't directly answer part of the question, say so
honestly instead of calculating an estimate.

If the information is incomplete, say so honestly.

Also rate your confidence in this answer from 1-10, based on:
- How directly the research answers the question
- How consistent the sources are with each other
- Whether anything important seems missing

Research collected:
{history_text}

STRICT: Reply ONLY in this JSON format, nothing else. The "answer" field
should contain the full answer text (with [number] citations inside it):
{{"answer": "your full answer text here", "confidence": 7, "confidence_reason": "one short sentence explaining the score"}}
"""

    response = llm.invoke(prompt)
    raw = response.content.strip()

    try:
        start = raw.index("{")
        end = raw.rindex("}") + 1
        parsed = json.loads(raw[start:end])
    except (ValueError, json.JSONDecodeError):
        parsed = {
            "answer": raw,
            "confidence": None,
            "confidence_reason": "",
        }

    answer_text = parsed.get("answer", "")
    confidence = parsed.get("confidence")
    confidence_reason = parsed.get("confidence_reason", "")

    if state["sources"]:
        sources_list = "\n".join(
            f"[{s['id']}] {s['title']} — {s['url']}" for s in state["sources"]
        )
        answer_text += f"\n\n**Sources:**\n{sources_list}"

    if confidence is not None:
        answer_text += f"\n\n**Confidence: {confidence}/10** — {confidence_reason}"

    state["final_answer"] = answer_text
    return state


def route_after_planner(state: AgentState) -> str:
    if state["next_action"] == "search":
        return "search"
    return "answer"


def build_agent():
    graph = StateGraph(AgentState)

    graph.add_node("planner", planner_node)
    graph.add_node("search", search_node)
    graph.add_node("answer", answer_node)

    graph.set_entry_point("planner")

    graph.add_conditional_edges(
        "planner",
        route_after_planner,
        {"search": "search", "answer": "answer"},
    )

    graph.add_edge("search", "planner")
    graph.add_edge("answer", END)

    return graph.compile()


def run_agent(question: str, conversation_history: list = None):
    """
    conversation_history: a list of dicts like
        [{"question": "...", "answer": "..."}, ...]
    representing prior turns in this session. Pass None or [] for a
    fresh conversation with no prior context.
    """
    app = build_agent()

    if conversation_history:
        # Turn the history into a readable text block for the prompts.
        # We only keep the last 3 turns to keep the prompt from growing
        # too large - older context matters less for follow-ups anyway.
        recent_turns = conversation_history[-3:]
        context_text = "\n\n".join(
            f"Q: {turn['question']}\nA: {turn['answer']}" for turn in recent_turns
        )
    else:
        context_text = ""

    initial_state: AgentState = {
        "question": question,
        "conversation_context": context_text,
        "search_history": [],
        "queries_used": [],
        "next_action": "",
        "next_query": "",
        "final_answer": "",
        "sources": [],
    }

    for step in app.stream(initial_state):
        yield step