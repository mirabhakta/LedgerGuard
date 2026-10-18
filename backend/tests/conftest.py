from __future__ import annotations

from pathlib import Path

import pytest

from backend.app.data.loader import QuickBooksDatasetLoader
from backend.app.data.normalizer import QuickBooksNormalizer
from backend.app.data.store import NormalizedAccountingStore


@pytest.fixture(scope="session")
def dataset_root() -> Path:
    return Path(__file__).parents[2] / "data" / "raw" / "hackathon-100"


@pytest.fixture(scope="session")
def loader(dataset_root: Path) -> QuickBooksDatasetLoader:
    return QuickBooksDatasetLoader(dataset_root)


@pytest.fixture(scope="session")
def normalized_store(loader: QuickBooksDatasetLoader) -> NormalizedAccountingStore:
    return NormalizedAccountingStore(loader, QuickBooksNormalizer())

