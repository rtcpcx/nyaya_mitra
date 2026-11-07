from src.schemas import LawyerRecommendation

URGENT_TERMS = [
    "immediate danger", "threatened to kill", "threat to kill", "physical violence",
    "being assaulted", "abduction", "suicide threat", "medical emergency",
    "currently detained", "in police custody", "arrested", "lockup",
    "imminent eviction with force", "forced out tonight", "child is missing",
    "rape", "sexual assault", "stalking outside my home"
]
PROMPT_TERMS = [
    "fir", "police notice", "summons", "court notice", "court date", "hearing",
    "charge sheet", "chargesheet", "arrest warrant", "bail", "limitation",
    "deadline", "appeal deadline", "divorce", "child custody", "domestic violence",
    "sexual harassment", "property title", "land dispute", "termination",
    "unpaid wages", "tax notice", "immigration", "eviction notice", "legal notice",
    "consumer forum", "bank freeze", "account frozen", "cheque bounce"
]

def triage_text(text: str) -> dict:
    q = (text or "").casefold()
    urgent = [term for term in URGENT_TERMS if term in q]
    prompt = [term for term in PROMPT_TERMS if term in q]
    if urgent:
        return {
            "level": "urgent", "lawyer_recommended": True,
            "reasons": ["Possible immediate safety, liberty or physical-risk indicators were detected: " + ", ".join(urgent)],
            "immediate_steps": [
                "Prioritise personal safety; move to a safer place if possible.",
                "If anyone is in immediate danger, contact local emergency services now.",
                "Contact a qualified local advocate and a trusted support person promptly.",
                "Preserve original messages, call logs, medical records, photographs and notices without altering them."
            ],
            "emergency_guidance": "Do not wait for an AI response if anyone is in immediate danger."
        }
    if prompt:
        return {
            "level": "prompt", "lawyer_recommended": True,
            "reasons": ["Potential deadline, police/court process or consequential legal issue detected: " + ", ".join(prompt)],
            "immediate_steps": [
                "Do not ignore notices, summons, court papers or official communications.",
                "Record the date and method of receipt and preserve the complete document/envelope/email.",
                "Ask an advocate in the relevant jurisdiction to check deadlines and the documents promptly.",
                "Avoid signing admissions, settlements or waivers until you understand their effect."
            ],
            "emergency_guidance": "If a hearing or deadline is near, arrange legal advice immediately."
        }
    return {
        "level": "routine", "lawyer_recommended": False,
        "reasons": ["No explicit emergency/deadline keyword was detected. This simple rule-based check can miss risk and does not prove the matter is low-risk."],
        "immediate_steps": [
            "Keep original documents and make dated copies of relevant messages and receipts.",
            "Write a factual timeline while events are fresh.",
            "Confirm the relevant state/city, dates and any notice deadlines.",
            "Consult an advocate before consequential action or sending a formal legal notice."
        ],
        "emergency_guidance": "If there is a threat, hidden deadline, police/court process or major impact, seek legal help promptly."
    }
