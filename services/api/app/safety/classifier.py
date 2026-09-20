import re
from dataclasses import dataclass, field

LEVEL_NORMAL = "normal"
LEVEL_URGENT = "urgent"
LEVEL_EMERGENCY = "emergency"

# ponytail: keyword/regex rule sets instead of a trained classifier model.
# Auditable, deterministic, zero-latency, and testable with plain
# input->expected-category pairs (see tests/test_safety_classifier.py).
# Upgrade trigger: false-negative rate on the eval suite is unacceptable for
# a pattern-based approach -> add a model-based second opinion layer on top,
# never replace this layer (defense in depth, section 8 of the spec).
_EMERGENCY_PATTERNS: dict[str, list[str]] = {
    "severe_breathing_difficulty": [
        r"can'?t breathe", r"cannot breathe", r"struggling to breathe",
        r"gasping for air", r"lips? (are |is )?(turning )?blue", r"choking and can'?t",
    ],
    "loss_of_consciousness": [
        r"passed out", r"lost consciousness", r"unconscious", r"unresponsive",
        r"fainted and (is )?not waking",
    ],
    "severe_chest_symptoms": [
        r"crushing chest pain", r"severe chest pain", r"chest pain.*(arm|jaw|can'?t breathe)",
        r"heart attack",
    ],
    "severe_allergic_reaction": [
        r"anaphylax", r"throat (is )?closing", r"swelling of (the )?(face|throat|tongue)",
        r"severe allergic reaction",
    ],
    "uncontrolled_bleeding": [
        r"bleeding (heavily|severely).{0,20}(won'?t|does not|doesn'?t) stop",
        r"won'?t stop bleeding", r"severe bleeding",
    ],
    "severe_neurological": [
        r"face (is )?drooping", r"can'?t speak (suddenly|properly)\b", r"slurred speech suddenly",
        r"sudden numbness", r"stroke symptoms", r"seizure (right now|happening now)",
    ],
    "severe_confusion": [r"suddenly (very )?confused", r"severe confusion", r"can'?t recognize"],
    "self_harm_crisis": [
        r"kill myself", r"suicid", r"end my life", r"want to die", r"harm myself",
    ],
}

_URGENT_PATTERNS: dict[str, list[str]] = {
    "worsening_symptoms": [r"getting worse", r"worsening", r"won'?t go away for days"],
    "persistent_high_fever": [r"fever (of |over )?(10[3-9]|1[1-9]\d)", r"high fever for (days|\d+ days)"],
    "moderate_allergic_reaction": [r"allergic reaction", r"hives and", r"rash and swelling"],
}

# Independent of triage level -- these adjust HOW the assistant should answer,
# handled per section 9's high-risk categories regardless of urgency.
_POLICY_PATTERNS: dict[str, list[str]] = {
    "dosage_change_request": [
        r"(double|increase|decrease|lower|stop|skip) (my |the )?(dose|dosage)",
        r"stop taking (my |the )?(medicine|medication|pill)",
        r"can i take (extra|more|less)",
    ],
    "prescription_only_request": [r"prescribe me", r"write me a prescription", r"get me (a |the )?prescription"],
    "pregnancy": [r"pregnan", r"breastfeed"],
    "children": [r"my (baby|toddler|infant|child|kid)", r"for a \d{1,2} year old"],
    "allergy_mentioned": [r"i'?m allergic to", r"allergic to"],
    "drug_interaction": [r"interact with", r"take .* (with|and) .* together", r"mix .* with"],
    "diagnosis_request": [r"do i have", r"diagnose me", r"what disease do i have"],
    "certainty_seeking": [r"are you (100% )?sure", r"guarantee", r"definitely (cures|treats)"],
}


@dataclass
class SafetyAssessment:
    level: str
    urgency_categories: list[str] = field(default_factory=list)
    policy_flags: list[str] = field(default_factory=list)


def _matches_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(p, text) for p in patterns)


def classify(text: str) -> SafetyAssessment:
    lowered = text.lower()

    emergency_hits = [cat for cat, patterns in _EMERGENCY_PATTERNS.items() if _matches_any(lowered, patterns)]
    urgent_hits = [cat for cat, patterns in _URGENT_PATTERNS.items() if _matches_any(lowered, patterns)]
    policy_hits = [cat for cat, patterns in _POLICY_PATTERNS.items() if _matches_any(lowered, patterns)]

    if emergency_hits:
        return SafetyAssessment(level=LEVEL_EMERGENCY, urgency_categories=emergency_hits, policy_flags=policy_hits)
    if urgent_hits:
        return SafetyAssessment(level=LEVEL_URGENT, urgency_categories=urgent_hits, policy_flags=policy_hits)
    return SafetyAssessment(level=LEVEL_NORMAL, urgency_categories=[], policy_flags=policy_hits)
