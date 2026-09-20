from scripts.ingest_real_sources import _clean_label_text, _select_sections, _strip_dosing_sentences


def test_strips_otc_leading_label() -> None:
    text = _clean_label_text("Uses temporarily relieves minor aches and pains.")
    assert text == "temporarily relieves minor aches and pains."


def test_strips_numbered_spl_section_header() -> None:
    text = _clean_label_text("6 ADVERSE REACTIONS The following are discussed in more detail.")
    assert text == "The following are discussed in more detail."


def test_strips_leaked_dosing_frequency_sentence() -> None:
    """Regression: a real amoxicillin label's information_for_patients field
    included 'Advise patients that amoxicillin tablets may be taken every 8
    hours or every 12 hours, depending on the dose prescribed.' inside an
    otherwise-fine counseling paragraph. MediRAG must never surface a
    specific dosing frequency, even as quoted evidence (see SAFETY.md)."""
    text = (
        "Counsel patients that amoxicillin is a penicillin class drug. "
        "Advise patients that amoxicillin tablets may be taken every 8 hours or every 12 hours. "
        "Tell patients to complete the full course of therapy."
    )
    cleaned = _strip_dosing_sentences(text)
    assert "every 8 hours" not in cleaned
    assert "penicillin class drug" in cleaned
    assert "complete the full course" in cleaned


def test_otc_label_uses_combined_warnings_field_only() -> None:
    """An OTC 'Drug Facts' warnings field already contains the do-not-use/
    stop-use content as one paragraph -- also including those fields
    individually duplicated the same sentences under the same heading."""
    label = {
        "warnings": ["Warnings: Liver warning: severe damage may occur. Stop use and ask a doctor if symptoms worsen."],
        "do_not_use": ["Do not use with other acetaminophen products."],
        "stop_use": ["Stop use and ask a doctor if symptoms worsen."],
    }
    sections = _select_sections(label)
    assert sections["Warnings"].count("Stop use and ask a doctor if symptoms worsen") == 1
    assert "Do not use with other acetaminophen products" not in sections["Warnings"]


def test_rx_label_without_combined_warnings_falls_back_to_granular_fields() -> None:
    label = {
        "contraindications": ["Contraindicated in patients with known hypersensitivity."],
        "warnings_and_cautions": ["Anaphylactic reactions have been reported."],
    }
    sections = _select_sections(label)
    assert "hypersensitivity" in sections["Warnings"]
    assert "Anaphylactic reactions" in sections["Warnings"]


def test_select_sections_skips_dosage_fields_entirely() -> None:
    label = {
        "indications_and_usage": ["Used to treat infections."],
        "dosage_and_administration": ["Take 500 mg every 8 hours."],
    }
    sections = _select_sections(label)
    assert "dosage_and_administration" not in sections
    assert not any("500 mg" in text for text in sections.values())
