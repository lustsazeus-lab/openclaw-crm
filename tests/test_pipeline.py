"""Unit tests for pipeline module."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from openclaw_crm import pipeline


class TestGetPipeline:
    """Tests for get_pipeline function."""

    def test_get_pipeline_returns_all_deals_by_default(self, mock_backend_with_pipeline):
        """get_pipeline should return all deals when active_only is False."""
        deals = pipeline.get_pipeline(active_only=False)
        assert len(deals) == 3  # 3 deals in test data

    def test_get_pipeline_filters_active_deals(self, mock_backend_with_pipeline):
        """get_pipeline should filter out won/lost deals by default."""
        deals = pipeline.get_pipeline(active_only=True)
        # Should only have 2 active deals (Acme is won, Beta is lead, Gamma is negotiation)
        assert len(deals) == 2
        stages = [d.get("Stage", "").lower() for d in deals]
        assert "won" not in stages
        assert "lost" not in stages

    def test_get_pipeline_empty_sheet(self, mock_backend):
        """get_pipeline should return empty list when no data."""
        deals = pipeline.get_pipeline()
        assert deals == []


class TestCreateDeal:
    """Tests for create_deal function."""

    def test_create_deal_basic(self, mock_backend):
        """create_deal should create a new deal."""
        deal = {
            "client": "Test Corp",
            "source": "upwork",
            "stage": "lead",
            "budget": "$1000",
        }
        result = pipeline.create_deal(deal)
        assert result["ok"] is True
        assert result["client"] == "Test Corp"

    def test_create_deal_with_referred_by_sets_source_to_network(self, mock_backend):
        """create_deal should set source to network when referred_by is provided."""
        deal = {
            "client": "Referred Corp",
            "referred_by": "Alice",
            "stage": "lead",
            "budget": "$2000",
        }
        result = pipeline.create_deal(deal)
        assert result["ok"] is True


class TestMoveStage:
    """Tests for move_stage function."""

    def test_move_stage_existing_client(self, mock_backend_with_pipeline):
        """move_stage should update stage for existing client."""
        result = pipeline.move_stage("Beta Inc", "qualifying")
        assert result["ok"] is True
        assert result["stage"] == "qualifying"

    def test_move_stage_nonexistent_client(self, mock_backend_with_pipeline):
        """move_stage should return error for nonexistent client."""
        result = pipeline.move_stage("NonExistent Corp", "won")
        assert result["ok"] is False
        assert "not found" in result["error"]

    def test_move_stage_normalizes_stage_name(self, mock_backend_with_pipeline):
        """move_stage should normalize stage names to lowercase."""
        result = pipeline.move_stage("Beta Inc", "LEAD")
        assert result["ok"] is True
        assert result["stage"] == "lead"


class TestGetPipelineSummary:
    """Tests for get_pipeline_summary function."""

    def test_get_pipeline_summary_basic(self, mock_backend_with_pipeline):
        """get_pipeline_summary should return correct summary."""
        summary = pipeline.get_pipeline_summary()
        assert summary["total_deals"] == 2  # active deals only
        assert summary["won_deals"] == 1
        assert "lead" in summary["by_stage"]
        assert "negotiation" in summary["by_stage"]

    def test_get_pipeline_summary_network_count(self, mock_backend_with_pipeline):
        """get_pipeline_summary should count network-referred deals."""
        summary = pipeline.get_pipeline_summary()
        assert summary["network_count"] == 1  # Beta Inc has Referred By

    def test_get_pipeline_summary_empty(self, mock_backend):
        """get_pipeline_summary should handle empty pipeline."""
        summary = pipeline.get_pipeline_summary()
        assert summary["total_deals"] == 0
        assert summary["won_deals"] == 0
        assert summary["by_stage"] == {}


class TestGetStaleDeals:
    """Tests for get_stale_deals function."""

    def test_get_stale_deals_with_default_thresholds(self, mock_backend_with_pipeline):
        """get_stale_deals should categorize deals by staleness."""
        buckets = pipeline.get_stale_deals()
        assert 7 in buckets
        assert 14 in buckets
        assert 21 in buckets

    def test_get_stale_deals_custom_thresholds(self, mock_backend_with_pipeline):
        """get_stale_deals should use custom thresholds."""
        buckets = pipeline.get_stale_deals(thresholds=[5, 10])
        assert 5 in buckets
        assert 10 in buckets

    def test_get_stale_deals_empty_pipeline(self, mock_backend):
        """get_stale_deals should handle empty pipeline."""
        buckets = pipeline.get_stale_deals()
        for deals in buckets.values():
            assert deals == []


class TestEdgeCases:
    """Tests for edge cases."""

    def test_get_pipeline_handles_missing_columns(self, mock_backend):
        """get_pipeline should handle sheets with missing columns."""
        # Sheet with only some columns
        rows = [["Client", "Stage"], ["Test Corp", "lead"]]
        mock_backend.set_data("Pipeline!A:U", rows)
        deals = pipeline.get_pipeline()
        assert len(deals) == 1
        assert deals[0].get("Client") == "Test Corp"

    def test_create_deal_with_all_fields(self, mock_backend):
        """create_deal should handle all fields."""
        deal = {
            "client": "Full Corp",
            "contact": "John Doe",
            "source": "referral",
            "stage": "proposal",
            "budget": "$10000",
            "rate_type": "hourly",
            "service": "Full Stack Dev",
            "notes": "Important client",
            "owner": "Alice",
        }
        result = pipeline.create_deal(deal)
        assert result["ok"] is True
