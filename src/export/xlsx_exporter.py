"""Excel (XLSX) registry export from database data."""

import logging
import tempfile
from pathlib import Path
from typing import List, Optional

from src.export.utils import group_requirements_by_sections

logger = logging.getLogger("api")


def export_xlsx_to_temp_file(
    document, sections: List, all_requirements: List, metrics=None
) -> Optional[Path]:
    """Build XLSX registry from database objects and return path to temp file.

    Args:
        document: DB Document ORM object.
        sections: List of DB Section ORM objects.
        all_requirements: List of DB Requirement ORM objects.
        metrics: DB CoverageMetrics ORM object or None.

    Returns:
        Path to the generated .xlsx temp file, or None if openpyxl is unavailable.
    """
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment
        from openpyxl.utils import get_column_letter
    except ImportError:
        logger.warning("openpyxl not installed, skipping Excel generation")
        return None

    wb = Workbook()
    ws = wb.active
    ws.title = "Реестр требований"

    # Header row
    headers = [
        "Раздел",
        "Номер раздела",
        "ID требования",
        "Текст требования",
        "Тип",
        "Приоритет",
        "Дисциплина",
        "Страница",
        "Статус",
        "Срок",
        "Ответственный",
    ]
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(wrap_text=True)

    section_reqs_map, orphans = group_requirements_by_sections(sections, all_requirements)

    # Append requirements row by row
    row_num = 2
    for section in sections:
        section_reqs = section_reqs_map[section.id]
        section_title = section.title or ""
        section_number = section.section_number or ""
        for req in section_reqs:
            display_text = req.human_edited or req.text or ""
            if req.subitems:
                display_text += "\n" + "\n".join(f"• {item}" for item in req.subitems)
            assignee_name = ""
            if hasattr(req, "assignee") and req.assignee:
                assignee_name = req.assignee.full_name or req.assignee.email or ""
            deadline_str = req.deadline.isoformat() if getattr(req, "deadline", None) else ""
            row_data = [
                section_title,
                section_number,
                req.requirement_id or "",
                display_text,
                req.type or "",
                req.priority or "",
                getattr(req, "discipline", None) or "",
                req.page_number or "",
                req.status or "pending",
                deadline_str,
                assignee_name,
            ]
            for col, val in enumerate(row_data, 1):
                ws.cell(row=row_num, column=col, value=val)
            row_num += 1

    for req in orphans:
        display_text = req.human_edited or req.text or ""
        if req.subitems:
            display_text += "\n" + "\n".join(f"• {item}" for item in req.subitems)
        assignee_name = ""
        if hasattr(req, "assignee") and req.assignee:
            assignee_name = req.assignee.full_name or req.assignee.email or ""
        deadline_str = req.deadline.isoformat() if getattr(req, "deadline", None) else ""
        row_data = [
            "Без раздела",
            "",
            req.requirement_id or "",
            display_text,
            req.type or "",
            req.priority or "",
            getattr(req, "discipline", None) or "",
            req.page_number or "",
            req.status or "pending",
            deadline_str,
            assignee_name,
        ]
        for col, val in enumerate(row_data, 1):
            ws.cell(row=row_num, column=col, value=val)
        row_num += 1

    # Auto-adjust column widths
    for col in range(1, len(headers) + 1):
        ws.column_dimensions[get_column_letter(col)].width = 15
    ws.column_dimensions["D"].width = 50  # Text column wider

    # Optional: add metrics sheet
    if metrics:
        ws_metrics = wb.create_sheet("Метрики покрытия")
        ws_metrics.cell(row=1, column=1, value="Параметр")
        ws_metrics.cell(row=1, column=2, value="Значение")
        ws_metrics.cell(row=1, column=1).font = Font(bold=True)
        ws_metrics.cell(row=1, column=2).font = Font(bold=True)
        ws_metrics.cell(row=2, column=1, value="Всего страниц")
        ws_metrics.cell(row=2, column=2, value=metrics.total_pages)
        ws_metrics.cell(row=3, column=1, value="Обработано страниц")
        ws_metrics.cell(row=3, column=2, value=metrics.processed_pages)
        ws_metrics.cell(row=4, column=1, value="Пропущено страниц")
        ws_metrics.cell(row=4, column=2, value=len(metrics.skipped_pages) if metrics.skipped_pages else 0)
        ws_metrics.cell(row=5, column=1, value="Покрытие %")
        ws_metrics.cell(row=5, column=2, value=f"{metrics.coverage_percent:.1f}")

    tmp = tempfile.NamedTemporaryFile(mode="wb", suffix=".xlsx", delete=False)
    wb.save(tmp.name)
    tmp.close()
    logger.info(f"[EXPORT] Excel registry generated: {tmp.name}")
    return Path(tmp.name)
