from orchestrator.state_machine import Opportunity


def test_from_discovery_api_maps_required_and_optional_fields():
    api_response = {
        "id": 42,
        "niche_title": "COBOL to Python translator",
        "niche_description": "Banks need this",
        "source": "github",
        "category": "devops",
        "status": "discovered",
        "confidence": 0.8,
    }
    opp = Opportunity.from_discovery_api(api_response)

    assert opp.source_id == "42"
    assert opp.niche_title == "COBOL to Python translator"
    assert opp.niche_description == "Banks need this"
    assert opp.source == "github"
    assert opp.category == "devops"


def test_from_discovery_api_defaults_missing_optional_fields():
    api_response = {"niche_title": "A niche", "source": "reddit"}
    opp = Opportunity.from_discovery_api(api_response)

    assert opp.source_id == ""
    assert opp.niche_description == ""
    assert opp.category == "other"
