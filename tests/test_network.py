"""Tests for network.py (spider network referral tracking)."""
from __future__ import annotations

import pytest

from openclaw_crm.network import (
    add_signal,
    promote_signal,
    dismiss_signal,
    get_network_tree,
    get_network_value,
    check_competitor_guard,
    SIGNALS_RANGE,
    PIPELINE_RANGE,
)


class TestAddSignal:
    """Tests for add_signal function."""

    def test_add_signal_basic(self, mock_backend):
        """Test adding a basic signal."""
        signal = {
            "timestamp": "2026-03-09T10:00:00",
            "source_client": "Alice",
            "channel": "slack",
            "signal_text": "Great lead",
            "mentioned_company": "NewCo",
        }
        result = add_signal(signal)
        assert result["ok"] is True
        assert result["status"] == "new"

    def test_add_signal_defaults(self, mock_backend):
        """Test adding signal with defaults."""
        result = add_signal({})
        assert result["ok"] is True
        assert result["status"] == "new"


class TestPromoteSignal:
    """Tests for promote_signal function."""

    def test_promote_signal_atomic(self, mock_backend_with_signals, mock_backend_with_pipeline):
        """Test atomic promote: deal created before signal marked as promoted."""
        # Promote the first signal (row 2 in sheet, index 1 in data)
        result = promote_signal(2, {"budget": "$5000"})
        
        assert result["ok"] is True
        assert result["signal_row"] == 2
        
        # Verify signal was marked as promoted in signals sheet
        # This happens after deal creation (atomic)
        backend = mock_backend_with_signals
        signals_data = backend._data.get(f"test_spreadsheet:{SIGNALS_RANGE}")
        # Row 2 should have "promoted" status
        signal_row = signals_data[1] if signals_data else []
        status_idx = 5  # Status is at index 5
        assert signal_row[status_idx] == "promoted"
        
        # Verify deal was created in pipeline
        pipeline_data = backend._data.get(f"test_spreadsheet:{PIPELINE_RANGE}")
        # Should have 5 rows now (1 header + 4 original + 1 new = but wait, fixture had 3 data rows)
        # Fixture: 1 header + 3 data = 4, + 1 new deal = 5
        assert len(pipeline_data) == 5

    def test_promote_signal_reject_already_promoted(self, mock_backend_with_signals, mock_backend_with_pipeline):
        """Test re-promote guard: reject if signal already promoted."""
        # Try to promote the second signal which is already "promoted"
        result = promote_signal(3)
        
        assert result["ok"] is False
        assert "already promoted" in result["error"]

    def test_promote_signal_out_of_range(self, mock_backend_with_signals):
        """Test promote with out of range row."""
        result = promote_signal(100)
        
        assert result["ok"] is False
        assert "out of range" in result["error"]


class TestDismissSignal:
    """Tests for dismiss_signal function."""

    def test_dismiss_signal(self, mock_backend_with_signals):
        """Test dismissing a signal."""
        result = dismiss_signal(2)
        
        assert result["ok"] is True
        
        # Verify signal was marked as dismissed
        backend = mock_backend_with_signals
        signals_data = backend._data.get(f"test_spreadsheet:{SIGNALS_RANGE}")
        signal_row = signals_data[1]
        assert signal_row[5] == "dismissed"

    def test_dismiss_signal_out_of_range(self, mock_backend_with_signals):
        """Test dismiss with out of range row."""
        result = dismiss_signal(100)
        
        assert result["ok"] is False
        assert "out of range" in result["error"]


class TestGetNetworkTree:
    """Tests for get_network_tree function."""

    def test_get_network_tree_full(self, mock_backend_with_pipeline):
        """Test getting full network tree."""
        tree = get_network_tree()
        
        assert "Alice" in tree
        assert len(tree["Alice"]) == 1
        assert tree["Alice"][0]["client"] == "Beta Inc"

    def test_get_network_tree_filtered(self, mock_backend_with_pipeline):
        """Test getting network tree for specific root."""
        tree = get_network_tree(root="Alice")
        
        assert "Alice" in tree
        assert len(tree["Alice"]) == 1

    def test_get_network_tree_empty(self, mock_backend):
        """Test network tree with no data."""
        tree = get_network_tree()
        
        assert tree == {}


class TestGetNetworkValue:
    """Tests for get_network_value function."""

    def test_get_network_value_direct_only(self, mock_backend_with_pipeline):
        """Test getting network value for direct client."""
        result = get_network_value("Acme Corp")
        
        assert result["client"] == "Acme Corp"
        assert result["direct_value"] == 5000
        assert result["network_value"] == 0
        assert result["total"] == 5000

    def test_get_network_value_with_network(self, mock_backend_with_pipeline):
        """Test getting network value including referrals."""
        result = get_network_value("Alice")
        
        assert result["client"] == "Alice"
        assert result["direct_value"] == 0
        assert result["network_value"] == 3000  # Beta Inc referred by Alice
        assert result["total"] == 3000


class TestCheckCompetitorGuard:
    """Tests for check_competitor_guard function."""

    def test_check_competitor_guard_new_company(self, mock_backend_with_pipeline, mock_backend_with_clients):
        """Test competitor guard allows new company."""
        # NewCo is not in pipeline or clients
        result = check_competitor_guard("NewCo", "Alice")
        
        assert result is True

    def test_check_competitor_guard_existing_in_pipeline(self, mock_backend_with_pipeline, mock_backend_with_clients):
        """Test competitor guard blocks company in Pipeline (won/negotiation/proposal)."""
        # Acme Corp is in pipeline with "won" stage
        result = check_competitor_guard("Acme Corp", "Alice")
        
        assert result is False

    def test_check_competitor_guard_existing_in_clients(self, mock_backend_with_pipeline, mock_backend_with_clients):
        """Test competitor guard blocks company in Clients tab (active/paused)."""
        # ExistingCorp is in clients with "active" status
        result = check_competitor_guard("ExistingCorp", "Alice")
        
        assert result is False

    def test_check_competitor_guard_case_insensitive(self, mock_backend_with_pipeline, mock_backend_with_clients):
        """Test competitor guard is case insensitive."""
        result = check_competitor_guard("ACME CORP", "Alice")
        
        assert result is False
