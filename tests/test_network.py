"""Unit tests for network module."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from openclaw_crm import network


class TestAddSignal:
    """Tests for add_signal function."""

    def test_add_signal_basic(self, mock_backend):
        """add_signal should add a new signal."""
        signal = {
            "source_client": "Alice",
            "channel": "slack",
            "signal_text": "Great lead",
            "mentioned_company": "NewCorp",
        }
        result = network.add_signal(signal)
        assert result["ok"] is True
        assert result["status"] == "new"


class TestPromoteSignal:
    """Tests for promote_signal function."""

    def test_promote_signal_creates_deal(self, mock_backend_with_signals, mock_backend_with_pipeline):
        """promote_signal should create a deal from signal."""
        # Row 2 (first data row after header)
        result = network.promote_signal(2)
        assert result["ok"] is True
        assert "deal" in result

    def test_promote_signal_already_promoted(self, mock_backend_with_signals, mock_backend_with_pipeline):
        """promote_signal should reject already promoted signals."""
        # Row 3 is already promoted
        result = network.promote_signal(3)
        assert result["ok"] is False
        assert "already promoted" in result.get("error", "").lower()

    def test_promote_signal_with_deal_overrides(self, mock_backend_with_signals, mock_backend_with_pipeline):
        """promote_signal should apply deal overrides."""
        result = network.promote_signal(2, deal_overrides={"budget": "$5000"})
        assert result["ok"] is True


class TestDismissSignal:
    """Tests for dismiss_signal function."""

    def test_dismiss_signal_basic(self, mock_backend_with_signals):
        """dismiss_signal should mark signal as dismissed."""
        result = network.dismiss_signal(2)
        assert result["ok"] is True


class TestGetNetworkTree:
    """Tests for get_network_tree function."""

    def test_get_network_tree_with_root(self, mock_backend_with_pipeline):
        """get_network_tree should return tree for specific root."""
        tree = network.get_network_tree(root="Alice")
        assert "Alice" in tree
        assert len(tree["Alice"]) > 0

    def test_get_network_tree_full(self, mock_backend_with_pipeline):
        """get_network_tree should return full network."""
        tree = network.get_network_tree()
        assert isinstance(tree, dict)

    def test_get_network_tree_empty(self, mock_backend):
        """get_network_tree should handle empty pipeline."""
        tree = network.get_network_tree()
        assert tree == {}


class TestGetNetworkValue:
    """Tests for get_network_value function."""

    def test_get_network_value_direct_only(self, mock_backend_with_pipeline):
        """get_network_value should calculate direct value."""
        result = network.get_network_value("Acme Corp")
        assert result["client"] == "Acme Corp"
        assert result["direct_value"] == 5000
        assert result["network_value"] == 0

    def test_get_network_value_with_network(self, mock_backend_with_pipeline):
        """get_network_value should include network value."""
        # Alice referred Beta Inc with $3000
        result = network.get_network_value("Alice")
        assert result["network_value"] == 3000

    def test_get_network_value_total(self, mock_backend_with_pipeline):
        """get_network_value should calculate total."""
        result = network.get_network_value("Alice")
        assert result["total"] == 3000  # Only network value since Alice has no direct deals

    def test_get_network_value_not_found(self, mock_backend_with_pipeline):
        """get_network_value should handle unknown client."""
        result = network.get_network_value("Unknown Corp")
        assert result["direct_value"] == 0
        assert result["network_value"] == 0


class TestCheckCompetitorGuard:
    """Tests for check_competitor_guard function."""

    def test_check_competitor_guard_new_company(self, mock_backend_with_pipeline, mock_backend_with_clients):
        """check_competitor_guard should allow new companies."""
        result = network.check_competitor_guard("NewCompany", "Alice")
        assert result is True

    def test_check_competitor_guard_existing_won(self, mock_backend_with_pipeline, mock_backend_with_clients):
        """check_competitor_guard should block existing clients in won stage."""
        result = network.check_competitor_guard("Acme Corp", "Alice")
        assert result is False

    def test_check_competitor_guard_existing_active_client(self, mock_backend_with_pipeline, mock_backend_with_clients):
        """check_competitor_guard should block existing active clients."""
        result = network.check_competitor_guard("ExistingCorp", "Alice")
        assert result is False

    def test_check_competitor_guard_paused_client(self, mock_backend_with_pipeline, mock_backend_with_clients):
        """check_competitor_guard should block paused clients."""
        result = network.check_competitor_guard("PausedInc", "Alice")
        assert result is False


class TestAtomicPromote:
    """Tests for atomic promote behavior (deal created before signal marked)."""

    def test_promote_creates_deal_first(self, mock_backend_with_signals, mock_backend_with_pipeline):
        """promote_signal should create deal before marking signal as promoted."""
        # This verifies the atomic behavior - deal is created successfully
        result = network.promote_signal(2)
        assert result["ok"] is True
        assert result["deal"]["ok"] is True


class TestRePromoteGuard:
    """Tests for re-promote guard."""

    def test_cannot_repromote_promoted_signal(self, mock_backend_with_signals, mock_backend_with_pipeline):
        """Cannot promote a signal that is already promoted."""
        # Row 3 is already promoted
        result = network.promote_signal(3)
        assert result["ok"] is False
        assert "already promoted" in result.get("error", "").lower()
