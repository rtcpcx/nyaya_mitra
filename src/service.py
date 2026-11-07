from src.config import DATABASE_PATH, TOP_K
from src.database import search_sources
from src.llm import generate_json
from src.schemas import AnalysisResponse
from src.triage import triage_text
import re

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


def _draft_was_explicitly_requested(problem: str) -> bool:
    return bool(DRAFT_REQUEST_RE.search(problem or "")) and not bool(DRAFT_NEGATION_RE.search(problem or ""))


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
    sources=search_sources(problem, DATABASE_PATH, TOP_K, state_hint, national_only=not bool(state_hint))
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
    """A safe local-only fallback for intake/triage while no Groq key is configured."""
    if not problem or not problem.strip(): raise ValueError("Please describe what happened.")
    triage=triage_text(problem)
    state_hint = _state_hint(state_city)
    sources=search_sources(problem,DATABASE_PATH,TOP_K,state_hint,national_only=not bool(state_hint))
    return {"triage":triage,"retrieved_sources":sources,"source_mode":"retrieved" if sources else "no_sources_retrieved",
            "notice":"AI analysis is not enabled until an LLM API key is configured. The source search and rule-based triage are available.",
            "database_note":"Retrieved records are research leads, not a legal conclusion. Verify official current text."}
