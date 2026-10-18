"""Read-only loader for the sponsor-provided RWM v4 dataset."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import yaml

from backend.app.models.accounting import RawQuickBooksRecord, RecordType
from backend.app.models.errors import DatasetLoadError, SchemaDriftError

from .mappings import ENTITY_FILES, REQUIRED_FIELDS


class QuickBooksDatasetLoader:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        if not (self.root / "index.json").is_file():
            raise DatasetLoadError(f"missing dataset index: {self.root / 'index.json'}")
        self._index_rows = self._read_index()
        self._index_by_company = {row["company_id"]: row for row in self._index_rows}

    @property
    def company_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._index_by_company))

    def index_row(self, company_id: str) -> dict[str, Any]:
        try:
            return dict(self._index_by_company[company_id])
        except KeyError as exc:
            raise DatasetLoadError(f"unknown company_id: {company_id}") from exc

    def world_path(self, company_id: str) -> Path:
        self.index_row(company_id)
        matches = sorted((self.root / company_id / "rwm-v4").glob("world-*"))
        if len(matches) != 1 or not matches[0].is_dir():
            raise DatasetLoadError(
                f"expected one RWM world for {company_id}, found {len(matches)}"
            )
        return matches[0]

    def manifest(self, company_id: str) -> dict[str, Any]:
        document = self._load_yaml(self.world_path(company_id) / "manifest.yaml")
        if not isinstance(document, dict):
            raise DatasetLoadError(f"manifest for {company_id} must be an object")
        return document

    def load_entity(
        self, company_id: str, record_type: RecordType
    ) -> tuple[RawQuickBooksRecord, ...]:
        relative_file = ENTITY_FILES[record_type]
        world = self.world_path(company_id)
        path = world / relative_file
        document = self._load_yaml(path)
        if document is None:
            document = []
        if not isinstance(document, list):
            raise DatasetLoadError(f"{path} must contain a YAML record array")
        manifest = self.manifest(company_id)
        dataset_id = str(manifest.get("dataset_id", ""))
        if not dataset_id:
            raise SchemaDriftError(f"manifest for {company_id} has no dataset_id")

        records: list[RawQuickBooksRecord] = []
        for index, payload in enumerate(document):
            if not isinstance(payload, dict):
                raise DatasetLoadError(f"{path} row {index} must be an object")
            missing = REQUIRED_FIELDS[record_type] - payload.keys()
            if missing:
                raise SchemaDriftError(
                    f"{path} row {index} is missing required fields: {sorted(missing)}"
                )
            records.append(
                RawQuickBooksRecord(
                    company_id=company_id,
                    dataset_id=dataset_id,
                    record_type=record_type,
                    relative_path=str(path.relative_to(self.root)),
                    payload=payload,
                )
            )
        return tuple(records)

    def iter_entity(self, record_type: RecordType) -> Iterator[RawQuickBooksRecord]:
        for company_id in self.company_ids:
            yield from self.load_entity(company_id, record_type)

    def _read_index(self) -> list[dict[str, Any]]:
        try:
            value = json.loads((self.root / "index.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise DatasetLoadError(f"cannot read dataset index: {exc}") from exc
        if not isinstance(value, list):
            raise DatasetLoadError("dataset index must be a JSON array")
        for index, row in enumerate(value):
            if (
                not isinstance(row, dict)
                or not isinstance(row.get("company_id"), str)
                or not row["company_id"].strip()
            ):
                raise DatasetLoadError(f"invalid index row {index}")
        company_ids = [row["company_id"] for row in value]
        if len(company_ids) != len(set(company_ids)):
            raise DatasetLoadError("dataset index contains duplicate company_id values")
        return value

    @staticmethod
    def _load_yaml(path: Path) -> Any:
        if not path.is_file():
            raise DatasetLoadError(f"missing dataset file: {path}")
        try:
            return yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise DatasetLoadError(f"cannot read YAML {path}: {exc}") from exc

