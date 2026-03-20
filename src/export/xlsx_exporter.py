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
        "Статус проверки",
        "Статус ЖЦ",
        "Дисциплина",
        "Метод подтверждения",
        "Страница",
        "Срок",
        "Ответственный",
    ]
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(wrap_text=True)

    section_reqs_map, orphans = group_requirements_by_sections(sections, all_requirements)

    def _req_row(section_title, section_number, req):
        display_text = req.human_edited or req.text or ""
        if req.subitems:
            display_text += "\n" + "\n".join(f"• {item}" for item in req.subitems)
        assignee_name = ""
        if hasattr(req, "assignee") and req.assignee:
            assignee_name = req.assignee.full_name or req.assignee.email or ""
        return [
            section_title,
            section_number,
            req.requirement_id or "",
            display_text,
            req.type or "",
            req.priority or "",
            req.status or "pending",
            getattr(req, "lifecycle_status", None) or "",
            getattr(req, "discipline", None) or "",
            getattr(req, "verification_method", None) or "",
            req.page_number or "",
            req.deadline.isoformat() if getattr(req, "deadline", None) else "",
            assignee_name,
        ]

    # Append requirements row by row
    row_num = 2
    for section in sections:
        section_title = section.title or ""
        section_number = section.section_number or ""
        for req in section_reqs_map[section.id]:
            for col, val in enumerate(_req_row(section_title, section_number, req), 1):
                ws.cell(row=row_num, column=col, value=val)
            row_num += 1

    for req in orphans:
        for col, val in enumerate(_req_row("Без раздела", "", req), 1):
            ws.cell(row=row_num, column=col, value=val)
        row_num += 1

    # Auto-adjust column widths
    col_widths = [20, 15, 16, 50, 14, 12, 14, 14, 16, 20, 9, 12, 20]
    for col, width in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(col)].width = width

    # Links sheet
    all_reqs_flat = [r for reqs in section_reqs_map.values() for r in reqs] + orphans
    has_links = any(
        (getattr(r, "outgoing_links", None) or []) + (getattr(r, "incoming_links", None) or [])
        for r in all_reqs_flat
    )
    if has_links:
        ws_links = wb.create_sheet("Связи требований")
        link_headers = ["ID требования", "Направление", "Тип связи", "Связанное требование"]
        for col, h in enumerate(link_headers, 1):
            cell = ws_links.cell(row=1, column=col, value=h)
            cell.font = Font(bold=True)
        link_row = 2
        for req in all_reqs_flat:
            for link in (getattr(req, "outgoing_links", None) or []):
                target = getattr(link, "target_requirement", None)
                ws_links.cell(row=link_row, column=1, value=req.requirement_id)
                ws_links.cell(row=link_row, column=2, value="→")
                ws_links.cell(row=link_row, column=3, value=link.link_type)
                ws_links.cell(row=link_row, column=4, value=target.requirement_id if target else "")
                link_row += 1
            for link in (getattr(req, "incoming_links", None) or []):
                source = getattr(link, "source_requirement", None)
                ws_links.cell(row=link_row, column=1, value=req.requirement_id)
                ws_links.cell(row=link_row, column=2, value="←")
                ws_links.cell(row=link_row, column=3, value=link.link_type)
                ws_links.cell(row=link_row, column=4, value=source.requirement_id if source else "")
                link_row += 1
        for col, width in enumerate([20, 12, 20, 20], 1):
            ws_links.column_dimensions[get_column_letter(col)].width = width

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
