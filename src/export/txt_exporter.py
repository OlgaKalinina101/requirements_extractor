"""TXT report export from database data."""

import logging
import tempfile
from pathlib import Path
from typing import List, Optional

from .utils import group_requirements_by_sections

logger = logging.getLogger("api")


def build_txt_report(
    document,
    sections: List,
    all_requirements: List,
    metrics=None,
) -> str:
    """Build TXT report content from document, sections, requirements, and metrics."""
    lines = [
        "=" * 80,
        "РЕЕСТР ТРЕБОВАНИЙ",
        "=" * 80,
        "",
        f"Документ: {document.filename}",
        f"Дата обработки: {document.uploaded_at.strftime('%d.%m.%Y %H:%M') if document.uploaded_at else 'N/A'}",
        f"Модель: {document.model_used or 'N/A'}",
        "",
        "=" * 80,
        "СТАТИСТИКА",
        "=" * 80,
        "",
        f"Всего требований: {len(all_requirements)}",
        f"Всего разделов: {len(sections)}",
        "",
    ]

    if metrics:
        lines.extend([
            f"Всего страниц: {metrics.total_pages}",
            f"Обработано страниц: {metrics.processed_pages}",
            f"Пропущено страниц: {len(metrics.skipped_pages) if metrics.skipped_pages else 0}",
            f"Покрытие: {metrics.coverage_percent:.1f}%",
            "",
        ])

    if metrics and metrics.requirements_by_type:
        lines.extend(["=" * 80, "ТРЕБОВАНИЯ ПО ТИПАМ", "=" * 80, ""])
        for req_type, count in metrics.requirements_by_type.items():
            lines.append(f"  {req_type}: {count}")
        lines.append("")

    # Full requirements listing grouped by section
    lines.extend(["=" * 80, "ПОЛНЫЙ РЕЕСТР ТРЕБОВАНИЙ", "=" * 80, ""])

    section_reqs, orphans = group_requirements_by_sections(sections, all_requirements)
    for section in sections:
        section_requirements = section_reqs[section.id]

        lines.append("─" * 60)
        lines.append(f"Раздел {section.section_number}: {section.title}")
        lines.append(f"Страницы: {section.page_start} – {section.page_end}  |  Требований: {len(section_requirements)}")
        lines.append("─" * 60)
        lines.append("")

        for req in section_requirements:
            display_text = req.human_edited or req.text or ""
            lines.append(
                f"[{req.requirement_id}] стр.{req.page_number or '?'}  [{req.type or '—'}]  [{req.priority or '—'}]  [{req.status}]"
            )
            lines.append(f"  {display_text}")
            if req.subitems:
                for item in req.subitems:
                    lines.append(f"    • {item}")
            lines.append("")

    # Orphan requirements (section_id is NULL)
    if orphans:
        lines.extend(["─" * 60, f"Требования без раздела  ({len(orphans)} шт.)", "─" * 60, ""])
        for req in orphans:
            display_text = req.human_edited or req.text or ""
            lines.append(
                f"[{req.requirement_id}] стр.{req.page_number or '?'}  [{req.type or '—'}]  [{req.priority or '—'}]  [{req.status}]"
            )
            lines.append(f"  {display_text}")
            if req.subitems:
                for item in req.subitems:
                    lines.append(f"    • {item}")
            lines.append("")

    lines.append("=" * 80)
    return "\n".join(lines)


def export_txt_to_temp_file(
    document,
    sections: List,
    all_requirements: List,
    metrics=None,
) -> Path:
    """Build TXT report and save to temporary file. Returns path to temp file."""
    content = build_txt_report(document, sections, all_requirements, metrics)
    temp_file = tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    )
    temp_file.write(content)
    temp_file.close()
    logger.info(f"[EXPORT] TXT report generated: {temp_file.name}")
    return Path(temp_file.name)
