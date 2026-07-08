from app.services.taxonomy_loader import load_taxonomy


def test_load_taxonomy() -> None:
    taxonomy = load_taxonomy()
    assert "快闪店" in taxonomy.space_type_names
    assert taxonomy.alias_to_space_type["popup store"] == "快闪店"
    assert taxonomy.alias_to_space_type["中庭"] == "购物中心中庭"
    assert "DP点" in taxonomy.point_names
