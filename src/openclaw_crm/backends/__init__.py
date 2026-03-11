"""Backends for OpenCLAW CRM.

This module provides pluggable backend implementations for Google Sheets access.
"""
from openclaw_crm.backends.gspread_backend import GspreadBackend

__all__ = ["GspreadBackend"]
