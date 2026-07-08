from app.services.intent_recognition_result import (
    FieldSource,
    RecognizedField,
    IntentRecognitionResult,
)


def test_recognized_field_defaults():
    field = RecognizedField(name="space_type", value="快闪店")
    assert field.source == FieldSource.UNKNOWN
    assert field.confidence == 0.0
    assert not field.is_confident()


def test_result_can_dump():
    result = IntentRecognitionResult(
        space_type=RecognizedField(name="space_type", value="快闪店", source=FieldSource.EXACT, confidence=1.0)
    )
    data = result.to_dict()
    assert data["space_type"]["value"] == "快闪店"
