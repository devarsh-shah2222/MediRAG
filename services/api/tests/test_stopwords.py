from app.providers.stopwords import tokenize, tokenize_counts


def test_paracetamol_and_acetaminophen_tokenize_identically() -> None:
    """Regression: real FDA labels never say 'paracetamol' (only
    'acetaminophen'), so a query using the international name couldn't match
    the actual Uses/Warnings content, only a short document-level synonym
    note -- which then wrongly outranked the real content it was written to
    make findable in the first place. Canonicalizing both names to one token
    fixes matching at the root instead of chasing it chunk by chunk."""
    assert tokenize("What is paracetamol used for?") == tokenize("What is acetaminophen used for?")


def test_synonym_canonicalization_preserves_term_frequency() -> None:
    counts = tokenize_counts("Paracetamol relieves pain. Acetaminophen also reduces fever.")
    assert counts["acetaminophen"] == 2
    assert "paracetamol" not in counts


def test_indian_brand_names_canonicalize_to_generic_names() -> None:
    """Verified-real Indian brand names (see DECISIONS.md) must resolve to
    the same token as the generic name the actual ingested FDA content uses,
    the same mechanism as the paracetamol/acetaminophen case."""
    brand_to_generic = {
        "crocin": "acetaminophen",
        "dolo": "acetaminophen",
        "calpol": "acetaminophen",
        "brufen": "ibuprofen",
        "novamox": "amoxicillin",
        "glycomet": "metformin",
        "amlong": "amlodipine",
        "amlopres": "amlodipine",
        "azithral": "azithromycin",
        "alerid": "cetirizine",
    }
    for brand, generic in brand_to_generic.items():
        assert tokenize(f"What is {brand} used for?") == tokenize(f"What is {generic} used for?"), brand
