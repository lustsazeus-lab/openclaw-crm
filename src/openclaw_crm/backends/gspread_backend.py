"""Gspread backend implementation for Google Sheets.

This backend uses the gspread library as an alternative to the gws CLI.
Install with: pip install openclaw-crm[gspread]

Usage:
    from openclaw_crm.backends import GspreadBackend
    from openclaw_crm.sheets import set_backend

    set_backend(GspreadBackend())
"""
from __future__ import annotations

from typing import Any

import gspread
from gspread import Cell, Spreadsheet, Worksheet
from gspread.exceptions import APIError, SpreadsheetNotFound, WorksheetNotFound

from openclaw_crm.sheets import SheetResult, SheetsBackend


class GspreadBackend(SheetsBackend):
    """Google Sheets backend using gspread library.

    This backend provides an alternative to GWSBackend using the gspread
    Python library for direct Google Sheets API access.
    """

    def __init__(self, service_account_file: str | None = None) -> None:
        """Initialize the GspreadBackend.

        Args:
            service_account_file: Path to Google service account JSON file.
                                  If None, uses default credentials.
        """
        if service_account_file:
            self._gc = gspread.service_account(filename=service_account_file)
        else:
            # Use default credentials (ADC or ~/.config/gspread/service_account.json)
            self._gc = gspread.service_account()

    def _handle_error(self, e: Exception) -> SheetResult:
        """Handle gspread exceptions and return SheetResult."""
        if isinstance(e, SpreadsheetNotFound):
            return SheetResult(success=False, data=None, error=f"Spreadsheet not found: {e}")
        if isinstance(e, WorksheetNotFound):
            return SheetResult(success=False, data=None, error=f"Worksheet not found: {e}")
        if isinstance(e, APIError):
            return SheetResult(success=False, data=None, error=f"Google Sheets API error: {e}")
        return SheetResult(success=False, data=None, error=str(e))

    def read(self, spreadsheet_id: str, range_: str) -> SheetResult:
        """Read values from a Google Sheet.

        Args:
            spreadsheet_id: The ID of the spreadsheet (from URL).
            range_: The A1 notation of the range (e.g., 'Sheet1!A1:D10').

        Returns:
            SheetResult with data containing list of lists, or error.
        """
        try:
            sh: Spreadsheet = self._gc.open_by_key(spreadsheet_id)
            worksheet = self._get_worksheet(sh, range_)
            range_parts = range_.split("!")
            if len(range_parts) == 2:
                # Get specific range
                values = worksheet.get(range_parts[1])
            else:
                # Get all values
                values = worksheet.get_all_values()
            return SheetResult(success=True, data=values)
        except Exception as e:
            return self._handle_error(e)

    def append(
        self, spreadsheet_id: str, range_: str, values: list[list[str]]
    ) -> SheetResult:
        """Append values to a Google Sheet.

        Args:
            spreadsheet_id: The ID of the spreadsheet.
            range_: The A1 notation of the range (e.g., 'Sheet1!A1').
            values: List of rows to append.

        Returns:
            SheetResult with updated range info, or error.
        """
        try:
            sh: Spreadsheet = self._gc.open_by_key(spreadsheet_id)
            worksheet = self._get_worksheet(sh, range_)
            # Append rows
            result = worksheet.append_rows(values, value_input_option="USER_ENTERED")
            return SheetResult(success=True, data=result)
        except Exception as e:
            return self._handle_error(e)

    def update(
        self, spreadsheet_id: str, range_: str, values: list[list[str]]
    ) -> SheetResult:
        """Update values in a Google Sheet.

        Args:
            spreadsheet_id: The ID of the spreadsheet.
            range_: The A1 notation of the range (e.g., 'Sheet1!A1:D10').
            values: 2D list of values to update.

        Returns:
            SheetResult with updated range info, or error.
        """
        try:
            sh: Spreadsheet = self._gc.open_by_key(spreadsheet_id)
            worksheet = self._get_worksheet(sh, range_)
            # Update cells - gspread expects a flat list for update
            cell_list = worksheet.update(range_, values)
            return SheetResult(success=True, data={"updated_cells": len(cell_list)})
        except Exception as e:
            return self._handle_error(e)

    def _get_worksheet(self, sh: Spreadsheet, range_: str) -> Worksheet:
        """Extract worksheet from range string.

        Args:
            sh: Spreadsheet object.
            range_: Range in format 'SheetName!A1:D10' or just 'SheetName'.

        Returns:
            Worksheet object.
        """
        parts = range_.split("!")
        sheet_name = parts[0] if parts else "Sheet1"
        return sh.worksheet(sheet_name)


# Example usage (can be run directly)
if __name__ == "__main__":
    # Example: How to use GspreadBackend
    example_code = '''
    from openclaw_crm.backends.gspread_backend import GspreadBackend
    from openclaw_crm.sheets import set_backend, read_sheet, append_sheet, update_sheet

    # Initialize with optional service account file
    backend = GspreadBackend(service_account_file="/path/to/service_account.json")

    # Set as the default backend
    set_backend(backend)

    # Now use the standard API
    result = read_sheet("spreadsheet_id", "Sheet1!A1:D10")
    print(result.data)

    # Append data
    append_sheet("spreadsheet_id", "Sheet1", [["new", "row", "data"]])

    # Update data
    update_sheet("spreadsheet_id", "1:D2", [["updated", "data"], ["rowSheet1!A2", "data"]])
    '''
    print(example_code)
