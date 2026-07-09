from app.services.learning.alias_expansion import AliasExpansionService
from app.services.learning.feedback_reader import IntentCorrectionRecord


def test_propose_alias_after_threshold():
    service = AliasExpansionService(min_occurrences=3)
    corrections = [
        IntentCorrectionRecord("space_type", "商厦中庭", "购物中心中庭", 3),
        IntentCorrectionRecord("space_type", "商厦", "购物中心中庭", 1),
    ]
    proposals = service.propose(corrections)
    assert len(proposals) == 1
    assert proposals[0].alias == "商厦中庭"
    assert proposals[0].canonical == "购物中心中庭"
    assert proposals[0].occurrences == 3


def test_no_proposal_below_threshold():
    service = AliasExpansionService(min_occurrences=3)
    corrections = [
        IntentCorrectionRecord("space_type", "商厦", "购物中心中庭", 1),
    ]
    proposals = service.propose(corrections)
    assert len(proposals) == 0
