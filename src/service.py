from src.config import DATABASE_PATH, TOP_K
from src.database import search_sources
from src.llm import generate_json, generate_conversation_json
from src.schemas import AnalysisResponse, ConversationResponse
from src.triage import triage_text
import re
from time import perf_counter

DRAFT_REQUEST_RE = re.compile(
    r"\b(?:draft|write|prepare|compose)\b.{0,100}\b(?:legal notice|notice|complaint|reply|response|application|affidavit|letter|agreement|petition|representation)\b"
    r"|\b(?:legal notice|notice|complaint|reply|response|application|affidavit|letter|agreement|petition|representation)\b.{0,100}\b(?:draft|write|prepare|compose)\b",
    re.IGNORECASE | re.DOTALL,
)
DRAFT_NEGATION_RE = re.compile(r"\b(?:do not|don't|dont|no need to|not)\s+(?:draft|write|prepare|compose)\b", re.IGNORECASE)

STATE_NAMES = ["andhra pradesh", "arunachal pradesh", "assam", "bihar", "chhattisgarh", "goa", "gujarat", "haryana", "himachal pradesh", "jharkhand", "karnataka", "kerala", "madhya pradesh", "maharashtra", "manipur", "meghalaya", "mizoram", "nagaland", "odisha", "punjab", "rajasthan", "sikkim", "tamil nadu", "telangana", "tripura", "uttar pradesh", "uttarakhand", "west bengal", "delhi", "jammu and kashmir", "ladakh", "puducherry", "chandigarh"]

def _state_hint(location: str) -> str | None:
    normalized = (location or "").casefold().replace("&", "and")
    for state in STATE_NAMES:
        if re.search(r"(?<![a-z])" + re.escape(state) + r"(?![a-z])", normalized):
            return state
    return None


DRAFT_ACCEPT_RE = re.compile(
    r"^\s*(?:yes|yeah|yep|sure|please|go ahead|do it|draft it|prepare it|write it|that would be great|okay)\b",
    re.IGNORECASE,
)
DRAFT_OFFER_RE = re.compile(r"\b(?:draft|prepare|write|compose)\b", re.IGNORECASE)


def _draft_was_explicitly_requested(problem: str, history: list[dict] | None = None) -> bool:
    """Accept an explicit request or a clear yes to the assistant's recent draft offer."""
    message = problem or ""
    if DRAFT_NEGATION_RE.search(message):
        return False
    if DRAFT_REQUEST_RE.search(message):
        return True
    if not DRAFT_ACCEPT_RE.search(message):
        return False
    recent_history = list(history or [])
    # The Streamlit caller includes the current user message in history.
    # Remove it so the previous assistant's offer can be recognised.
    if recent_history and recent_history[-1].get("role") == "user":
        if str(recent_history[-1].get("content") or "").strip() == message.strip():
            recent_history = recent_history[:-1]
    for item in reversed(recent_history):
        if item.get("role") == "assistant":
            offered = str(item.get("content") or "")
            return bool(DRAFT_OFFER_RE.search(offered))
        if item.get("role") == "user":
            break
    return False


def _reconcile_lawyer_recommendation(validated: dict, triage: dict) -> None:
    """Prevent model output from downgrading first-pass urgent/prompt flags."""
    recommendation = validated.setdefault("lawyer_recommendation", {})
    rank = {"routine": 0, "prompt": 1, "urgent": 2}
    triage_level = triage.get("level", "routine")
    model_level = recommendation.get("urgency", "routine")
    if rank.get(triage_level, 0) > rank.get(model_level, 0):
        recommendation["urgency"] = triage_level
    if triage.get("lawyer_recommended") and not recommendation.get("recommended", False):
        recommendation["recommended"] = True
        recommendation.setdefault("why", []).append(
            "The first-pass safety triage flagged this matter for advocate review."
        )
    recommendation["why"] = list(dict.fromkeys(recommendation.get("why", [])))


def analyze_problem(problem: str, state_city: str = "", language: str = "English") -> dict:
    if not problem or not problem.strip(): raise ValueError("Please describe what happened.")
    triage=triage_text(problem)
    state_hint = _state_hint(state_city)
    sources=search_sources(problem, DATABASE_PATH, TOP_K, state_hint, national_only=not bool(state_hint), strict_relevance=True)
    draft_requested = _draft_was_explicitly_requested(problem)
    payload={
        "task":"Structure the user's legal problem and provide cautious, plain-language legal information.",
        "user_story":problem,
        "state_or_city":state_city.strip() or "Not supplied; do not assume a state. Ask the user to confirm.",
        "response_language":language,
        "retrieved_sources":sources,
        "triage_rules_result":triage,
        "required_output_schema":{
            "intake":{"short_summary":"string","category":"criminal/property/rental/consumer/employment/family/contract/civil/constitutional/tax/cyber/immigration/administrative/banking/other/unclear","jurisdiction":"string","parties":["string"],"facts":["string"],"timeline":["string"],"evidence_mentioned":["string"],"missing_information":["string"],"disputed_or_unverified_points":["string"],"immediate_safety_or_deadline_concerns":["string"]},
            "plain_language_assessment":"string","possible_options":["string"],"practical_next_steps":["string"],"questions_to_clarify":["string"],
            "lawyer_recommendation":{"recommended":"boolean","why":["string"],"urgency":"routine/prompt/urgent"},
            "source_notes":["For each legal proposition cite retrieved source title, section/article, jurisdiction, status/year and URL; otherwise say not verified."],
            "draft":"optional factual draft; no invented facts or legal citations"
        },
        "additional_rules":[
            "Retrieved passages may be stale, incomplete or noisy. Mention uncertainty and verify current official text.",
            "Do not cite any source not present in retrieved_sources.",
            "Do not infer jurisdiction from the database records; use the user's location and facts.",
            "If no retrieved sources, do not state specific law, section, case, limitation period or deadline as fact.",
            "Do not infer facts not stated. Label user claims as assertions, not proven facts.",
            "Only provide a draft when the user explicitly asks to draft, write, prepare or compose a named legal document; otherwise return an empty draft string.",
            "Never add unprovided facts about rent, payments, utilities, agreement clauses, promises, dates or communications.",
            "Never request or include full bank account/card numbers, passwords, OTPs or unnecessary sensitive identifiers. Use a safe placeholder if needed.",
            "A requested draft must contain only user-supplied facts, clearly marked placeholders, no unsupported legal citations, and an advocate-review warning.",
            "If state/city is missing or unclear, do not use state-specific laws; ask the user to confirm location."
        ]
    }
    raw=generate_json(payload)
    validated=AnalysisResponse.model_validate(raw).model_dump()
    _reconcile_lawyer_recommendation(validated, triage)
    if not draft_requested:
        validated["draft"] = ""
    validated["triage"]=triage
    validated["retrieved_sources"]=sources
    validated["source_mode"]="retrieved" if sources else "no_sources_retrieved"
    validated["database_note"]="Dataset retrieval is not confirmation that a provision is current or applicable. Check the linked official text and relevant Gazette/notifications."
    return validated


def analyze_without_llm(problem: str, state_city: str = "") -> dict:
    """A safe local-only fallback for intake/triage while no LLM key is configured."""
    if not problem or not problem.strip(): raise ValueError("Please describe what happened.")
    triage=triage_text(problem)
    state_hint = _state_hint(state_city)
    sources=search_sources(problem,DATABASE_PATH,TOP_K,state_hint,national_only=not bool(state_hint),strict_relevance=True)
    return {"triage":triage,"retrieved_sources":sources,"source_mode":"retrieved" if sources else "no_sources_retrieved",
            "notice":"AI analysis is not enabled until an LLM API key is configured. The source search and rule-based triage are available.",
            "database_note":"Retrieved records are research leads, not a legal conclusion. Verify official current text."}



def _first_question(text: str) -> str:
    """Keep at most one complete question from model output."""
    if not text:
        return ""
    match = re.search(r"[^?]*\?", text, flags=re.DOTALL)
    if match:
        return match.group(0).strip()
    candidate = re.split(r"[.!]", text.strip(), maxsplit=1)[0].strip()
    return candidate + "?" if candidate else ""


def _remove_questions(text: str) -> str:
    """Keep the conversational reply declarative; the follow-up lives separately."""
    if not text:
        return ""
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return " ".join(part for part in parts if "?" not in part).strip()


def respond_to_turn(
    user_message: str,
    history: list[dict] | None = None,
    state_city: str = "",
    language: str = "English",
) -> dict:
    """Handle one conversational turn and return compact user output plus diagnostics."""
    if not user_message or not user_message.strip():
        raise ValueError("Please enter a message.")

    started = perf_counter()
    prior_summary = ""
    for item in reversed(history or []):
        metadata = item.get("metadata") if isinstance(item, dict) else None
        if item.get("role") == "assistant" and isinstance(metadata, dict) and metadata.get("case_summary"):
            prior_summary = str(metadata["case_summary"])[:2200]
            break
    turns = [
        {"role": item.get("role"), "content": str(item.get("content") or "")[:1600]}
        for item in (history or [])
        if item.get("role") in {"user", "assistant"} and item.get("content")
    ][-20:]
    if turns and turns[-1]["role"] == "user" and turns[-1]["content"].strip() == user_message.strip():
        turns = turns[:-1]
    # Preserve the user's own statements separately from assistant prose.
    # This helps prevent repeat questions and retains facts beyond the last few turns.
    user_statements = [
        str(item.get("content") or "").strip()[:1600]
        for item in (history or [])
        if isinstance(item, dict) and item.get("role") == "user" and item.get("content")
    ]
    if not user_statements or user_statements[-1] != user_message.strip():
        user_statements.append(user_message.strip()[:1600])
    user_statements = user_statements[-20:]
    user_context = " ".join(user_statements)
    retrieval_query = user_context[-9000:]
    case_text = (retrieval_query or user_message).strip()
    triage = triage_text(case_text)
    # A location stated in the conversation counts even if the sidebar field is blank.
    state_hint = _state_hint(state_city) or _state_hint(user_context) or _state_hint(prior_summary)
    resolved_location = state_city.strip() or (state_hint.title() if state_hint else "Not confirmed; do not assume a state.")

    retrieval_started = perf_counter()
    sources = search_sources(
        retrieval_query or user_message,
        DATABASE_PATH,
        min(max(TOP_K, 6), 12),
        state_hint,
        national_only=not bool(state_hint),
        strict_relevance=True,
    )
    retrieval_ms = round((perf_counter() - retrieval_started) * 1000, 2)

    payload = {
        "user_message": user_message,
        "recent_conversation": turns,
        "previous_case_summary": prior_summary,
        "location": resolved_location,
        "user_statements_so_far": user_statements,
        "response_language": language,
        "relevant_legal_passages": [
            {
                "title": source.get("title"),
                "section": source.get("section"),
                "text": (source.get("text") or "")[:1800],
                "jurisdiction": source.get("jurisdiction"),
                "status": source.get("status"),
                "year": source.get("year"),
                "source_type": source.get("source_type"),
                "source_url": source.get("source_url"),
                "legal_subject": source.get("legal_subject"),
            }
            for source in sources[:3]
        ],
        "first_pass_safety_triage": triage,
        "output_contract": {
            "reply": "empathetic, fact-specific and substantive. Answer the user's actual question first. During intake use 2-5 useful sentences; when enough facts exist provide a structured explanation in several paragraphs.",
            "next_question": "at most 2-3 focused questions that materially affect the next step; compare against every user statement and never repeat a question already answered; empty when enough is known or user asked a direct question that can be answered now",
            "case_summary": "cumulative factual ledger from all user statements; retain amount, payment method, location, parties, allegation/reason, dates, agreement terms, evidence, contact attempts, address, desired outcome and unresolved facts; label claims; do not silently drop earlier facts",
            "risk_level": "routine, prompt, or urgent",
        },
    }

    generation_started = perf_counter()
    model_output = generate_conversation_json(payload)
    generation_ms = round((perf_counter() - generation_started) * 1000, 2)
    parsed = ConversationResponse.model_validate(model_output).model_dump()
    draft = parsed.get("draft", "") if _draft_was_explicitly_requested(user_message, history) else ""

    # Preserve a small grouped set of intake questions; reducing this to the
    # first question discarded useful context-gathering prompts.
    question = (parsed.get("next_question", "") or "").strip()[:1200]
    reply = _remove_questions(parsed.get("reply", "")).strip()
    if not reply:
        reply = "I can help you work through this carefully."
    if not sources and not question:
        caveat = "I couldn't verify a sufficiently relevant legal provision in the local index, so I won't guess at the specific law."
        if caveat.casefold() not in reply.casefold():
            reply = f"{reply} {caveat}"

    rank = {"routine": 0, "prompt": 1, "urgent": 2}
    risk_level = parsed.get("risk_level", "routine")
    if rank.get(triage.get("level", "routine"), 0) > rank.get(risk_level, 0):
        risk_level = triage["level"]

    return {
        "reply": reply,
        "next_question": question,
        "case_summary": parsed.get("case_summary", ""),
        "draft": draft,
        "risk_level": risk_level,
        "triage": triage,
        "retrieved_sources": sources,
        "source_mode": "relevant_sources_retrieved" if sources else "no_relevant_sources",
        "timings_ms": {
            "retrieval": retrieval_ms,
            "generation": generation_ms,
            "total": round((perf_counter() - started) * 1000, 2),
        },
        "database_note": "Local retrieval is a research aid, not confirmation that a provision is current, commenced or applicable. Verify official text and relevant notifications.",
        "model_output": model_output,
    }


def respond_without_llm(
    user_message: str,
    history: list[dict] | None = None,
    state_city: str = "",
) -> dict:
    """Safe, transparent chat fallback when no model key is configured."""
    if not user_message or not user_message.strip():
        raise ValueError("Please enter a message.")
    started = perf_counter()
    triage = triage_text(user_message)
    state_hint = _state_hint(state_city)
    retrieval_started = perf_counter()
    sources = search_sources(
        user_message, DATABASE_PATH, min(max(TOP_K, 8), 20), state_hint,
        national_only=not bool(state_hint), strict_relevance=True,
    )
    retrieval_ms = round((perf_counter() - retrieval_started) * 1000, 2)
    return {
        "reply": "I can help you organise the facts and identify what needs checking. AI-generated legal explanations are currently disabled because no LLM API key is configured.",
        "next_question": "What happened most recently?",
        "case_summary": user_message[:500],
        "draft": "",
        "risk_level": triage["level"],
        "triage": triage,
        "retrieved_sources": sources,
        "source_mode": "relevant_sources_retrieved" if sources else "no_relevant_sources",
        "timings_ms": {
            "retrieval": retrieval_ms,
            "generation": 0.0,
            "total": round((perf_counter() - started) * 1000, 2),
        },
        "database_note": "Local retrieval is a research aid, not confirmation that a provision is current, commenced or applicable.",
        "notice": "Configure an LLM_API_KEY to enable conversational AI analysis.",
        "model_output": None,
    }
