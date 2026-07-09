from app.agents.input_parser import PhotoParser, ReferenceParser


def test_photo_parser_normalizes_space_type() -> None:
    parser = PhotoParser()
    assert parser._normalize_vlm_value("popup store", "space_type") == "快闪店"
    assert parser._normalize_vlm_value("快闪店", "space_type") == "快闪店"


def test_reference_parser_normalizes_style_and_material() -> None:
    parser = ReferenceParser()
    assert parser._normalize_vlm_value("中国风", "style") == "国潮"
    assert parser._normalize_vlm_value("acrylic", "material") == "亚克力"
