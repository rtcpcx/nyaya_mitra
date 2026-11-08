from typing import Literal
from pydantic import BaseModel, Field

Category = Literal["criminal", "property", "rental", "consumer", "employment", "family", "contract", "civil", "constitutional", "tax", "cyber", "immigration", "administrative", "banking", "other", "unclear"]

class CaseIntake(BaseModel):
    short_summary: str = ""
    category: Category = "unclear"
    jurisdiction: str = "India (state/city to confirm)"
    parties: list[str] = Field(default_factory=list)
    facts: list[str] = Field(default_factory=list)
    timeline: list[str] = Field(default_factory=list)
    evidence_mentioned: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    disputed_or_unverified_points: list[str] = Field(default_factory=list)
    immediate_safety_or_deadline_concerns: list[str] = Field(default_factory=list)

class LawyerRecommendation(BaseModel):
    recommended: bool = True
    why: list[str] = Field(default_factory=list)
    urgency: Literal["routine", "prompt", "urgent"] = "prompt"

class AnalysisResponse(BaseModel):
    intake: CaseIntake = Field(default_factory=CaseIntake)
    plain_language_assessment: str = ""
    possible_options: list[str] = Field(default_factory=list)
    practical_next_steps: list[str] = Field(default_factory=list)
    questions_to_clarify: list[str] = Field(default_factory=list)
    lawyer_recommendation: LawyerRecommendation = Field(default_factory=LawyerRecommendation)
    source_notes: list[str] = Field(default_factory=list)
    draft: str = ""


class ConversationResponse(BaseModel):
    reply: str = Field(min_length=1, max_length=5000)
    next_question: str = Field(default="", max_length=1200)
    case_summary: str = Field(default="", max_length=1200)
    risk_level: Literal["routine", "prompt", "urgent"] = "routine"
    draft: str = Field(default="", max_length=6000)
