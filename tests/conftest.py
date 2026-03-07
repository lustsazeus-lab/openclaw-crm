"""Pytest configuration and fixtures for openclaw-crm tests."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from openclaw_crm.sheets import SheetsBackend, SheetResult, set_backend


class MockBackend(SheetsBackend):
    """Mock Google Sheets backend for testing.
    
    Stores data in memory and simulates sheet operations.
    """

    def __init__(self):
        self._data: dict[str, list[list[str]]] = {}
        self._next_row: dict[str, int] = {}
        self._spreadsheet_id = "test_spreadsheet"

    def _key(self, spreadsheet_id: str, range_: str) -> str:
        return f"{spreadsheet_id}:{range_}"

    def read(self, spreadsheet_id: str, range_: str) -> SheetResult:
        key = self._key(spreadsheet_id, range_)
        if key in self._data:
            return SheetResult(success=True, data={"values": self._data[key]})
        return SheetResult(success=True, data={"values": []})

    def append(self, spreadsheet_id: str, range_: str, values: list[list[str]]) -> SheetResult:
        key = self._key(spreadsheet_id, range_)
        if key not in self._data:
            # Initialize with headers if empty
            self._data[key] = []
        self._data[key].extend(values)
        return SheetResult(success=True, data={})

    def update(self, spreadsheet_id: str, range_: str, values: list[list[str]]) -> SheetResult:
        key = self._key(spreadsheet_id, range_)
        # Simple update - just replace the row
        if key in self._data:
            # Parse range to get row number (e.g., "A2:U2" -> row 2)
            import re
            match = re.search(r'!A(\d+):', range_)
            if match:
                row_idx = int(match.group(1)) - 1  # 0-indexed
                if row_idx < len(self._data[key]):
                    self._data[key][row_idx] = values[0]
        return SheetResult(success=True, data={})

    def set_data(self, range_: str, rows: list[list[str]]) -> None:
        """Helper to set initial data for a range.
        
        Uses a fixed spreadsheet_id for simplicity in tests.
        """
        # Store with a default spreadsheet ID
        self._data[f"{self._spreadsheet_id}:{range_}"] = rows


# Global patchers that will be started/stopped by fixtures
_patcher_pipeline = patch("openclaw_crm.pipeline.get_spreadsheet_id", return_value="test_spreadsheet")
_patcher_network = patch("openclaw_crm.network.get_spreadsheet_id", return_value="test_spreadsheet")


@pytest.fixture
def mock_backend():
    """Provide a fresh MockBackend for each test."""
    # Start patches
    patcher_pipeline = patch("openclaw_crm.pipeline.get_spreadsheet_id", return_value="test_spreadsheet")
    patcher_network = patch("openclaw_crm.network.get_spreadsheet_id", return_value="test_spreadsheet")
    
    patcher_pipeline.start()
    patcher_network.start()
    
    backend = MockBackend()
    set_backend(backend)
    yield backend
    
    set_backend(None)
    patcher_pipeline.stop()
    patcher_network.stop()


@pytest.fixture
def mock_backend_with_pipeline(mock_backend: MockBackend) -> MockBackend:
    """Provide MockBackend with typical pipeline data."""
    headers = [
        "Client", "Contact", "Source", "Stage", "Budget", "Rate Type",
        "Service", "First Contact", "Last Contact", "Next Action",
        "Due Date", "Notes", "Slack Channel", "Proposal Link",
        "Owner", "Upwork URL", "Probability",
        "Referred By", "Network Parent", "Network Notes", "Signal Date",
    ]
    rows = [
        headers,
        ["Acme Corp", "John Doe", "upwork", "won", "$5000", "fixed", "Dev", "2026-01-01", "2026-03-01", "", "", "", "", "", "", "", "", "", "", "", ""],
        ["Beta Inc", "Jane Smith", "network", "lead", "$3000", "hourly", "Design", "2026-02-01", "2026-03-05", "", "", "", "", "", "", "", "", "Alice", "Alice", "Found in Slack", "2026-02-15"],
        ["Gamma LLC", "Bob Wilson", "referral", "negotiation", "$8000", "fixed", "Dev", "2026-01-15", "2026-03-07", "", "", "", "", "", "", "", "", "", "", "", ""],
    ]
    mock_backend.set_data("Pipeline!A:U", rows)
    return mock_backend


@pytest.fixture
def mock_backend_with_signals(mock_backend: MockBackend) -> MockBackend:
    """Provide MockBackend with network signals data."""
    headers = ["Timestamp", "Source Client", "Channel", "Signal Text", "Mentioned Company", "Status"]
    rows = [
        headers,
        ["2026-03-01T10:00:00", "Alice", "slack", "Great potential client", "NewCo", "new"],
        ["2026-03-02T11:00:00", "Bob", "twitter", "Looking for dev help", "TechStartup", "promoted"],
    ]
    mock_backend.set_data("'Network Signals'!A:F", rows)
    return mock_backend


@pytest.fixture
def mock_backend_with_clients(mock_backend: MockBackend) -> MockBackend:
    """Provide MockBackend with clients data."""
    headers = ["Client", "Contact", "Email", "Status", "", "", "", "", ""]
    rows = [
        headers,
        ["ExistingCorp", "John", "john@existing.com", "active", "", "", "", "", ""],
        ["PausedInc", "Jane", "jane@paused.com", "paused", "", "", "", "", ""],
    ]
    mock_backend.set_data("Clients!A:I", rows)
    return mock_backend
