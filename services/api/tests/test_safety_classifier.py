import pytest

from app.safety import classifier

EMERGENCY_CASES = [
    "I can't breathe and my lips are turning blue",
    "My father just passed out and is unresponsive",
    "I have crushing chest pain radiating to my arm",
    "Her throat is closing and her face is swelling, I think it's anaphylaxis",
    "He is bleeding heavily and it won't stop",
    "Her face is drooping and she can't speak suddenly, is this a stroke",
    "I want to kill myself",
]

URGENT_CASES = [
    "My fever has been 104 for two days and it's getting worse",
    "I have hives and a rash that keeps spreading",
]

NORMAL_CASES = [
    "What is paracetamol used for?",
    "What are common side effects of ibuprofen?",
    "Explain what hypertension means in simple words",
    "I have a mild headache, what could help?",
]

POLICY_CASES = [
    ("Should I double my dose of ibuprofen?", "dosage_change_request"),
    ("Can you prescribe me antibiotics?", "prescription_only_request"),
    ("Is this safe during pregnancy?", "pregnancy"),
    ("What can I give my toddler for a cold?", "children"),
    ("I'm allergic to penicillin, what should I know?", "allergy_mentioned"),
    ("Does ibuprofen interact with my blood thinner?", "drug_interaction"),
    ("Do I have diabetes based on these symptoms?", "diagnosis_request"),
]


@pytest.mark.parametrize("text", EMERGENCY_CASES)
def test_emergency_detection(text: str) -> None:
    assessment = classifier.classify(text)
    assert assessment.level == classifier.LEVEL_EMERGENCY, f"expected emergency for: {text}"


@pytest.mark.parametrize("text", URGENT_CASES)
def test_urgent_detection(text: str) -> None:
    assessment = classifier.classify(text)
    assert assessment.level == classifier.LEVEL_URGENT, f"expected urgent for: {text}"


@pytest.mark.parametrize("text", NORMAL_CASES)
def test_normal_requests_are_not_flagged(text: str) -> None:
    """False-positive regression: everyday health questions must not trigger
    urgent/emergency states, or the safety UI would bury normal chat under
    constant false alarms."""
    assessment = classifier.classify(text)
    assert assessment.level == classifier.LEVEL_NORMAL, f"unexpected escalation for: {text}"


@pytest.mark.parametrize("text,expected_flag", POLICY_CASES)
def test_policy_flags_detected_independent_of_level(text: str, expected_flag: str) -> None:
    assessment = classifier.classify(text)
    assert expected_flag in assessment.policy_flags
