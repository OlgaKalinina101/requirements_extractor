"""FastAPI backend server for PDF requirements extraction.

This module provides a RESTful API and WebSocket interface for extracting
requirements from PDF technical specifications using OpenRouter AI models.

Features:
    - File upload and processing
    - Real-time progress updates via WebSocket
    - Requirements extraction with AI (OpenRouter: Claude, GPT, Gemini, Qwen)
    - Image-based requirements extraction (multimodal)
    - Word and JSON export
    - Usage tracking and cost calculation
"""

# Standard library imports
import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Third-party imports
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

# Local imports
from src.config import ApplicationConfig, load_from_env
from src.requirements_extractor import RequirementsExtractor, create_extractor
from src.logger import setup_logger
from src.models import TableOfContentsEntry, RequirementType, RequirementPriority
from src.usage_tracker import get_usage_report, reset_usage_report
from src.database.database import get_db, init_db
from src.database import crud
from src.database.models import Document, Requirement, Section, CoverageMetrics

# Setup logging
setup_logger(name="api", log_file=Path("logs/api.log"), level="INFO")
logger = logging.getLogger("api")

# Setup logging for other modules
setup_logger(name="src.openrouter_client", log_file=Path("logs/openrouter.log"), level="INFO")
setup_logger(name="src.requirements_extractor", log_file=Path("logs/extractor.log"), level="INFO")
setup_logger(name="src.pdf_processor", log_file=Path("logs/pdf.log"), level="INFO")

# Create FastAPI app
app = FastAPI(
    title="PDF Requirements Extractor API - OpenRouter",
    description="Extract requirements from technical specifications using OpenRouter AI models (Claude, GPT, Gemini, Qwen)",
    version="3.0.0"
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database on application startup."""
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        logger.warning("Continuing without database - some features may not work")

# WebSocket connections manager
class ConnectionManager:
    """Manages WebSocket connections for real-time communication.
    
    Handles multiple concurrent WebSocket connections, broadcasting messages
    to all connected clients, and cleaning up disconnected clients.
    
    Attributes:
        active_connections: List of currently active WebSocket connections.
    """
    
    def __init__(self) -> None:
        """Initialize the connection manager with an empty connections list."""
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and register a new WebSocket connection.
        
        Args:
            websocket: The WebSocket connection to register.
        """
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket) -> None:
        """Unregister a WebSocket connection.
        
        Args:
            websocket: The WebSocket connection to remove.
        """
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
        else:
            logger.warning("WebSocket disconnect called but connection not in list")

    async def send_message(self, message: Dict[str, Any]) -> None:
        """Send message to all connected clients.
        
        Broadcasts the message to all active connections. Automatically
        removes disconnected clients that fail to receive the message.
        
        Args:
            message: Dictionary containing the message data to broadcast.
        """
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error sending message via WebSocket: {e}")
                disconnected.append(connection)
        
        # Remove disconnected clients
        for conn in disconnected:
            if conn in self.active_connections:
                self.active_connections.remove(conn)
                logger.info(f"Removed disconnected WebSocket. Remaining: {len(self.active_connections)}")

manager = ConnectionManager()


# Custom logging handler to send logs via WebSocket
class WebSocketHandler(logging.Handler):
    """Custom logging handler that sends log messages via WebSocket.
    
    This handler intercepts log messages and broadcasts them to all
    connected WebSocket clients. Uses thread-safe async execution to
    work correctly from both main thread and ThreadPoolExecutor threads.
    
    Attributes:
        manager: ConnectionManager instance for broadcasting messages.
        loop: asyncio event loop for thread-safe coroutine execution.
    """
    
    def __init__(self, manager_instance: ConnectionManager, event_loop: asyncio.AbstractEventLoop) -> None:
        """Initialize the WebSocket logging handler.
        
        Args:
            manager_instance: ConnectionManager for broadcasting log messages.
            event_loop: Event loop for scheduling coroutines from any thread.
        """
        super().__init__()
        self.manager = manager_instance
        self.loop = event_loop
        
    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record by sending it via WebSocket.
        
        Formats the log record and broadcasts it to all connected clients
        using thread-safe async execution.
        
        Args:
            record: The log record to emit.
        """
        try:
            log_entry = {
                "type": "log",
                "level": record.levelname,
                "message": self.format(record),
                "timestamp": datetime.now().isoformat()
            }
            # Use run_coroutine_threadsafe for thread-safe async call
            asyncio.run_coroutine_threadsafe(
                self.manager.send_message(log_entry),
                self.loop
            )
        except Exception as e:
            # Don't let logging errors break the app
            print(f"WebSocket logging error: {e}")


# Pydantic models for API responses
class ExtractionStatus(BaseModel):
    """Status information for ongoing extraction process.
    
    Attributes:
        status: Current status of extraction ('processing', 'completed', 'failed').
        progress: Progress percentage (0-100).
        current_step: Name of current processing step.
        message: Human-readable status message.
    """
    
    status: str = Field(..., description="Current extraction status")
    progress: int = Field(..., ge=0, le=100, description="Progress percentage")
    current_step: str = Field(..., description="Current processing step")
    message: str = Field(..., description="Status message")


class ExtractionResult(BaseModel):
    """Result of completed extraction process.
    
    Attributes:
        success: Whether extraction completed successfully.
        message: Result message or error description.
        requirements_count: Total number of requirements extracted.
        sections_count: Number of document sections processed.
        total_tokens: Total AI tokens consumed.
        total_cost: Total cost in USD.
        processing_time: Processing time in seconds.
        files: Dictionary mapping file types to file paths.
        model_used: AI model used for extraction.
    """
    
    success: bool = Field(..., description="Success status")
    message: str = Field(..., description="Result message")
    requirements_count: int = Field(..., ge=0, description="Number of requirements")
    sections_count: int = Field(..., ge=0, description="Number of sections")
    total_tokens: int = Field(..., ge=0, description="Total tokens used")
    total_cost: float = Field(..., ge=0, description="Total cost in USD")
    processing_time: float = Field(..., ge=0, description="Processing time in seconds")
    files: Dict[str, str] = Field(..., description="Generated file paths")
    model_used: Optional[str] = Field(None, description="AI model used")
    document_id: Optional[int] = Field(None, description="Database document ID")


# Review API request models
class EditRequirementRequest(BaseModel):
    """Request model for editing a requirement.
    
    Attributes:
        edited_text: New requirement text after human editing.
        reason: Optional reason for the edit.
        edited_by: Optional identifier of the person who edited.
    """
    
    edited_text: str = Field(..., description="New requirement text", min_length=1)
    reason: Optional[str] = Field(None, description="Reason for editing")
    edited_by: Optional[str] = Field(None, description="User who edited the requirement")


class RejectRequirementRequest(BaseModel):
    """Request model for rejecting a requirement.
    
    Attributes:
        reason: Optional reason for rejection.
    """
    
    reason: Optional[str] = Field(None, description="Reason for rejection")


@app.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint providing API information.
    
    Returns:
        Dictionary with API name, version, and status.
    """
    return {
        "name": "PDF Requirements Extractor API",
        "version": "2.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint for monitoring.
    
    Returns:
        Dictionary with health status and current timestamp.
    """
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time log streaming.
    
    Accepts WebSocket connections and streams log messages and progress
    updates in real-time. Supports ping/pong for connection keep-alive.
    
    Args:
        websocket: The WebSocket connection to handle.
        
    Raises:
        WebSocketDisconnect: When client disconnects.
    """
    await manager.connect(websocket)
    
    # Send welcome message
    await websocket.send_json({
        "type": "log",
        "level": "INFO",
        "message": "WebSocket connection established successfully",
        "timestamp": datetime.now().isoformat()
    })
    
    try:
        while True:
            # Keep connection alive and handle pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)


async def send_progress(step: str, progress: int, message: str) -> None:
    """Send progress update to all connected WebSocket clients.
    
    Broadcasts progress information to connected clients and logs to console
    and file. Handles cases where no clients are connected.
    
    Args:
        step: Name of the current processing step (e.g., 'upload', 'pdf', 'extract').
        progress: Progress percentage (0-100).
        message: Human-readable progress message.
    """
    progress_msg = {
        "type": "progress",
        "step": step,
        "progress": progress,
        "message": message,
        "timestamp": datetime.now().isoformat()
    }
    
    # Debug logging
    print(f"[PROGRESS] Sending: {progress}% - {message}")  # Console output
    logger.info(f"[PROGRESS] {progress}% - {message}")  # File log
    
    # Send to WebSocket
    if len(manager.active_connections) > 0:
        await manager.send_message(progress_msg)
        print(f"[PROGRESS] Sent to {len(manager.active_connections)} client(s)")
    else:
        print("[PROGRESS] WARNING: No active WebSocket connections!")


@app.post("/api/extract", response_model=ExtractionResult)
async def extract_requirements(
    file: UploadFile = File(..., description="PDF file containing technical specifications"),
    generate_word: bool = Form(True),
    model: str = Form("claude-sonnet-4.5", description="AI model identifier"),
    project_id: Optional[str] = Form(None, description="Project ID to associate document with"),
) -> ExtractionResult:
    """Extract requirements from uploaded PDF file using OpenRouter AI models.
    
    This endpoint:
    1. Validates and saves the uploaded PDF
    2. Extracts text and images from all pages
    3. Parses table of contents (or creates automatic sections)
    4. Extracts requirements from text using selected AI model
    5. Extracts requirements from images using multimodal AI
    6. Generates JSON registry and optional Word document
    7. Calculates token usage and costs
    
    Progress updates are sent via WebSocket in real-time.
    
    Args:
        file: PDF file to process (technical specification document).
        generate_word: Whether to generate Word document with results.
        model: AI model to use (default: claude-sonnet-4.5)
    
    Returns:
        ExtractionResult containing success status, statistics, and file paths.
        
    Raises:
        HTTPException: If file is invalid, processing fails, or API errors occur.
    """
    start_time = datetime.now()
    output_dir = None  # Initialize for cleanup in finally block
    
    try:
        # Validate file
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        await send_progress("upload", 5, f"Uploading file: {file.filename}")
        logger.info(f"[UPLOAD] Starting upload: {file.filename}")
        
        # Save uploaded file
        upload_dir = Path("data/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_filename = f"{timestamp}_{file.filename}"
        pdf_path = upload_dir / pdf_filename
        
        content = await file.read()
        with open(pdf_path, "wb") as f:
            f.write(content)
        
        logger.info(f"File uploaded: {pdf_path}")
        logger.info(f"Current working directory: {Path.cwd()}")
        
        # Save document to database
        db_document = None
        try:
            print("[DB] Attempting to connect to database...")
            db = next(get_db())
            print("[DB] Database connection successful")
            db_document = crud.create_document(
                db=db,
                filename=file.filename,
                file_path=str(pdf_path),
                total_pages=None,
                project_id=int(project_id) if project_id else None,
                model_used=model,
            )
            print(f"[DB] Document saved to database with ID: {db_document.id}")
            await send_progress("upload", 10, f"File uploaded successfully (Document ID: {db_document.id})")
        except Exception as db_error:
            print(f"[DB] FAILED to save document: {db_error}")
            import traceback
            traceback.print_exc()
            logger.error(f"[DB] Failed to save document to database: {db_error}", exc_info=True)
            logger.warning("[DB] Continuing without database - data will only be saved to files")
            await send_progress("upload", 10, "File uploaded successfully")
        
        # Create temporary directory for this session
        import tempfile
        temp_session_dir = tempfile.mkdtemp(prefix=f"req_extract_{timestamp}_")
        output_dir = Path(temp_session_dir)
        
        logger.info(f"[TEMP] Using temporary directory: {output_dir}")
        
        # Reset usage tracking
        reset_usage_report()
        
        # Get current event loop for thread-safe WebSocket communication
        current_loop = asyncio.get_running_loop()
        
        # Setup WebSocket logging for this extraction
        ws_handler = WebSocketHandler(manager, current_loop)
        ws_handler.setLevel(logging.INFO)
        ws_handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
        
        # Add handler to relevant loggers
        api_logger = logging.getLogger("api")
        api_logger.addHandler(ws_handler)
        
        openrouter_logger = logging.getLogger("src.openrouter_client")
        openrouter_logger.addHandler(ws_handler)
        
        extractor_logger = logging.getLogger("src.requirements_extractor")
        extractor_logger.addHandler(ws_handler)
        
        pdf_logger = logging.getLogger("src.pdf_processor")
        pdf_logger.addHandler(ws_handler)
        
        await send_progress("init", 15, "Initializing extractor")
        logger.info(f"[INIT] Creating configuration and extractor with model: {model}")
        await asyncio.sleep(0.3)
        
        # Load configuration from environment
        config = load_from_env()
        config.pdf_path = pdf_path
        config.output_dir = output_dir
        config.image_dir = output_dir / "images"
        config.provider = "openrouter"  # Use OpenRouter by default
        
        # Ensure image directory exists BEFORE creating extractor
        # (ApplicationConfig.__post_init__ only creates the default data/images path)
        config.image_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"[INIT] Image directory: {config.image_dir}")
        
        # Create extractor with selected model
        # PDF processor is initialized automatically in RequirementsExtractor.__init__
        try:
            extractor = create_extractor(config, model_id=model)
        except ValueError as e:
            # Handle invalid model error
            error_msg = str(e)
            logger.error(f"[INIT] Invalid model '{model}': {error_msg}")
            await send_progress("error", 0, f"Ошибка: Неверная модель '{model}'")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid model '{model}'. Available models: claude-sonnet-4.5, claude-opus-4.6, gpt-4.1, qwen-3.5-plus, gemini-3.1-pro"
            )
        
        # Verify model was set correctly
        actual_model = extractor.ai_client.selected_model if extractor.ai_client else None
        logger.info(f"[INIT] Requested model: {model}, Actual model in client: {actual_model} via {config.provider}")
        
        # Step 1: Extract PDF pages with progress callback
        logger.info(f"[PDF] Starting PDF extraction for {pdf_path}")
        await send_progress("pdf", 20, "📄 Starting PDF extraction...")
        await asyncio.sleep(0.3)
        
        # Get the event loop for thread-safe calls
        main_loop = asyncio.get_running_loop()
        
        # Track pages processed
        pages_processed = [0]
        total_pages_ref = [0]
        last_update = [0]  # Track last update to avoid too many messages
        
        def sync_progress(current: int, total: int):
            """Sync wrapper for progress callback - thread-safe."""
            pages_processed[0] = current
            total_pages_ref[0] = total
            percentage = 20 + int((current / total) * 10)  # 20-30%
            
            # Log progress (every 10 pages)
            if current % 10 == 0 or current == 1 or current == total:
                logger.info(f"[PDF] Extraction progress: {current}/{total} pages")
            
            # Send to WebSocket (every 5 pages to avoid spam)
            if current - last_update[0] >= 5 or current == 1 or current == total:
                last_update[0] = current
                # Use run_coroutine_threadsafe for thread-safe async call
                asyncio.run_coroutine_threadsafe(
                    send_progress(
                        "pdf", 
                        percentage, 
                        f"📄 Extracting pages: {current}/{total}"
                    ),
                    main_loop
                )
        
        # Extract pages with progress - run in executor to not block
        from concurrent.futures import ThreadPoolExecutor
        
        loop = asyncio.get_event_loop()
        
        def extract_pdf_sync():
            logger.info("[PDF] Starting pymupdf extraction")
            pages, image_metadata = extractor.pdf_processor.extract_pages(
                pdf_path,
                config.image_dir,
                progress_callback=sync_progress
            )
            return pages, image_metadata
        
        # Run in executor to allow async operations to continue
        logger.info("[PDF] Running extraction in thread pool")
        with ThreadPoolExecutor() as executor:
            extractor.pages, extractor.page_image_metadata = await loop.run_in_executor(executor, extract_pdf_sync)
        
        total_images = sum(len(imgs) for imgs in extractor.page_image_metadata.values())
        logger.info(f"[PDF] Extraction complete: {len(extractor.pages)} pages, {total_images} images")
        if total_images > 0:
            logger.info(f"[PDF] Images found on pages: {sorted(extractor.page_image_metadata.keys())}")
            for page_num, imgs in extractor.page_image_metadata.items():
                logger.debug(f"[PDF] Page {page_num}: {len(imgs)} images - {[img['filename'] for img in imgs]}")
        else:
            logger.warning("[PDF] No images found in PDF!")
        await send_progress("pdf", 30, f"✅ Extracted {len(extractor.pages)} pages successfully")
        await asyncio.sleep(0.5)
        
        # Update document status to processing
        if db_document:
            try:
                db = next(get_db())
                crud.update_document_status(
                    db=db,
                    document_id=db_document.id,
                    status="processing",
                    total_pages=len(extractor.pages),
                )
                logger.info(f"[DB] Document {db_document.id} status updated to 'processing'")
            except Exception as db_error:
                logger.warning(f"[DB] Failed to update document status: {db_error}")
        
        # Step 2: Parse TOC from first pages or use AI
        logger.info("[TOC] Starting table of contents analysis")
        await send_progress("toc", 35, "📚 Analyzing document structure...")
        await asyncio.sleep(0.3)
        
        # Try to extract TOC from PDF (use first 10 pages for analysis)
        toc_text = "\n\n".join(extractor.pages[:min(10, len(extractor.pages))])
        
        logger.info(f"Attempting to parse TOC from first {min(10, len(extractor.pages))} pages")
        
        try:
            # Use AI client to parse TOC
            if extractor.ai_client:
                toc_entries_data = extractor.ai_client.parse_table_of_contents(toc_text)
                logger.info(f"[TOC] AI returned {len(toc_entries_data)} TOC entries")
                toc_entries = []
                skipped_count = 0
                for entry in toc_entries_data:
                    # Validate and set default for page_start
                    page_start = entry.get("page_start")
                    if page_start is None or not isinstance(page_start, int):
                        logger.warning(f"[TOC] Invalid page_start for entry {entry.get('number', 'unknown')}: {entry.get('title', 'unknown')}, skipping")
                        skipped_count += 1
                        continue
                    
                    toc_entries.append(
                        TableOfContentsEntry(
                            level=entry.get("level", 1),
                            number=entry.get("number", ""),
                            title=entry.get("title", ""),
                            page_start=page_start
                        )
                    )
                    logger.debug(f"[TOC] Added entry: {entry.get('number')} - {entry.get('title')} (page {page_start})")
                
                logger.info(f"[TOC] Successfully parsed {len(toc_entries)} TOC entries from PDF (skipped {skipped_count} invalid entries)")
                if len(toc_entries) > 0:
                    extractor.toc_entries = toc_entries
                    logger.info(f"[TOC] Sections: {[f'{e.number} - {e.title} (p.{e.page_start})' for e in toc_entries]}")
                    await send_progress("toc", 40, f"✅ Found {len(toc_entries)} sections in document")
                    await asyncio.sleep(0.3)
                else:
                    # AI returned 0 valid sections — fall back to automatic
                    raise RuntimeError(
                        f"TOC parsing returned 0 valid sections (AI data: {len(toc_entries_data)} raw, "
                        f"{skipped_count} skipped). Falling back to automatic sections."
                    )
            else:
                raise RuntimeError("AI client not available for TOC parsing")
                
        except Exception as e:
            logger.warning(f"Failed to parse TOC automatically: {e}")
            logger.info("Creating automatic sections based on pages")
            
            # Fallback: create sections for every ~20 pages
            manual_toc = []
            total_pages = len(extractor.pages)
            sections_per_doc = max(1, total_pages // 20)  # ~20 pages per section
            
            for i in range(0, total_pages, sections_per_doc):
                section_num = len(manual_toc) + 1
                manual_toc.append({
                    "level": 1,
                    "number": str(section_num),
                    "title": f"Раздел {section_num} (стр. {i+1}-{min(i+sections_per_doc, total_pages)})",
                    "page_start": i + 1,
                    "children": []
                })
            
            extractor.parse_table_of_contents(manual_toc=manual_toc)
            logger.info(f"Created {len(manual_toc)} automatic sections")
            await send_progress("toc", 40, f"✅ Created {len(manual_toc)} sections automatically")
            await asyncio.sleep(0.3)
        
        # Step 3: Extract requirements with detailed progress
        logger.info("[EXTRACT] Starting requirements extraction")
        # Get actual model name from extractor
        if extractor.ai_client and hasattr(extractor.ai_client, 'selected_model'):
            from src.openrouter_client import AVAILABLE_MODELS
            actual_model = extractor.ai_client.selected_model
            if actual_model in AVAILABLE_MODELS:
                model_display_name = AVAILABLE_MODELS[actual_model].name
            else:
                model_display_name = actual_model
        else:
            model_display_name = model
        await send_progress("extract", 45, f"🤖 Starting requirements extraction with {model_display_name}...")
        await asyncio.sleep(0.5)
        
        total_sections = len(extractor.toc_entries)
        logger.info(f"[EXTRACT] Total sections to process: {total_sections}")
        
        # Manual extraction with progress updates using AI client
        if not extractor.ai_client:
            raise RuntimeError("AI client not configured")
        
        for idx, toc_entry in enumerate(extractor.toc_entries):
            section_num = idx + 1
            base_progress = 45 + int((idx / total_sections) * 40)
            
            logger.info(f"[EXTRACT] Processing section {section_num}/{total_sections}: {toc_entry.number} {toc_entry.title}")
            
            await send_progress(
                "extract", 
                base_progress, 
                f"📝 Section {section_num}/{total_sections}: {toc_entry.number} {toc_entry.title}"
            )
            await asyncio.sleep(0.3)
            
            # Find end page
            end_page = None
            # Ensure toc_entry.page_start is valid
            if toc_entry.page_start is None or not isinstance(toc_entry.page_start, int):
                logger.error(f"Invalid page_start for TOC entry: {toc_entry.number} - {toc_entry.title}")
                continue
            
            for next_entry in extractor.toc_entries[idx+1:]:
                # Skip entries with invalid page_start
                if next_entry.page_start is None or not isinstance(next_entry.page_start, int):
                    continue
                if next_entry.page_start > toc_entry.page_start:
                    end_page = next_entry.page_start
                    break
            
            # Validate end_page before use
            if end_page is not None and not isinstance(end_page, int):
                logger.warning(f"Invalid end_page type: {type(end_page)}, setting to None")
                end_page = None
            
            # Get section text
            section_text = extractor.pdf_processor.get_section_text(
                extractor.pages,
                toc_entry.page_start,
                end_page
            )
            
            await send_progress(
                "extract",
                base_progress + 1,
                f"⚡ Sending section {section_num}/{total_sections} to AI API..."
            )
            await asyncio.sleep(0.3)
            
            logger.info(f"[EXTRACT] Calling AI API for section {section_num}/{total_sections}")
            
            # Extract requirements from text
            # Safe calculation: only subtract if end_page is a valid integer
            page_range = f"{toc_entry.page_start}-{end_page - 1 if (end_page is not None and isinstance(end_page, int)) else 'end'}"
            requirements = extractor.ai_client.extract_requirements(
                section_number=toc_entry.number,
                section_title=toc_entry.title,
                page_range=page_range,
                section_text=section_text
            )
            
            # Assign accurate page numbers using text search
            from src.page_finder import assign_page_numbers_to_requirements
            assign_page_numbers_to_requirements(
                requirements=requirements,
                pages=extractor.pages,
                page_start=toc_entry.page_start,
                page_end=end_page,
                fallback_page=toc_entry.page_start
            )
            
            # Set section and source type
            for req in requirements:
                req.section_number = toc_entry.number
                req.source_type = "text"
            
            # Extract requirements from images in this section (ONCE per section, not per requirement!)
            image_requirements = []
            if hasattr(extractor, 'page_image_metadata') and extractor.page_image_metadata:
                # Check if we have images for pages in this section
                # Safe range: only use end_page if it's a valid integer
                range_end = end_page if (end_page is not None and isinstance(end_page, int)) else len(extractor.pages) + 1
                section_pages = list(range(toc_entry.page_start, range_end))
                logger.debug(f"[EXTRACT] Section {section_num}: checking pages {section_pages} for images")
                logger.debug(f"[EXTRACT] Available image pages: {sorted(extractor.page_image_metadata.keys())}")
                section_images = []
                for page_num in section_pages:
                    if page_num in extractor.page_image_metadata:
                        imgs = extractor.page_image_metadata[page_num]
                        logger.debug(f"[EXTRACT] Found {len(imgs)} images on page {page_num}")
                        section_images.extend(imgs)
                    else:
                        logger.debug(f"[EXTRACT] No images on page {page_num}")
                
                if section_images:
                    logger.info(f"[EXTRACT] Found {len(section_images)} images in section {section_num}/{total_sections}")
                    await send_progress(
                        "extract",
                        base_progress + 1,
                        f"🖼️ Processing {len(section_images)} images in section {section_num}/{total_sections}..."
                    )
                    
                    # Use OpenRouter client if available for image extraction
                    if hasattr(extractor, 'ai_client') and extractor.ai_client:
                        if hasattr(extractor.ai_client, 'extract_requirements_from_image'):
                            logger.info(f"[EXTRACT] Processing {len(section_images)} images separately from text")
                            for idx, img_meta in enumerate(section_images, 1):
                                image_path = Path(img_meta["path"])
                                logger.info(f"[EXTRACT] Image {idx}/{len(section_images)}: {image_path.name} (page {img_meta['page_number']}, section {toc_entry.number})")
                                
                                if image_path.exists():
                                    logger.debug(f"[EXTRACT] Image file exists: {image_path.absolute()}")
                                    logger.debug(f"[EXTRACT] Image metadata: {img_meta}")
                                    
                                    # Extract requirements from this image separately
                                    img_reqs = extractor.ai_client.extract_requirements_from_image(
                                        image_path=image_path,
                                        page_number=img_meta["page_number"],
                                        section_number=toc_entry.number,
                                        section_title=toc_entry.title
                                    )
                                    
                                    logger.info(f"[EXTRACT] Image {idx}/{len(section_images)}: Got {len(img_reqs)} requirements from AI")
                                    if img_reqs:
                                        logger.debug(f"[EXTRACT] Image requirements IDs: {[req.id for req in img_reqs]}")
                                    else:
                                        logger.warning(f"[EXTRACT] Image {idx}/{len(section_images)}: No requirements returned from AI for {image_path.name}")
                                    
                                    image_requirements.extend(img_reqs)
                                else:
                                    logger.warning(f"[EXTRACT] Image file not found: {image_path.absolute()}")
                        else:
                            logger.warning("[EXTRACT] Image extraction skipped - client doesn't support images (no extract_requirements_from_image method)")
                    else:
                        logger.warning("[EXTRACT] Image extraction skipped - AI client not available")
                else:
                    logger.debug(f"[EXTRACT] No images found for section {section_num} (pages {toc_entry.page_start}-{range_end-1})")
            else:
                logger.debug(f"[EXTRACT] No page_image_metadata available for section {section_num}")
            
            # Combine text and image requirements
            all_requirements = requirements + image_requirements
            
            # Create section and add to registry
            from src.models import Section
            # Safe calculation: only subtract if end_page is a valid integer
            page_end_value = None
            if end_page is not None and isinstance(end_page, int):
                page_end_value = end_page - 1
            
            section = Section(
                number=toc_entry.number,
                title=toc_entry.title,
                page_start=toc_entry.page_start,
                page_end=page_end_value,
                raw_text=section_text,
                requirements=all_requirements
            )
            
            # Add image metadata to section
            if hasattr(extractor, 'page_image_metadata'):
                # Safe range: only use end_page if it's a valid integer
                range_end = end_page if (end_page is not None and isinstance(end_page, int)) else len(extractor.pages) + 1
                for page_num in range(toc_entry.page_start, range_end):
                    if page_num in extractor.page_image_metadata:
                        section.images.extend(extractor.page_image_metadata[page_num])
            
            extractor.registry.add_section(section)
            
            # Save section and requirements to database
            if db_document:
                try:
                    db = next(get_db())
                    # Create section in database
                    db_section = crud.create_section(
                        db=db,
                        document_id=db_document.id,
                        section_number=toc_entry.number,
                        title=toc_entry.title,
                        page_start=toc_entry.page_start,
                        page_end=page_end_value,
                    )
                    
                    # Save all requirements to database
                    for req in all_requirements:
                        crud.create_requirement(
                            db=db,
                            document_id=db_document.id,
                            requirement_id=req.id,
                            text=req.text,
                            ai_suggested=req.text,  # Original AI text
                            section_id=db_section.id,
                            type=req.type,
                            priority=req.priority,
                            page_number=req.source_page or req.page_number,
                            bbox=None,  # Can be added later if needed
                        )
                    
                    logger.debug(f"[DB] Saved section {section_num} with {len(all_requirements)} requirements to database")
                except Exception as db_error:
                    print(f"[DB] FAILED to save section {section_num}: {db_error}")
                    logger.warning(f"[DB] Failed to save section {section_num} to database: {db_error}")
            
            req_count_text = len(requirements)
            req_count_image = len(image_requirements)
            req_count_total = len(all_requirements)
            
            await send_progress(
                "extract",
                base_progress + 2,
                f"✅ Section {section_num}/{total_sections}: {req_count_text} text + {req_count_image} image = {req_count_total} requirements"
            )
            await asyncio.sleep(0.3)
            
            logger.info(f"[EXTRACT] Section {section_num}/{total_sections} complete: {req_count_text} text + {req_count_image} image = {req_count_total} requirements")
        
        logger.info(f"[EXTRACT] All sections complete! Total requirements: {extractor.registry.total_requirements}")
        await send_progress("extract", 85, f"🎉 Requirements extraction complete! Total: {extractor.registry.total_requirements}")
        await asyncio.sleep(0.5)
        
        # Update document status and save coverage metrics to database
        if db_document:
            try:
                db = next(get_db())
                # Update document status and total pages
                crud.update_document_status(
                    db=db,
                    document_id=db_document.id,
                    status="processing",  # Will be updated to "completed" later
                    total_pages=len(extractor.pages),
                )
                
                # Calculate and save coverage metrics
                # Find which pages actually have requirements
                pages_with_requirements = set()
                for section in extractor.registry.sections:
                    for req in section.requirements:
                        # Use page_number if available, fallback to source_page
                        page = req.page_number or req.source_page
                        if page:
                            pages_with_requirements.add(page)
                
                logger.info(f"[METRICS DEBUG] Total requirements: {extractor.registry.total_requirements}")
                logger.info(f"[METRICS DEBUG] Sections: {len(extractor.registry.sections)}")
                for i, section in enumerate(extractor.registry.sections[:3]):  # Log first 3 sections
                    logger.info(f"[METRICS DEBUG] Section {i+1}: {len(section.requirements)} requirements")
                    for j, req in enumerate(section.requirements[:3]):  # Log first 3 reqs per section
                        logger.info(f"[METRICS DEBUG]   Req {j+1}: page_number={req.page_number}, source_page={req.source_page}")
                
                # Calculate skipped pages (pages without any requirements)
                all_pages = set(range(1, len(extractor.pages) + 1))
                skipped_pages = sorted(list(all_pages - pages_with_requirements))
                processed_pages = len(pages_with_requirements)
                
                logger.info(f"[METRICS] Total pages: {len(extractor.pages)}, "
                           f"Processed: {processed_pages}, "
                           f"Skipped: {len(skipped_pages)} pages: {skipped_pages[:10]}...")
                
                # Count requirements by type
                requirements_by_type = {}
                for section in extractor.registry.sections:
                    for req in section.requirements:
                        req_type = req.type.value if hasattr(req.type, 'value') else (req.type if req.type else "Other")
                        requirements_by_type[req_type] = requirements_by_type.get(req_type, 0) + 1
                
                crud.create_or_update_coverage_metrics(
                    db=db,
                    document_id=db_document.id,
                    total_pages=len(extractor.pages),
                    processed_pages=processed_pages,
                    skipped_pages=skipped_pages,
                    requirements_count=extractor.registry.total_requirements,
                    requirements_by_type=requirements_by_type,
                )
                
                logger.info(f"[DB] Updated document {db_document.id} status and metrics")
            except Exception as db_error:
                print(f"[DB] FAILED to update metrics: {db_error}")
                logger.warning(f"[DB] Failed to update document metrics: {db_error}")
        
        # Step 4: Save results
        await send_progress("save", 90, "Saving results...")
        registry_path = extractor.save_registry()
        
        logger.info(f"Registry saved to: {registry_path}")
        logger.info(f"Registry path absolute: {registry_path.absolute()}")
        
        # Get usage report
        usage_report = get_usage_report()
        usage_report_path = output_dir / "usage_report.txt"
        
        # Determine provider name for report
        provider_name = "OpenRouter" if config.provider == "openrouter" else "DeepSeek API"
        usage_report.save_to_file(usage_report_path, provider_name=provider_name)
        
        logger.info(f"Usage report saved to: {usage_report_path}")
        
        await send_progress("save", 95, "Generating reports...")
        
        # Step 5: Generate Word document if requested
        word_path = None
        if generate_word:
            await send_progress("word", 97, "Generating Word document...")
            word_path = await generate_word_document(
                extractor,
                usage_report,
                output_dir
            )
        
        # Calculate processing time
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        await send_progress("complete", 100, "Processing complete!")
        
        # Update document status to completed
        if db_document:
            try:
                db = next(get_db())
                crud.update_document_status(
                    db=db,
                    document_id=db_document.id,
                    status="completed",
                )
                logger.info(f"[DB] Document {db_document.id} marked as completed")
            except Exception as db_error:
                logger.warning(f"[DB] Failed to update document status: {db_error}")
        
        # Prepare response with proper path handling
        cwd = Path.cwd()
        
        def get_relative_path(path: Path) -> str:
            """Safely get relative path."""
            try:
                # Try to make absolute paths relative
                if not path.is_absolute():
                    path = path.absolute()
                return str(path.relative_to(cwd))
            except (ValueError, Exception):
                # If relative_to fails, return the path as-is
                return str(path).replace('\\', '/')
        
        files = {
            "registry": get_relative_path(registry_path),
            "usage_report": get_relative_path(usage_report_path),
        }
        
        if word_path:
            files["word_document"] = get_relative_path(word_path)
        
        result = ExtractionResult(
            success=True,
            message="Requirements extracted successfully",
            requirements_count=extractor.registry.total_requirements,
            sections_count=len(extractor.registry.sections),
            total_tokens=usage_report.total_tokens,
            total_cost=usage_report.total_cost,
            processing_time=processing_time,
            files=files,
            model_used=model,
            document_id=db_document.id if db_document else None
        )
        
        logger.info(f"Extraction completed: {result.requirements_count} requirements")
        logger.info(f"Files prepared for download:")
        for file_type, file_path in files.items():
            logger.info(f"  {file_type}: {file_path}")
        
        # Remove WebSocket handlers
        api_logger.removeHandler(ws_handler)
        openrouter_logger.removeHandler(ws_handler)
        extractor_logger.removeHandler(ws_handler)
        pdf_logger.removeHandler(ws_handler)
        
        # Return result
        result_dict = result.model_dump()
        print(f"[RESPONSE] document_id={result_dict.get('document_id')}, model_used={result_dict.get('model_used')}")
        
        return result_dict
        
    except Exception as e:
        logger.error(f"Extraction failed: {e}", exc_info=True)
        await send_progress("error", 0, f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Always cleanup temporary directory
        if output_dir and output_dir.exists():
            try:
                import shutil
                shutil.rmtree(output_dir)
                logger.info(f"[CLEANUP] Removed temporary directory: {output_dir}")
            except Exception as cleanup_error:
                logger.warning(f"[CLEANUP] Failed to remove temporary directory: {cleanup_error}")


async def generate_word_document(
    extractor: RequirementsExtractor,
    usage_report,
    output_dir: Path
) -> Path:
    """
    Generate Word document with requirements and usage report.
    
    Args:
        extractor: Requirements extractor instance
        usage_report: Usage report instance
        output_dir: Output directory
    
    Returns:
        Path to generated Word document
    """
    try:
        from docx import Document
        from docx.shared import Inches, Pt, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        
        doc = Document()
        
        # Add title
        title = doc.add_heading('Реестр требований', 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Add metadata
        doc.add_paragraph(f"Дата создания: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
        doc.add_paragraph(f"Всего требований: {extractor.registry.total_requirements}")
        doc.add_paragraph(f"Всего разделов: {len(extractor.registry.sections)}")
        doc.add_paragraph("")
        
        # Add requirements by section
        doc.add_heading('Требования по разделам', 1)
        
        for section in extractor.registry.sections:
            doc.add_heading(section.full_title, 2)
            doc.add_paragraph(f"Страницы: {section.page_range}")
            doc.add_paragraph(f"Требований: {len(section.requirements)}")
            doc.add_paragraph("")
            
            if section.requirements:
                # Create table
                table = doc.add_table(rows=1, cols=4)
                table.style = 'Light Grid Accent 1'
                
                # Header row
                header_cells = table.rows[0].cells
                header_cells[0].text = 'ID'
                header_cells[1].text = 'Требование'
                header_cells[2].text = 'Тип'
                header_cells[3].text = 'Приоритет'
                
                # Add requirements
                for req in section.requirements:
                    row_cells = table.add_row().cells
                    row_cells[0].text = req.id
                    row_cells[1].text = req.text
                    row_cells[2].text = req.type.value if hasattr(req.type, 'value') else str(req.type or '')
                    row_cells[3].text = req.priority.value if hasattr(req.priority, 'value') else str(req.priority or '')
                
                doc.add_paragraph("")
        
        # Add usage report
        doc.add_page_break()
        doc.add_heading('Отчет о затратах', 1)
        
        doc.add_paragraph(f"Всего вызовов API: {usage_report.calls_count}")
        doc.add_paragraph(f"Входных токенов: {usage_report.total_input_tokens:,}")
        doc.add_paragraph(f"Выходных токенов: {usage_report.total_output_tokens:,}")
        doc.add_paragraph(f"Всего токенов: {usage_report.total_tokens:,}")
        doc.add_paragraph("")
        
        # Cost with formatting
        cost_para = doc.add_paragraph()
        cost_run = cost_para.add_run(f"Общая стоимость: ${usage_report.total_cost:.4f} USD")
        cost_run.bold = True
        cost_run.font.size = Pt(14)
        cost_run.font.color.rgb = RGBColor(0, 128, 0)
        
        doc.add_paragraph("")
        
        # Breakdown by section
        doc.add_heading('Детализация по разделам', 2)
        
        stats = usage_report.get_stats_by_section()
        table = doc.add_table(rows=1, cols=4)
        table.style = 'Light Grid Accent 1'
        
        header_cells = table.rows[0].cells
        header_cells[0].text = 'Раздел'
        header_cells[1].text = 'Вызовов'
        header_cells[2].text = 'Токенов'
        header_cells[3].text = 'Стоимость'
        
        for section_name, section_stats in sorted(stats.items()):
            row_cells = table.add_row().cells
            row_cells[0].text = section_name
            row_cells[1].text = str(section_stats['calls'])
            row_cells[2].text = f"{section_stats['input_tokens'] + section_stats['output_tokens']:,}"
            row_cells[3].text = f"${section_stats['cost']:.4f}"
        
        # Save document
        word_path = output_dir / "requirements_report.docx"
        doc.save(word_path)
        
        logger.info(f"Word document generated: {word_path}")
        return word_path
        
    except ImportError:
        logger.warning("python-docx not installed, skipping Word generation")
        return None


# ========== Database API Endpoints ==========

@app.get("/api/documents")
async def get_all_documents(
    skip: int = 0,
    limit: int = 100,
    project_id: Optional[int] = Query(None, description="Filter by project"),
):
    """Get all documents with pagination. Optionally filter by project."""
    try:
        db = next(get_db())
        if project_id:
            documents = crud.get_documents_by_project(db, project_id)
        else:
            documents = crud.get_all_documents(db, skip=skip, limit=limit)
        result = []
        for doc in documents:
            result.append({
                "id": doc.id,
                "project_id": doc.project_id,
                "filename": doc.filename,
                "status": doc.status,
                "total_pages": doc.total_pages,
                "model_used": doc.model_used,
                "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
                "processed_at": doc.processed_at.isoformat() if doc.processed_at else None,
            })
        return {
            "documents": result,
            "total": len(result),
        }
    except Exception as e:
        logger.error(f"Failed to get documents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/documents/{document_id}")
async def get_document(document_id: int):
    """Get document by ID with full metadata.
    
    Args:
        document_id: Document ID
    
    Returns:
        Document with metadata
    """
    try:
        db = next(get_db())
        document = crud.get_document(db, document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return {
            "id": document.id,
            "project_id": document.project_id,
            "filename": document.filename,
            "file_path": document.file_path,
            "status": document.status,
            "total_pages": document.total_pages,
            "model_used": document.model_used,
            "uploaded_at": document.uploaded_at.isoformat() if document.uploaded_at else None,
            "processed_at": document.processed_at.isoformat() if document.processed_at else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/documents/{document_id}/requirements")
async def get_requirements(
    document_id: int,
    status: Optional[str] = None,
    type: Optional[str] = None,
    skip: int = 0,
    limit: int = 1000,
):
    """Get requirements for a document with optional filters.
    
    Args:
        document_id: Document ID
        status: Filter by status (pending, accepted, rejected, modified)
        type: Filter by type (Technical, Functional, etc.)
        skip: Number of records to skip
        limit: Maximum number of records to return
    
    Returns:
        List of requirements with metadata
    """
    try:
        db = next(get_db())
        
        # Verify document exists
        document = crud.get_document(db, document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Convert type string to enum if provided
        req_type = None
        if type:
            try:
                req_type = RequirementType(type)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid requirement type: {type}")
        
        requirements = crud.get_requirements_by_document(
            db=db,
            document_id=document_id,
            status=status,
            type=req_type,
            skip=skip,
            limit=limit,
        )
        
        return {
            "requirements": [
                {
                    "id": req.id,
                    "requirement_id": req.requirement_id,
                    "text": req.text,
                    "type": req.type,  # Already a string in DB
                    "priority": req.priority,  # Already a string in DB
                    "page_number": req.page_number,
                    "status": req.status,
                    "ai_suggested": req.ai_suggested,
                    "human_edited": req.human_edited,
                    "edit_reason": req.edit_reason,
                    "edited_at": req.edited_at.isoformat() if req.edited_at else None,
                    "section_id": req.section_id,
                    "created_at": req.created_at.isoformat() if req.created_at else None,
                }
                for req in requirements
            ],
            "total": len(requirements),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get requirements for document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/documents/{document_id}/metrics")
async def get_metrics(document_id: int):
    """Get coverage metrics for a document.
    
    Args:
        document_id: Document ID
    
    Returns:
        Coverage metrics with statistics
    """
    try:
        db = next(get_db())
        
        # Verify document exists
        document = crud.get_document(db, document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        metrics = crud.get_coverage_metrics(db, document_id)
        if not metrics:
            raise HTTPException(status_code=404, detail="Metrics not found for this document")
        
        return {
            "document_id": metrics.document_id,
            "total_pages": metrics.total_pages,
            "processed_pages": metrics.processed_pages,
            "skipped_pages": metrics.skipped_pages or [],
            "coverage_percent": metrics.coverage_percent,
            "requirements_count": metrics.requirements_count,
            "requirements_by_type": metrics.requirements_by_type or {},
            "calculated_at": metrics.calculated_at.isoformat() if metrics.calculated_at else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get metrics for document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/requirements/{requirement_id}")
async def get_requirement(requirement_id: int):
    """Get requirement by ID with full details.
    
    Args:
        requirement_id: Requirement ID
    
    Returns:
        Requirement with full metadata including audit trail
    """
    try:
        db = next(get_db())
        requirement = crud.get_requirement(db, requirement_id)
        if not requirement:
            raise HTTPException(status_code=404, detail="Requirement not found")
        
        return {
            "id": requirement.id,
            "requirement_id": requirement.requirement_id,
            "text": requirement.text,
            "type": requirement.type,  # Already a string
            "priority": requirement.priority,  # Already a string
            "page_number": requirement.page_number,
            "status": requirement.status,
            "ai_suggested": requirement.ai_suggested,
            "human_edited": requirement.human_edited,
            "edit_reason": requirement.edit_reason,
            "edited_by": requirement.edited_by,
            "edited_at": requirement.edited_at.isoformat() if requirement.edited_at else None,
            "document_id": requirement.document_id,
            "section_id": requirement.section_id,
            "created_at": requirement.created_at.isoformat() if requirement.created_at else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get requirement {requirement_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== Review API Endpoints ==========

@app.post("/api/requirements/{requirement_id}/accept")
async def accept_requirement_endpoint(requirement_id: int):
    """Accept a requirement (mark as accepted).
    
    Marks the requirement as accepted, meaning the AI-suggested text
    is correct and approved by human reviewer.
    
    Args:
        requirement_id: Requirement ID to accept
    
    Returns:
        Updated requirement with status 'accepted'
    """
    try:
        db = next(get_db())
        requirement = crud.accept_requirement(db, requirement_id)
        
        if not requirement:
            raise HTTPException(status_code=404, detail="Requirement not found")
        
        logger.info(f"[REVIEW] Requirement {requirement_id} accepted")
        
        return {
            "id": requirement.id,
            "requirement_id": requirement.requirement_id,
            "text": requirement.text,
            "status": requirement.status,
            "ai_suggested": requirement.ai_suggested,
            "message": "Requirement accepted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[REVIEW] Failed to accept requirement {requirement_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/requirements/{requirement_id}/reject")
async def reject_requirement_endpoint(
    requirement_id: int,
    request: Optional[RejectRequirementRequest] = None
):
    """Reject a requirement (mark as rejected).
    
    Marks the requirement as rejected, meaning it's not a valid requirement
    or the AI made an error.
    
    Args:
        requirement_id: Requirement ID to reject
        request: Optional rejection reason (can be omitted)
    
    Returns:
        Updated requirement with status 'rejected'
    """
    try:
        db = next(get_db())
        
        # Handle optional request body
        reason = request.reason if request else None
        
        requirement = crud.reject_requirement(db, requirement_id, reason=reason)
        
        if not requirement:
            raise HTTPException(status_code=404, detail="Requirement not found")
        
        logger.info(f"[REVIEW] Requirement {requirement_id} rejected (reason: {reason or 'none'})")
        
        return {
            "id": requirement.id,
            "requirement_id": requirement.requirement_id,
            "text": requirement.text,
            "status": requirement.status,
            "edit_reason": requirement.edit_reason,
            "message": "Requirement rejected successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[REVIEW] Failed to reject requirement {requirement_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/requirements/{requirement_id}/edit")
async def edit_requirement_endpoint(
    requirement_id: int,
    request: EditRequirementRequest
):
    """Edit a requirement (mark as modified).
    
    Updates the requirement text with human-edited version and marks it as modified.
    Preserves both AI-suggested and human-edited versions for audit trail.
    
    Args:
        requirement_id: Requirement ID to edit
        request: Edit request with new text and optional reason
    
    Returns:
        Updated requirement with status 'modified' and audit trail
    """
    try:
        db = next(get_db())
        requirement = crud.edit_requirement(
            db=db,
            requirement_id=requirement_id,
            edited_text=request.edited_text,
            reason=request.reason,
            edited_by=request.edited_by
        )
        
        if not requirement:
            raise HTTPException(status_code=404, detail="Requirement not found")
        
        logger.info(f"[REVIEW] Requirement {requirement_id} edited by {request.edited_by or 'unknown'}")
        
        return {
            "id": requirement.id,
            "requirement_id": requirement.requirement_id,
            "text": requirement.text,  # Current text (human-edited)
            "status": requirement.status,
            "ai_suggested": requirement.ai_suggested,  # Original AI text
            "human_edited": requirement.human_edited,  # Human-edited text
            "edit_reason": requirement.edit_reason,
            "edited_by": requirement.edited_by,
            "edited_at": requirement.edited_at.isoformat() if requirement.edited_at else None,
            "message": "Requirement edited successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[REVIEW] Failed to edit requirement {requirement_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/documents/{document_id}/pdf")
async def get_document_pdf(document_id: int):
    """Get PDF file for document viewer.
    
    Returns the original PDF file for viewing in browser.
    
    Args:
        document_id: Document ID
    
    Returns:
        FileResponse with PDF file
    
    Raises:
        HTTPException: 404 if document or file not found
    """
    try:
        db = next(get_db())
        document = crud.get_document(db, document_id)
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        file_path = Path(document.file_path)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="PDF file not found")
        
        return StreamingResponse(
            open(file_path, "rb"),
            media_type="application/pdf",
            headers={
                "Content-Disposition": "inline",
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get PDF for document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/download")
async def download_file(path: str) -> FileResponse:
    """Download generated file by path with security checks.
    
    Serves files from the data directory with security validation to prevent
    directory traversal attacks. Automatically determines correct media type
    based on file extension.
    
    Args:
        path: Relative or absolute path to the file to download.
    
    Returns:
        FileResponse with appropriate media type and filename.
        
    Raises:
        HTTPException: 
            - 403 if path is outside data directory (security violation)
            - 404 if file doesn't exist
            - 500 for other errors
    """
    try:
        # Ensure the path is within our data directory for security
        file_path = Path(path).absolute()
        base_path = Path.cwd() / "data"
        
        # Security check: ensure file is in data directory
        if not str(file_path).startswith(str(base_path)):
            raise HTTPException(status_code=403, detail="Access denied")
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        # Determine media type based on file extension
        media_type = "application/octet-stream"
        if file_path.suffix == ".json":
            media_type = "application/json"
        elif file_path.suffix == ".txt":
            media_type = "text/plain"
        elif file_path.suffix == ".docx":
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        
        return FileResponse(
            path=file_path,
            filename=file_path.name,
            media_type=media_type
        )
    except Exception as e:
        logger.error(f"Download error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# PROJECT ENDPOINTS
# ============================================================================

@app.get("/api/projects")
async def get_projects(db=Depends(get_db)):
    """Get all projects."""
    projects = crud.get_all_projects(db)
    result = []
    for p in projects:
        doc_count = len(p.documents) if p.documents else 0
        req_count = sum(len(d.requirements) for d in p.documents) if p.documents else 0
        result.append({
            "id": p.id,
            "name": p.name,
            "code": p.code,
            "description": p.description,
            "status": p.status,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            "documents_count": doc_count,
            "requirements_count": req_count,
        })
    return {"projects": result}


@app.post("/api/projects")
async def create_project(
    name: str = Form(...),
    code: str = Form(None),
    description: str = Form(None),
    db=Depends(get_db)
):
    """Create a new project."""
    if code:
        existing = crud.get_project_by_code(db, code)
        if existing:
            raise HTTPException(status_code=400, detail=f"Project with code '{code}' already exists")
    
    project = crud.create_project(db, name=name, code=code, description=description)
    return {
        "id": project.id,
        "name": project.name,
        "code": project.code,
        "description": project.description,
        "status": project.status,
        "created_at": project.created_at.isoformat() if project.created_at else None,
    }


@app.get("/api/projects/{project_id}")
async def get_project(project_id: int, db=Depends(get_db)):
    """Get project details with documents."""
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    documents = crud.get_documents_by_project(db, project_id)
    docs_data = []
    for doc in documents:
        req_count = len(doc.requirements) if doc.requirements else 0
        docs_data.append({
            "id": doc.id,
            "filename": doc.filename,
            "status": doc.status,
            "total_pages": doc.total_pages,
            "model_used": doc.model_used,
            "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
            "processed_at": doc.processed_at.isoformat() if doc.processed_at else None,
            "requirements_count": req_count,
        })
    
    return {
        "id": project.id,
        "name": project.name,
        "code": project.code,
        "description": project.description,
        "status": project.status,
        "created_at": project.created_at.isoformat() if project.created_at else None,
        "updated_at": project.updated_at.isoformat() if project.updated_at else None,
        "documents": docs_data,
    }


@app.put("/api/projects/{project_id}")
async def update_project(
    project_id: int,
    name: str = Form(None),
    code: str = Form(None),
    description: str = Form(None),
    status: str = Form(None),
    db=Depends(get_db)
):
    """Update a project."""
    project = crud.update_project(db, project_id, name=name, code=code, description=description, status=status)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return {
        "id": project.id,
        "name": project.name,
        "code": project.code,
        "description": project.description,
        "status": project.status,
    }


@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: int, db=Depends(get_db)):
    """Delete a project and all its documents."""
    success = crud.delete_project(db, project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"ok": True}


# ============================================================================
# EXPORT ENDPOINTS
# ============================================================================
# Export Endpoints (Generate files from DB)
# ============================================================================

@app.get("/api/documents/{document_id}/export/word")
async def export_word(
    document_id: int,
    db = Depends(get_db)
):
    """
    Generate Word document from database data on-the-fly.
    
    Args:
        document_id: Document ID
        
    Returns:
        FileResponse with Word document
    """
    try:
        import tempfile
        from docx import Document as DocxDocument
        from docx.shared import Pt, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        
        logger.info(f"[EXPORT] Generating Word document for document {document_id}")
        
        # Fetch data from DB
        document = crud.get_document(db, document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        sections = crud.get_sections_by_document(db, document_id)
        all_requirements = crud.get_requirements_by_document(db, document_id)
        metrics = crud.get_coverage_metrics(db, document_id)
        
        # Create Word document
        doc = DocxDocument()
        
        # Title
        title = doc.add_heading('Реестр требований', 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Metadata
        doc.add_paragraph(f"Документ: {document.filename}")
        doc.add_paragraph(f"Дата обработки: {document.uploaded_at.strftime('%d.%m.%Y %H:%M')}")
        doc.add_paragraph(f"Всего требований: {len(all_requirements)}")
        doc.add_paragraph(f"Всего разделов: {len(sections)}")
        doc.add_paragraph("")
        
        # Requirements by section
        doc.add_heading('Требования по разделам', 1)
        
        for section in sections:
            # Get requirements for this section
            section_requirements = [r for r in all_requirements if r.section_id == section.id]
            
            doc.add_heading(section.title, 2)
            doc.add_paragraph(f"Страницы: {section.page_start} - {section.page_end}")
            doc.add_paragraph(f"Требований: {len(section_requirements)}")
            doc.add_paragraph("")
            
            if section_requirements:
                # Create table
                table = doc.add_table(rows=1, cols=5)
                table.style = 'Light Grid Accent 1'
                
                # Header
                header_cells = table.rows[0].cells
                header_cells[0].text = 'ID'
                header_cells[1].text = 'Требование'
                header_cells[2].text = 'Тип'
                header_cells[3].text = 'Приоритет'
                header_cells[4].text = 'Страница'
                
                # Add requirements
                for req in section_requirements:
                    row_cells = table.add_row().cells
                    row_cells[0].text = req.requirement_id or ''
                    row_cells[1].text = req.text or ''
                    row_cells[2].text = req.type or ''
                    row_cells[3].text = req.priority or ''
                    row_cells[4].text = str(req.page_number or '')
                
                doc.add_paragraph("")
        
        # Coverage metrics
        if metrics:
            doc.add_page_break()
            doc.add_heading('Метрики покрытия', 1)
            
            doc.add_paragraph(f"Всего страниц: {metrics.total_pages}")
            doc.add_paragraph(f"Обработано страниц: {metrics.processed_pages}")
            doc.add_paragraph(f"Пропущено страниц: {len(metrics.skipped_pages) if metrics.skipped_pages else 0}")
            doc.add_paragraph(f"Покрытие: {metrics.coverage_percent:.1f}%")
            doc.add_paragraph("")
            
            # Requirements by type
            doc.add_heading('Требования по типам', 2)
            if metrics.requirements_by_type:
                table = doc.add_table(rows=1, cols=2)
                table.style = 'Light Grid Accent 1'
                
                header_cells = table.rows[0].cells
                header_cells[0].text = 'Тип'
                header_cells[1].text = 'Количество'
                
                for req_type, count in metrics.requirements_by_type.items():
                    row_cells = table.add_row().cells
                    row_cells[0].text = req_type
                    row_cells[1].text = str(count)
        
        # Save to temporary file
        temp_file = tempfile.NamedTemporaryFile(mode='wb', suffix='.docx', delete=False)
        doc.save(temp_file.name)
        temp_file.close()
        
        logger.info(f"[EXPORT] Word document generated: {temp_file.name}")
        
        # Return file (will be cleaned up by OS later)
        return FileResponse(
            temp_file.name,
            media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            filename=f"{document.filename}_requirements.docx"
        )
        
    except Exception as e:
        logger.error(f"[EXPORT] Word generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/documents/{document_id}/export/json")
async def export_json(
    document_id: int,
    db = Depends(get_db)
):
    """
    Generate JSON registry from database data on-the-fly.
    
    Args:
        document_id: Document ID
        
    Returns:
        JSON response with requirements registry
    """
    try:
        import tempfile
        
        logger.info(f"[EXPORT] Generating JSON registry for document {document_id}")
        
        # Fetch data from DB
        document = crud.get_document(db, document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        sections = crud.get_sections_by_document(db, document_id)
        all_requirements = crud.get_requirements_by_document(db, document_id)
        
        # Build registry structure
        registry = {
            "document": {
                "filename": document.filename,
                "uploaded_at": document.uploaded_at.isoformat(),
                "total_requirements": len(all_requirements),
                "total_sections": len(sections)
            },
            "sections": []
        }
        
        for section in sections:
            section_requirements = [r for r in all_requirements if r.section_id == section.id]
            
            section_data = {
                "number": section.section_number,
                "title": section.title,
                "page_start": section.page_start,
                "page_end": section.page_end,
                "requirements": [
                    {
                        "id": req.requirement_id,
                        "text": req.text,
                        "type": req.type,
                        "priority": req.priority,
                        "page_number": req.page_number,
                        "status": req.status
                    }
                    for req in section_requirements
                ]
            }
            registry["sections"].append(section_data)
        
        # Save to temporary file
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8')
        json.dump(registry, temp_file, ensure_ascii=False, indent=2)
        temp_file.close()
        
        logger.info(f"[EXPORT] JSON registry generated: {temp_file.name}")
        
        # Return file
        return FileResponse(
            temp_file.name,
            media_type='application/json',
            filename=f"{document.filename}_registry.json"
        )
        
    except Exception as e:
        logger.error(f"[EXPORT] JSON generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/documents/{document_id}/export/txt")
async def export_txt(
    document_id: int,
    db = Depends(get_db)
):
    """
    Generate TXT usage report from database data on-the-fly.
    
    Args:
        document_id: Document ID
        
    Returns:
        TXT file with processing statistics
    """
    try:
        import tempfile
        
        logger.info(f"[EXPORT] Generating TXT report for document {document_id}")
        
        # Fetch data from DB
        document = crud.get_document(db, document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        sections = crud.get_sections_by_document(db, document_id)
        all_requirements = crud.get_requirements_by_document(db, document_id)
        metrics = crud.get_coverage_metrics(db, document_id)
        
        # Build report
        lines = [
            "=" * 80,
            "ОТЧЕТ О ОБРАБОТКЕ ДОКУМЕНТА",
            "=" * 80,
            "",
            f"Документ: {document.filename}",
            f"Дата обработки: {document.uploaded_at.strftime('%d.%m.%Y %H:%M')}",
            f"Модель: {document.model_used or 'N/A'}",
            "",
            "=" * 80,
            "СТАТИСТИКА",
            "=" * 80,
            "",
            f"Всего требований: {len(all_requirements)}",
            f"Всего разделов: {len(sections)}",
            ""
        ]
        
        if metrics:
            lines.extend([
                f"Всего страниц: {metrics.total_pages}",
                f"Обработано страниц: {metrics.processed_pages}",
                f"Пропущено страниц: {len(metrics.skipped_pages) if metrics.skipped_pages else 0}",
                f"Покрытие: {metrics.coverage_percent:.1f}%",
                ""
            ])
        
        # Requirements by type
        if metrics and metrics.requirements_by_type:
            lines.extend([
                "=" * 80,
                "ТРЕБОВАНИЯ ПО ТИПАМ",
                "=" * 80,
                ""
            ])
            for req_type, count in metrics.requirements_by_type.items():
                lines.append(f"{req_type}: {count}")
            lines.append("")
        
        # Sections
        lines.extend([
            "=" * 80,
            "РАЗДЕЛЫ",
            "=" * 80,
            ""
        ])
        
        for section in sections:
            section_requirements = [r for r in all_requirements if r.section_id == section.id]
            lines.append(f"{section.section_number}. {section.title}")
            lines.append(f"  Страницы: {section.page_start} - {section.page_end}")
            lines.append(f"  Требований: {len(section_requirements)}")
            lines.append("")
        
        lines.append("=" * 80)
        
        # Save to temporary file
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
        temp_file.write('\n'.join(lines))
        temp_file.close()
        
        logger.info(f"[EXPORT] TXT report generated: {temp_file.name}")
        
        # Return file
        return FileResponse(
            temp_file.name,
            media_type='text/plain',
            filename=f"{document.filename}_report.txt"
        )
        
    except Exception as e:
        logger.error(f"[EXPORT] TXT generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    
    # Configure uvicorn to not shutdown on first request
    config = uvicorn.Config(
        app, 
        host="0.0.0.0", 
        port=8000, 
        log_level="info",
        timeout_keep_alive=300,  # Keep connections alive for 5 minutes
        timeout_graceful_shutdown=30  # Allow 30 seconds for graceful shutdown
    )
    server = uvicorn.Server(config)
    server.run()
