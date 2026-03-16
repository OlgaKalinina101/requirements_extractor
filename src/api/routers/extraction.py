"""Extraction endpoint."""

import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, Depends

from src.api.schemas import ExtractionResult
from src.api.websocket import manager, WebSocketHandler, send_progress
from src.database.database import db_session
from src.auth.dependencies import require_manager

router = APIRouter(tags=["extraction"])
logger = logging.getLogger("api")


@router.post("", response_model=ExtractionResult)
async def extract_requirements(
    file: UploadFile = File(..., description="PDF file containing technical specifications"),
    generate_word: bool = Form(True),
    model: str = Form("claude-sonnet-4.5", description="AI model identifier"),
    project_id: Optional[str] = Form(None, description="Project ID to associate document with"),
    _current=Depends(require_manager),
) -> ExtractionResult:
    """Extract requirements from uploaded PDF using OpenRouter AI models."""
    from src.extraction_service import ExtractionService

    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    logger.info(f"[UPLOAD] Starting upload: {file.filename}")

    current_loop = asyncio.get_running_loop()

    ws_handler = WebSocketHandler(manager, current_loop)
    ws_handler.setLevel(logging.INFO)
    ws_handler.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))
    for log_name in ("api", "src.openrouter_client", "src.requirements_extractor", "src.pdf_processor"):
        logging.getLogger(log_name).addHandler(ws_handler)

    try:
        content = await file.read()
        service = ExtractionService(
            file_content=content,
            filename=file.filename,
            model=model,
            generate_word=generate_word,
            project_id=int(project_id) if project_id else None,
            ws_manager=manager,
            event_loop=current_loop,
            progress_callback=send_progress,
        )
        result_dict = await service.run(db_session)
        await send_progress("complete", 100, "Processing complete!")
        logger.info(f"[RESPONSE] document_id={result_dict.get('document_id')}, model_used={result_dict.get('model_used')}")
        return result_dict
    except ValueError as e:
        logger.error(f"[INIT] Invalid model '{model}': {e}")
        await send_progress("error", 0, f"Ошибка: Неверная модель '{model}'")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid model '{model}'. Available models: claude-sonnet-4.5, claude-opus-4.6, gpt-4.1, qwen-3.5-plus, gemini-3.1-pro",
        )
    except Exception as e:
        logger.error(f"Extraction failed: {e}", exc_info=True)
        await send_progress("error", 0, f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        for log_name in ("api", "src.openrouter_client", "src.requirements_extractor", "src.pdf_processor"):
            logging.getLogger(log_name).removeHandler(ws_handler)
