"""Extraction service — orchestrates the PDF → AI → DB pipeline.

Splits the logic that previously lived in the 450-line
``extract_requirements`` endpoint into focused methods so each step can
be reasoned about, tested and modified independently.
"""

from __future__ import annotations

import asyncio
import logging
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.config import ApplicationConfig, load_from_env
from src.models import Requirement
from src.requirements_extractor import RequirementsExtractor, create_extractor
from src.usage_tracker import get_usage_report, reset_usage_report

logger = logging.getLogger("api")


class ExtractionService:
    """Orchestrates the full PDF extraction pipeline for a single request."""

    UPLOAD_DIR = Path("data/uploads")

    def __init__(
        self,
        file_content: bytes,
        filename: str,
        model: str,
        generate_word: bool,
        project_id: Optional[int],
        ws_manager,
        event_loop: asyncio.AbstractEventLoop,
        progress_callback=None,
    ) -> None:
        self.file_content = file_content
        self.filename = filename
        self.model = model
        self.generate_word = generate_word
        self.project_id = project_id
        self.ws_manager = ws_manager
        self.event_loop = event_loop
        # Async callable: async def send_progress(step, pct, message) -> None
        self._send_progress = progress_callback

        self.pdf_path: Optional[Path] = None
        self.output_dir: Optional[Path] = None
        self.extractor: Optional[RequirementsExtractor] = None
        self.config: Optional[ApplicationConfig] = None
        self.db_document = None
        self.all_requirements: List[Requirement] = []
        self.total_requirements_saved: int = 0

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def _progress(self, step: str, pct: int, message: str) -> None:
        """Fire progress update if a callback was provided."""
        if self._send_progress is not None:
            try:
                await self._send_progress(step, pct, message)
            except Exception as e:
                logger.warning(f"[PROGRESS] Failed to send progress update: {e}")

    async def run(self, db_session_factory) -> Dict[str, Any]:
        """Execute the full pipeline; returns a dict suitable for ExtractionResult."""
        start_time = datetime.now()
        try:
            await self._progress("upload", 10, f"Сохранение файла: {self.filename}")
            await self._save_file()

            await self._progress("init", 15, "Создание записи в базе данных")
            await self._create_db_document(db_session_factory)

            await self._progress("init", 20, "Инициализация AI-клиента")
            await self._init_extractor()

            await self._progress("pdf", 25, "Извлечение страниц PDF")
            await self._extract_pdf_pages()

            await self._progress("extract", 30, "Начало извлечения требований")
            await self._update_db_status("processing", db_session_factory)
            await self._extract_requirements()

            await self._progress("save", 90, "Сохранение требований в базу данных")
            await self._save_to_db(db_session_factory)
            await self._save_coverage_metrics(db_session_factory)
            await self._finalize_db(db_session_factory)

            if self.generate_word:
                await self._progress("export", 95, "Генерация Word-документа")
            word_path = await self._build_word() if self.generate_word else None

            return self._build_result(start_time, word_path)
        finally:
            if self.output_dir and self.output_dir.exists():
                import shutil
                try:
                    shutil.rmtree(self.output_dir)
                except Exception as e:
                    logger.warning(f"[CLEANUP] Could not remove temp dir: {e}")

    # ------------------------------------------------------------------
    # Pipeline steps
    # ------------------------------------------------------------------

    async def _save_file(self) -> None:
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_filename = f"{timestamp}_{self.filename}"
        self.pdf_path = self.UPLOAD_DIR / pdf_filename
        with open(self.pdf_path, "wb") as f:
            f.write(self.file_content)
        logger.info(f"[UPLOAD] File saved: {self.pdf_path}")

        temp_dir = tempfile.mkdtemp(prefix=f"req_extract_{timestamp}_")
        self.output_dir = Path(temp_dir)
        logger.info(f"[TEMP] Temp directory: {self.output_dir}")

    async def _create_db_document(self, db_session_factory) -> None:
        from src.database import crud
        try:
            with db_session_factory() as db:
                self.db_document = crud.create_document(
                    db=db,
                    filename=self.filename,
                    file_path=str(self.pdf_path),
                    total_pages=None,
                    project_id=self.project_id,
                    model_used=self.model,
                )
            logger.info(f"[DB] Document created: id={self.db_document.id}")
        except Exception as e:
            logger.error(f"[DB] Failed to create document: {e}", exc_info=True)

    async def _init_extractor(self) -> None:
        reset_usage_report()
        self.config = load_from_env()
        self.config.pdf_path = self.pdf_path
        self.config.output_dir = self.output_dir
        self.config.image_dir = self.output_dir / "images"
        self.config.provider = "openrouter"
        self.config.image_dir.mkdir(parents=True, exist_ok=True)
        self.extractor = create_extractor(self.config, model_id=self.model)
        logger.info(f"[INIT] Extractor created with model: {self.model}")

    async def _extract_pdf_pages(self) -> None:
        loop = asyncio.get_running_loop()
        main_loop = loop

        def sync_progress(current: int, total: int) -> None:
            if current % 10 == 0 or current == 1 or current == total:
                logger.info(f"[PDF] {current}/{total} pages extracted")

        def _extract():
            return self.extractor.pdf_processor.extract_pages(
                self.pdf_path,
                self.config.image_dir,
                progress_callback=sync_progress,
            )

        with ThreadPoolExecutor() as executor:
            self.extractor.pages, self.extractor.page_image_metadata = await loop.run_in_executor(
                executor, _extract
            )
        logger.info(f"[PDF] Extracted {len(self.extractor.pages)} pages")

    async def _update_db_status(self, status: str, db_session_factory) -> None:
        if not self.db_document:
            return
        from src.database import crud
        try:
            with db_session_factory() as db:
                crud.update_document_status(
                    db=db,
                    document_id=self.db_document.id,
                    status=status,
                    total_pages=len(self.extractor.pages),
                )
        except Exception as e:
            logger.warning(f"[DB] Failed to update status to '{status}': {e}")

    async def _extract_requirements(self) -> None:
        if not self.extractor.ai_client:
            raise RuntimeError("AI client not configured")

        total_pages = len(self.extractor.pages)
        completed_pages = 0

        def page_progress_callback(page_num: int, total: int, message: str) -> None:
            """Called from thread pool after each page — bridges sync→async safely."""
            nonlocal completed_pages
            if self._send_progress is None or self.event_loop is None:
                return
            completed_pages += 1
            # Progress only moves forward: based on completed count, never page number
            pct = 30 + int((completed_pages / max(total, 1)) * 58)  # 30%→88%
            asyncio.run_coroutine_threadsafe(
                self._send_progress("extract", pct, f"Обработано страниц: {completed_pages}/{total}"),
                self.event_loop,
            )

        self.all_requirements = await self.extractor.extract_requirements_from_all_pages(
            image_dir=self.output_dir,
            batch_size=7,
            progress_callback=page_progress_callback,
        )
        logger.info(f"[EXTRACT] {len(self.all_requirements)} requirements extracted")

    async def _save_to_db(self, db_session_factory) -> None:
        if not self.db_document:
            self.total_requirements_saved = len(self.all_requirements)
            return
        from src.database import crud
        try:
            with db_session_factory() as db:
                db_section = crud.create_section(
                    db=db,
                    document_id=self.db_document.id,
                    section_number="1",
                    title="All Pages",
                    page_start=1,
                    page_end=len(self.extractor.pages),
                )
                self.total_requirements_saved = crud.bulk_create_requirements(
                    db=db,
                    document_id=self.db_document.id,
                    section_id=db_section.id,
                    requirements=self.all_requirements,
                )
            logger.info(f"[DB] Saved {self.total_requirements_saved} requirements")
        except Exception as e:
            logger.error(f"[DB] Failed to save requirements: {e}", exc_info=True)
            self.total_requirements_saved = len(self.all_requirements)

    async def _save_coverage_metrics(self, db_session_factory) -> None:
        if not self.db_document:
            return
        from src.database import crud
        try:
            total_pages = len(self.extractor.pages)
            pages_with_reqs = {
                r.source_page for r in self.all_requirements
                if hasattr(r, "source_page") and r.source_page
            }
            processed_pages = len(pages_with_reqs)
            skipped_pages = sorted(set(range(1, total_pages + 1)) - pages_with_reqs)
            coverage_pct = (processed_pages / total_pages * 100) if total_pages > 0 else 0.0

            with db_session_factory() as db:
                crud.create_coverage_metrics(
                    db=db,
                    document_id=self.db_document.id,
                    total_pages=total_pages,
                    processed_pages=processed_pages,
                    skipped_pages=skipped_pages,
                    coverage_percent=coverage_pct,
                    requirements_count=self.total_requirements_saved,
                )
            logger.info(f"[DB] Coverage metrics saved: {processed_pages}/{total_pages} pages")
        except Exception as e:
            logger.error(f"[DB] Failed to save coverage metrics: {e}", exc_info=True)

    async def _finalize_db(self, db_session_factory) -> None:
        await self._update_db_status("completed", db_session_factory)

    async def _build_word(self) -> Optional[Path]:
        usage_report = get_usage_report()
        try:
            from src.word_exporter import generate_word_document
            return await generate_word_document(self.extractor, usage_report, self.output_dir)
        except Exception as e:
            logger.warning(f"[WORD] Word generation failed: {e}")
            return None

    def _build_result(self, start_time: datetime, word_path: Optional[Path]) -> Dict[str, Any]:
        usage_report = get_usage_report()
        usage_report_path = self.output_dir / "usage_report.txt"
        usage_report.save_to_file(usage_report_path, provider_name="OpenRouter")

        cwd = Path.cwd()

        def rel(p: Path) -> str:
            try:
                return str(p.absolute().relative_to(cwd))
            except ValueError:
                return str(p).replace("\\", "/")

        files: Dict[str, str] = {
            "registry": rel(self.extractor.save_registry()),
            "usage_report": rel(usage_report_path),
        }
        if word_path:
            files["word_document"] = rel(word_path)

        return {
            "success": True,
            "message": "Requirements extracted successfully",
            "requirements_count": self.total_requirements_saved,
            "sections_count": len(self.extractor.registry.sections),
            "total_tokens": usage_report.total_tokens,
            "total_cost": usage_report.total_cost,
            "processing_time": (datetime.now() - start_time).total_seconds(),
            "files": files,
            "model_used": self.model,
            "document_id": self.db_document.id if self.db_document else None,
        }
