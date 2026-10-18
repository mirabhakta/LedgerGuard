from __future__ import annotations

from pathlib import Path

import pytest

from backend.app.data.loader import QuickBooksDatasetLoader
from backend.app.models.accounting import RecordType
from backend.app.models.errors import DatasetLoadError, SchemaDriftError


def test_discovers_all_real_companies(loader: QuickBooksDatasetLoader) -> None:
    assert len(loader.company_ids) == 100
    assert loader.company_ids[0] == "company-001"
    assert loader.company_ids[-1] == "company-100"


def test_loads_real_entity_counts_and_empty_files(loader: QuickBooksDatasetLoader) -> None:
    assert len(loader.load_entity("company-001", RecordType.BILL)) == 359
    assert len(loader.load_entity("company-001", RecordType.BANK_TRANSACTION)) == 3606
    assert loader.load_entity("company-073", RecordType.INVOICE) == ()
    assert loader.load_entity("company-001", RecordType.PROJECT) == ()


def test_missing_index_is_a_typed_error(tmp_path: Path) -> None:
    with pytest.raises(DatasetLoadError, match="missing dataset index"):
        QuickBooksDatasetLoader(tmp_path)


def test_missing_required_source_field_is_schema_drift(tmp_path: Path) -> None:
    (tmp_path / "index.json").write_text('[{"company_id":"company-001"}]')
    world = tmp_path / "company-001" / "rwm-v4" / "world-test"
    world.mkdir(parents=True)
    (world / "manifest.yaml").write_text("schema_version: '4'\ndataset_id: world-test\ncurrency: USD\n")
    (world / "bills.yaml").write_text("- id: bill-1\n  total_amount: '1.00'\n")
    loader = QuickBooksDatasetLoader(tmp_path)
    with pytest.raises(SchemaDriftError, match="missing required fields"):
        loader.load_entity("company-001", RecordType.BILL)


def test_malformed_yaml_is_a_typed_error(tmp_path: Path) -> None:
    (tmp_path / "index.json").write_text('[{"company_id":"company-001"}]')
    world = tmp_path / "company-001" / "rwm-v4" / "world-test"
    world.mkdir(parents=True)
    (world / "manifest.yaml").write_text("schema_version: '4'\ndataset_id: world-test\ncurrency: USD\n")
    (world / "bills.yaml").write_text("- id: [unterminated")
    loader = QuickBooksDatasetLoader(tmp_path)
    with pytest.raises(DatasetLoadError, match="cannot read YAML"):
        loader.load_entity("company-001", RecordType.BILL)


def test_duplicate_or_blank_company_ids_are_rejected(tmp_path: Path) -> None:
    index = tmp_path / "index.json"
    index.write_text(
        '[{"company_id":"company-001"},{"company_id":"company-001"}]',
        encoding="utf-8",
    )
    with pytest.raises(DatasetLoadError, match="duplicate company_id"):
        QuickBooksDatasetLoader(tmp_path)
    index.write_text('[{"company_id":"  "}]', encoding="utf-8")
    with pytest.raises(DatasetLoadError, match="invalid index row"):
        QuickBooksDatasetLoader(tmp_path)

