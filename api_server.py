"""FastAPI backend server for PDF requirements extraction.

This module provides a RESTful API and WebSocket interface for extracting
requirements from PDF technical specifications using DeepSeek AI.

Features:
    - File upload and processing
    - Real-time progress updates via WebSocket
    - Requirements extraction with AI
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
from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

# Local imports
from src.config import ApplicationConfig
from src.extractor import RequirementsExtractor
from src.logger import setup_logger
from src.models import TableOfContentsEntry
from src.usage_tracker import get_usage_report, reset_usage_report

# Setup logging
setup_logger(log_file=Path("logs/api.log"), level="INFO")
logger = logging.getLogger("api")

# Create FastAPI app
app = FastAPI(
    title="PDF Requirements Extractor API",
    description="Extract requirements from technical specifications using AI",
    version="2.0.0"
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

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
    """
    
    success: bool = Field(..., description="Success status")
    message: str = Field(..., description="Result message")
    requirements_count: int = Field(..., ge=0, description="Number of requirements")
    sections_count: int = Field(..., ge=0, description="Number of sections")
    total_tokens: int = Field(..., ge=0, description="Total tokens used")
    total_cost: float = Field(..., ge=0, description="Total cost in USD")
    processing_time: float = Field(..., ge=0, description="Processing time in seconds")
    files: Dict[str, str] = Field(..., description="Generated file paths")


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
    generate_word: bool = True
) -> ExtractionResult:
    """Extract requirements from uploaded PDF file using DeepSeek AI.
    
    This endpoint:
    1. Validates and saves the uploaded PDF
    2. Extracts text from all pages
    3. Parses table of contents (or creates automatic sections)
    4. Extracts requirements using DeepSeek AI
    5. Generates JSON registry and optional Word document
    6. Calculates token usage and costs
    
    Progress updates are sent via WebSocket in real-time.
    
    Args:
        file: PDF file to process (technical specification document).
        generate_word: Whether to generate Word document with results.
    
    Returns:
        ExtractionResult containing success status, statistics, and file paths.
        
    Raises:
        HTTPException: If file is invalid, processing fails, or API errors occur.
    """
    start_time = datetime.now()
    
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
        await send_progress("upload", 10, "File uploaded successfully")
        
        # Create output directory for this session
        output_dir = Path(f"data/output/{timestamp}")
        output_dir.mkdir(parents=True, exist_ok=True)
        
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
        
        deepseek_logger = logging.getLogger("src.deepseek_client")
        deepseek_logger.addHandler(ws_handler)
        
        extractor_logger = logging.getLogger("src.extractor")
        extractor_logger.addHandler(ws_handler)
        
        pdf_logger = logging.getLogger("src.pdf_processor")
        pdf_logger.addHandler(ws_handler)
        
        await send_progress("init", 15, "Initializing extractor")
        logger.info("[INIT] Creating configuration and extractor")
        await asyncio.sleep(0.3)
        
        # Create configuration
        config = ApplicationConfig()
        config.pdf_path = pdf_path
        config.output_dir = output_dir
        config.image_dir = output_dir / "images"
        
        # Create extractor
        extractor = RequirementsExtractor(config)
        
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
            return extractor.pdf_processor.extract_pages(
                pdf_path,
                config.image_dir,
                progress_callback=sync_progress
            )
        
        # Run in executor to allow async operations to continue
        logger.info("[PDF] Running extraction in thread pool")
        with ThreadPoolExecutor() as executor:
            extractor.pages = await loop.run_in_executor(executor, extract_pdf_sync)
        
        logger.info(f"[PDF] Extraction complete: {len(extractor.pages)} pages")
        await send_progress("pdf", 30, f"✅ Extracted {len(extractor.pages)} pages successfully")
        await asyncio.sleep(0.5)
        
        # Step 2: Parse TOC from first pages or use AI
        logger.info("[TOC] Starting table of contents analysis")
        await send_progress("toc", 35, "📚 Analyzing document structure...")
        await asyncio.sleep(0.3)
        
        # Try to extract TOC from PDF (use first 10 pages for analysis)
        toc_text = "\n\n".join(extractor.pages[:min(10, len(extractor.pages))])
        
        logger.info(f"Attempting to parse TOC from first {min(10, len(extractor.pages))} pages")
        
        try:
            # Use DeepSeek to parse TOC
            from src.deepseek_client import DeepSeekClient
            
            with DeepSeekClient(config.deepseek) as deepseek_client:
                toc_entries = deepseek_client.parse_table_of_contents(toc_text)
                extractor.toc_entries = toc_entries
                
                logger.info(f"Successfully parsed {len(toc_entries)} TOC entries from PDF")
                await send_progress("toc", 40, f"✅ Found {len(toc_entries)} sections in document")
                await asyncio.sleep(0.3)
                
        except Exception as e:
            logger.warning(f"Failed to parse TOC automatically: {e}")
            logger.info("Creating automatic sections based on pages")
            
            # Fallback: create sections for every 10 pages
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
        await send_progress("extract", 45, "🤖 Starting requirements extraction with DeepSeek AI...")
        await asyncio.sleep(0.5)
        
        total_sections = len(extractor.toc_entries)
        logger.info(f"[EXTRACT] Total sections to process: {total_sections}")
        
        # Manual extraction with progress updates
        from src.deepseek_client import DeepSeekClient
        
        with DeepSeekClient(config.deepseek) as deepseek_client:
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
                for next_entry in extractor.toc_entries[idx+1:]:
                    if next_entry.page_start > toc_entry.page_start:
                        end_page = next_entry.page_start
                        break
                
                # Get section text
                section_text = extractor.pdf_processor.get_section_text(
                    extractor.pages,
                    toc_entry.page_start,
                    end_page
                )
                
                await send_progress(
                    "extract",
                    base_progress + 1,
                    f"⚡ Sending section {section_num}/{total_sections} to DeepSeek API..."
                )
                await asyncio.sleep(0.3)
                
                logger.info(f"[EXTRACT] Calling DeepSeek API for section {section_num}/{total_sections}")
                
                # Set current section for usage tracking
                deepseek_client.current_section = f"{toc_entry.number} {toc_entry.title}"
                
                # Extract requirements
                page_range = f"{toc_entry.page_start}-{end_page-1 if end_page else 'end'}"
                requirements = deepseek_client.extract_requirements(
                    section_number=toc_entry.number,
                    section_title=toc_entry.title,
                    page_range=page_range,
                    section_text=section_text
                )
                
                # Create section and add to registry
                from src.models import Section
                section = Section(
                    number=toc_entry.number,
                    title=toc_entry.title,
                    page_start=toc_entry.page_start,
                    page_end=end_page - 1 if end_page else None,
                    raw_text=section_text,
                    requirements=requirements
                )
                
                extractor.registry.add_section(section)
                
                await send_progress(
                    "extract",
                    base_progress + 2,
                    f"✅ Section {section_num}/{total_sections}: extracted {len(requirements)} requirements"
                )
                await asyncio.sleep(0.3)
                
                logger.info(f"[EXTRACT] Section {section_num}/{total_sections} complete: {len(requirements)} requirements")
        
        logger.info(f"[EXTRACT] All sections complete! Total requirements: {extractor.registry.total_requirements}")
        await send_progress("extract", 85, f"🎉 Requirements extraction complete! Total: {extractor.registry.total_requirements}")
        await asyncio.sleep(0.5)
        
        # Step 4: Save results
        await send_progress("save", 90, "Saving results...")
        registry_path = extractor.save_registry()
        
        logger.info(f"Registry saved to: {registry_path}")
        logger.info(f"Registry path absolute: {registry_path.absolute()}")
        
        # Get usage report
        usage_report = get_usage_report()
        usage_report_path = output_dir / "usage_report.txt"
        usage_report.save_to_file(usage_report_path)
        
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
            files=files
        )
        
        logger.info(f"Extraction completed: {result.requirements_count} requirements")
        logger.info(f"Files prepared for download:")
        for file_type, file_path in files.items():
            logger.info(f"  {file_type}: {file_path}")
        
        # Remove WebSocket handlers
        api_logger.removeHandler(ws_handler)
        deepseek_logger.removeHandler(ws_handler)
        extractor_logger.removeHandler(ws_handler)
        pdf_logger.removeHandler(ws_handler)
        
        return result
        
    except Exception as e:
        logger.error(f"Extraction failed: {e}", exc_info=True)
        await send_progress("error", 0, f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


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
                    row_cells[2].text = req.type.value
                    row_cells[3].text = req.priority.value
                
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
