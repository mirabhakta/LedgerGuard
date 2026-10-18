from backend.app.data.loader import QuickBooksDatasetLoader
from backend.app.data.schema_inspector import DatasetSchemaInspector


def test_inspects_real_company_and_matches_index(loader: QuickBooksDatasetLoader) -> None:
    result = DatasetSchemaInspector(loader).inspect_company("company-001")
    assert result.schema_version == "4"
    assert result.currency == "USD"
    assert result.actual_counts["bill"] == 359
    assert result.actual_counts["invoice"] == 1574

