"""Airtable backend for openclaw-crm."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from openclaw_crm.sheets import SheetResult, SheetsBackend

# Column mapping: Airtable field name -> Pipeline column index
PIPELINE_FIELDS = [
    "Client",  # A
    "Contact",  # B
    "Source",  # C
    "Stage",  # D
    "Budget",  # E
    "Rate Type",  # F
    "Service",  # G
    "First Contact",  # H
    "Last Contact",  # I
    "Next Action",  # J
    "Due Date",  # K
    "Notes",  # L
    "Slack Channel",  # M
    "Proposal Link",  # N
    "Owner",  # O
    "Upwork URL",  # P
    "Probability",  # Q
    "Referred By",  # R
    "Network Parent",  # S
    "Network Notes",  # T
    "Signal Date",  # U
]

NETWORK_SIGNALS_FIELDS = [
    "Timestamp",  # A
    "Source Client",  # B
    "Channel",  # C
    "Signal Text",  # D
    "Mentioned Company",  # E
    "Status",  # F
]


class AirtableBackend(SheetsBackend):
    """Airtable backend implementing SheetsBackend interface."""

    def __init__(
        self,
        base_id: str | None = None,
        api_token: str | None = None,
        table_name: str = "Pipeline",
        network_table_name: str = "Network Signals",
    ):
        """Initialize Airtable backend.

        Args:
            base_id: Airtable base ID (or env var AIRTABLE_BASE_ID)
            api_token: Airtable API token (or env var AIRTABLE_API_TOKEN)
            table_name: Name of the Pipeline table
            network_table_name: Name of the Network Signals table
        """
        self.base_id = base_id or os.environ.get("AIRTABLE_BASE_ID")
        self.api_token = api_token or os.environ.get("AIRTABLE_API_TOKEN")
        self.table_name = table_name
        self.network_table_name = network_table_name

        if not self.base_id or not self.api_token:
            raise ValueError(
                "Airtable base_id and api_token are required. "
                "Pass as arguments or set AIRTABLE_BASE_ID and AIRTABLE_API_TOKEN env vars."
            )

        self._client: Any = None

    def _get_client(self) -> Any:
        """Lazy-load the pyairtable library."""
        if self._client is None:
            try:
                from pyairtable import Api

                self._client = Api(self.api_token)
            except ImportError:
                raise ImportError(
                    "pyairtable is required for Airtable backend. "
                    "Install with: pip install openclaw-crm[airtable]"
                )
        return self._client

    def _airtable_to_sheet_format(self, records: list[dict]) -> dict:
        """Convert Airtable records to sheet-like format."""
        values = []
        for record in records:
            fields = record.get("fields", {})
            row = []
            # Build row in the same column order as the sheet
            for field_name in PIPELINE_FIELDS:
                row.append(fields.get(field_name, ""))
            values.append(row)
        return {"values": values}

    def _sheet_to_airtable_format(self, values: list[list[str]]) -> list[dict]:
        """Convert sheet-like format to Airtable record format."""
        records = []
        for row in values:
            fields = {}
            for idx, value in enumerate(row):
                if idx < len(PIPELINE_FIELDS) and value:
                    fields[PIPELINE_FIELDS[idx]] = value
            if fields:
                records.append({"fields": fields})
        return records

    def read(self, spreadsheet_id: str, range_: str) -> SheetResult:
        """Read records from Airtable table.

        Args:
            spreadsheet_id: Used as base_id for Airtable
            range_: Table name (e.g., "Pipeline" or "Network Signals")
        """
        try:
            client = self._get_client()
            table = client.table(spreadsheet_id, range_)

            # Get all records (Airtable limits to 100 per page)
            records = table.all()

            # Convert to sheet-like format
            if range_ == "Network Signals":
                # Different field mapping for network signals
                values = []
                for record in records:
                    fields = record.get("fields", {})
                    row = [
                        fields.get("Timestamp", ""),
                        fields.get("Source Client", ""),
                        fields.get("Channel", ""),
                        fields.get("Signal Text", ""),
                        fields.get("Mentioned Company", ""),
                        fields.get("Status", ""),
                    ]
                    values.append(row)
                data = {"values": values}
            else:
                data = self._airtable_to_sheet_format(records)

            return SheetResult(success=True, data=data)
        except Exception as e:
            return SheetResult(success=False, data=None, error=str(e))

    def append(self, spreadsheet_id: str, range_: str, values: list[list[str]]) -> SheetResult:
        """Append records to Airtable table."""
        try:
            client = self._get_client()
            table = client.table(spreadsheet_id, range_)

            records = self._sheet_to_airtable_format(values)

            # Create records in batches
            created = table.create(records)

            return SheetResult(success=True, data={"created": len(created)})
        except Exception as e:
            return SheetResult(success=False, data=None, error=str(e))

    def update(self, spreadsheet_id: str, range_: str, values: list[list[str]]) -> SheetResult:
        """Update records in Airtable table.

        Note: Airtable requires record IDs for updates. This implementation
        uses the first column (Client name) to match existing records.
        """
        try:
            client = self._get_client()
            table = client.table(spreadsheet_id, range_)

            # Get existing records to find matching ones
            existing = table.all()
            existing_by_client = {r.get("fields", {}).get("Client", ""): r for r in existing}

            updated_count = 0
            for row in values:
                if not row:
                    continue
                client_name = row[0]
                if client_name in existing_by_client:
                    record_id = existing_by_client[client_name]["id"]
                    fields = {}
                    for idx, value in enumerate(row):
                        if idx < len(PIPELINE_FIELDS) and value:
                            fields[PIPELINE_FIELDS[idx]] = value
                    table.update(record_id, fields)
                    updated_count += 1

            return SheetResult(success=True, data={"updated": updated_count})
        except Exception as e:
            return SheetResult(success=False, data=None, error=str(e))
