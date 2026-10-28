"""
Comprehensive test suite for Krabs Against Security (K.A.S.) cards, schemas, and art manifest.
Validates 100% of cards against JSON schemas, MITRE ATT&CK formatting, d20 checks, and uniqueness constraints.
"""

import json
import os
import re
import pytest
from jsonschema import Draft7Validator

try:
    from referencing import Registry, Resource
    HAS_REFERENCING = True
except ImportError:
    from jsonschema import RefResolver
    HAS_REFERENCING = False

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMAS_DIR = os.path.join(BASE_DIR, "schemas")
CARDS_FILE = os.path.join(BASE_DIR, "cards", "core-v1", "cards.json")
ART_FILE = os.path.join(BASE_DIR, "art", "art_manifest.json")

CARD_SCHEMA_FILE = os.path.join(SCHEMAS_DIR, "card-schema-v1.json")
DECK_SCHEMA_FILE = os.path.join(SCHEMAS_DIR, "deck-schema-v1.json")
ART_SCHEMA_FILE = os.path.join(SCHEMAS_DIR, "art-manifest-v1.schema.json")


@pytest.fixture(scope="module")
def card_schema():
    with open(CARD_SCHEMA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def deck_schema():
    with open(DECK_SCHEMA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def art_schema():
    with open(ART_SCHEMA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def deck_data():
    with open(CARDS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def art_manifest_data():
    with open(ART_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def test_schema_validity(card_schema, deck_schema, art_schema):
    """Ensure all JSON schemas are self-validating Draft-07 schemas."""
    Draft7Validator.check_schema(card_schema)
    Draft7Validator.check_schema(deck_schema)
    Draft7Validator.check_schema(art_schema)


def test_card_count_and_distribution(deck_data):
    """Verify exact 80 cards and expected deck distributions."""
    cards = deck_data["cards"]
    assert len(cards) == 80, f"Expected 80 cards, got {len(cards)}"

    counts = {
        "initial_compromise": 0,
        "pivot_escalate": 0,
        "persistence": 0,
        "c2_exfil": 0,
        "procedures": 0,
        "injects": 0,
    }

    for c in cards:
        deck = c["deck"]
        assert deck in counts, f"Unexpected deck: {deck}"
        counts[deck] += 1

    assert counts["initial_compromise"] == 12, "Must have exactly 12 Initial Compromise cards"
    assert counts["pivot_escalate"] == 12, "Must have exactly 12 Pivot & Escalate cards"
    assert counts["persistence"] == 12, "Must have exactly 12 Persistence cards"
    assert counts["c2_exfil"] == 12, "Must have exactly 12 C2 & Exfil cards"
    assert counts["procedures"] == 16, "Must have exactly 16 Procedure cards"
    assert counts["injects"] == 16, "Must have exactly 16 Inject cards"


def test_deck_schema_validation(deck_schema, card_schema, deck_data):
    """Validate full deck collection against deck-schema-v1.json with local card-schema resolution."""
    if HAS_REFERENCING:
        card_resource = Resource.from_contents(card_schema)
        registry = Registry().with_resource(
            "https://krabs.ketron.dev/schemas/card-schema-v1.json",
            card_resource
        ).with_resource(
            "card-schema-v1.json",
            card_resource
        )
        validator = Draft7Validator(deck_schema, registry=registry)
    else:
        store = {
            "card-schema-v1.json": card_schema,
            "https://krabs.ketron.dev/schemas/card-schema-v1.json": card_schema,
            card_schema.get("$id", ""): card_schema,
        }
        resolver = RefResolver(
            base_uri="https://krabs.ketron.dev/schemas/",
            referrer=deck_schema,
            store=store
        )
        validator = Draft7Validator(deck_schema, resolver=resolver)

    errors = list(validator.iter_errors(deck_data))
    if errors:
        error_msgs = "\n".join(f"{e.json_path}: {e.message}" for e in errors)
        pytest.fail(f"Deck schema validation failed:\n{error_msgs}")


def test_individual_card_schema_validation(card_schema, deck_data):
    """Validate each of the 80 cards individually against card-schema-v1.json."""
    validator = Draft7Validator(card_schema)
    for card in deck_data["cards"]:
        errors = list(validator.iter_errors(card))
        assert not errors, f"Card {card.get('id', 'unknown')} failed schema:\n" + "\n".join(
            e.message for e in errors
        )


def test_art_manifest_schema_validation(art_schema, art_manifest_data):
    """Validate art manifest against art-manifest-v1.schema.json."""
    validator = Draft7Validator(art_schema)
    errors = list(validator.iter_errors(art_manifest_data))
    if errors:
        error_msgs = "\n".join(f"{e.json_path}: {e.message}" for e in errors)
        pytest.fail(f"Art manifest schema validation failed:\n{error_msgs}")


def test_unique_ids_and_slugs(deck_data):
    """Ensure no duplicate IDs or slugs exist across all cards."""
    ids = [c["id"] for c in deck_data["cards"]]
    slugs = [c["slug"] for c in deck_data["cards"]]
    art_ids = [c["art_id"] for c in deck_data["cards"]]

    assert len(ids) == len(set(ids)), f"Duplicate card IDs detected: {[x for x in ids if ids.count(x) > 1]}"
    assert len(slugs) == len(set(slugs)), f"Duplicate slugs detected: {[x for x in slugs if slugs.count(x) > 1]}"
    assert len(art_ids) == len(set(art_ids)), f"Duplicate art_ids detected: {[x for x in art_ids if art_ids.count(x) > 1]}"


def test_d20_thresholds_for_procedures(deck_data):
    """Verify that all procedures have valid d20 thresholds between 10 and 18."""
    for card in deck_data["cards"]:
        if card["deck"] == "procedures":
            assert "d20_threshold" in card, f"Procedure {card['id']} missing d20_threshold"
            threshold = card["d20_threshold"]
            assert isinstance(threshold, int), f"Procedure {card['id']} d20_threshold is not an int"
            assert 10 <= threshold <= 18, f"Procedure {card['id']} threshold {threshold} outside 10-18 range"
            assert "procedure_category" in card, f"Procedure {card['id']} missing procedure_category"
        else:
            assert "d20_threshold" not in card, f"Non-procedure {card['id']} should not have d20_threshold"


def test_mitre_attack_ids_for_attack_cards(deck_data):
    """Verify that all 48 attack cards have valid MITRE ATT&CK technique IDs."""
    attack_decks = {"initial_compromise", "pivot_escalate", "persistence", "c2_exfil"}
    attack_id_regex = re.compile(r"^T1[0-9]{3}(\.[0-9]{3})?$")

    for card in deck_data["cards"]:
        if card["deck"] in attack_decks:
            assert "attack_technique_id" in card, f"Attack card {card['id']} missing attack_technique_id"
            tech_id = card["attack_technique_id"]
            assert attack_id_regex.match(tech_id), f"Invalid ATT&CK ID format '{tech_id}' in {card['id']}"
            assert "attack_technique_name" in card, f"Attack card {card['id']} missing technique name"
            assert len(card["attack_technique_name"]) > 3
        else:
            assert "attack_technique_id" not in card, f"Non-attack card {card['id']} should not have ATT&CK ID"


def test_nist_phases(deck_data):
    """Verify all cards have valid NIST SP 800-61r2 phases."""
    valid_phases = {
        "Preparation",
        "Detection & Analysis",
        "Containment, Eradication & Recovery",
        "Post-Incident Activity",
    }
    for card in deck_data["cards"]:
        phase = card.get("nist_phase")
        assert phase in valid_phases, f"Card {card['id']} has invalid NIST phase: {phase}"


def test_art_manifest_synchronization(deck_data, art_manifest_data):
    """Ensure complete 1-to-1 mapping between canonical cards and art manifest entries."""
    card_ids = {c["id"] for c in deck_data["cards"]}
    art_card_ids = {a["card_id"] for a in art_manifest_data["cards"]}

    assert card_ids == art_card_ids, f"Mismatch between cards.json and art_manifest.json: {card_ids ^ art_card_ids}"
    assert len(art_manifest_data["cards"]) == 80

    for entry in art_manifest_data["cards"]:
        assert entry["art_status"] in ("approved", "deferred"), f"Art entry {entry['card_id']} status is not approved or deferred"
        assert entry["aspect_ratio"] == "4:3", f"Art entry {entry['card_id']} aspect ratio is not 4:3"
        assert isinstance(entry["seed"], int), f"Art entry {entry['card_id']} seed must be an int"
        assert len(entry["prompt"]) >= 20, f"Art entry {entry['card_id']} prompt too brief"
        assert entry["asset_path"].startswith("assets/cards/"), f"Invalid asset path in {entry['card_id']}"
        assert entry["print_asset_path"].startswith("assets/cards/print/"), f"Invalid print path in {entry['card_id']}"


def test_scenarios_integrity(deck_data):
    """Verify that scenario packs correctly reference valid card IDs."""
    card_lookup = {c["id"]: c for c in deck_data["cards"]}

    scenarios = deck_data.get("scenarios", [])
    assert len(scenarios) >= 3, "Expected at least 3 curated scenarios"

    for scn in scenarios:
        assert scn["id"].startswith("SCN-")
        sc = scn["scenario_cards"]
        assert sc["initial_compromise"] in card_lookup
        assert card_lookup[sc["initial_compromise"]]["deck"] == "initial_compromise"

        assert sc["pivot_escalate"] in card_lookup
        assert card_lookup[sc["pivot_escalate"]]["deck"] == "pivot_escalate"

        assert sc["persistence"] in card_lookup
        assert card_lookup[sc["persistence"]]["deck"] == "persistence"

        assert sc["c2_exfil"] in card_lookup
        assert card_lookup[sc["c2_exfil"]]["deck"] == "c2_exfil"

        for inj_id in scn.get("recommended_injects", []):
            assert inj_id in card_lookup
            assert card_lookup[inj_id]["deck"] == "injects"


if __name__ == "__main__":
    pytest.main(["-v", __file__])
