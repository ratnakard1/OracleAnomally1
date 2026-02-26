#!/usr/bin/env python3
"""Convert database performance tuning recommendations to Excel format."""

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

def create_performance_tuning_xl():
    wb = Workbook()
    ws = wb.active
    ws.title = "DB Performance Tuning"

    # Header style
    header_fill = PatternFill(start_color="2F5496", end_color="2F5496", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )

    headers = ["#", "Action/Recommendation", "Details", "Status / Notes"]
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin_border

    data = [
        (1, "Increase Buffer Cache", "ADDM and advisory both suggest an increase (e.g., to ~70 GB)", "Planning part of CRQ#"),
        (2, "Increase PGA", "Target exceeded; raise pga_aggregate_target by ~40–50% (Current Size 100GB)", "Need to investigate more, probably will work with Oracle"),
        (3, "Tune Top I/O SQLs", "Especially 4z83wfaxqtdp7, 5yn8skt7tm21p, 22rydaq9zqcxs", "Need to be analyzed"),
        (4, "Reduce dblink Usage", "SQL*Net message from dblink accounts for 2.3% of DB time", "Need to take it with SRE"),
        (5, "Investigate Parse Contention", "Parse CPU to Parse Elapsed 32.87%; check shared pool and cursor usage", "Increasing Buffer cache at #1 should take care of this"),
        (6, "Review Redo Configuration", "Reduce redo log space requests and optimize archive destination. 1. Increase redo size from 1GB to 2GB, 2. Check redo storage performance", "Need to revisit - Part of PMX"),
        (7, "Tune High-CPU SQLs", "6q6gwbfc78ux7 (TPOP_VALIDATION), 0vqt1a627sdna (DELAYED_ACTIVITIES), gdf06rsgk493z", ""),
        (8, "Cache or Batch Frequent Lookups", "SUBSCRIBER_RSOURCE PTN lookups", "Need to check"),
        (9, "Table Cleanup", "Top 10 largest tables", "Need to work with SRE"),
    ]

    for row_idx, (num, action, details, status) in enumerate(data, start=2):
        ws.cell(row=row_idx, column=1, value=num)
        ws.cell(row=row_idx, column=2, value=action)
        ws.cell(row=row_idx, column=3, value=details)
        ws.cell(row=row_idx, column=4, value=status)
        for col in range(1, 5):
            cell = ws.cell(row=row_idx, column=col)
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            cell.border = thin_border

    # Column widths
    ws.column_dimensions['A'].width = 6
    ws.column_dimensions['B'].width = 28
    ws.column_dimensions['C'].width = 70
    ws.column_dimensions['D'].width = 45

    wb.save("/workspace/Database_Performance_Tuning_Plan.xlsx")
    print("Created: Database_Performance_Tuning_Plan.xlsx")

if __name__ == "__main__":
    create_performance_tuning_xl()
