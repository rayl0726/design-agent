import tempfile
from pathlib import Path

import yaml

from app.services.learning.alias_expansion import AliasProposal
from app.services.learning.taxonomy_writer import TaxonomyWriter


def test_apply_alias_to_taxonomy():
    source = """
space_types:
  - name: "购物中心中庭"
    aliases: ["商场中庭"]
"""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "intent_taxonomy.yaml"
        path.write_text(source, encoding="utf-8")
        writer = TaxonomyWriter(path)
        writer.apply_alias(AliasProposal("space_type", "商厦中庭", "购物中心中庭", 3, 0.9))
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert "商厦中庭" in data["space_types"][0]["aliases"]
