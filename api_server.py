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
import os
import sys
import tempfile
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

# Third-party imports
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

# Local imports
from src.logger import setup_logger
from src.models import RequirementType
from src.database.database import get_db, init_db, SessionLocal
from src.database import crud
from src.auth.dependencies import get_current_user, require_admin, require_manager


@contextmanager
def db_session() -> Generator:
    """Context manager that opens and properly closes a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Setup logging
setup_logger(name="api", log_file=Path("logs/api.log"), level="INFO")
logger = logging.getLogger("api")

# Setup logging for other modules
setup_logger(name="src.openrouter_client", log_file=Path("logs/openrouter.log"), level="INFO")
setup_logger(name="src.requirements_extractor", log_file=Path("logs/extractor.log"), level="INFO")
setup_logger(name="src.pdf_processor", log_file=Path("logs/pdf.log"), level="INFO")

def _seed_admin_if_needed() -> None:
    """Ensure the default admin user exists and has the password from env vars.

    - If no users exist: creates the admin.
    - If the admin email exists: updates the password from env (so changing
      ADMIN_PASSWORD in .env and restarting always takes effect).
    """
    from src.auth.password import hash_password
    from src.database.models import User as UserModel

    email = os.getenv("ADMIN_EMAIL", "admin@example.com")
    password = os.getenv("ADMIN_PASSWORD", "changeme")
    name = os.getenv("ADMIN_NAME", "Администратор")

    with db_session() as db:
        existing = crud.get_user_by_email(db, email)
        if existing:
            # Always sync the password from env so restarts with new password work
            db.query(UserModel).filter(UserModel.id == existing.id).update(
                {"hashed_password": hash_password(password)}
            )
            db.commit()
            logger.info(f"Admin password synced from env: {email}")
        else:
            crud.create_user(db, email=email, hashed_password=hash_password(password), full_name=name, role="admin")
            logger.info(f"Created default admin user: {email}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler — runs startup and shutdown logic.

    In Docker: schema is managed by `alembic upgrade head` in entrypoint.sh.
    In local dev (without entrypoint): init_db() creates tables as fallback.
    """
    try:
        # Fallback for local dev without entrypoint.sh (alembic not run manually)
        init_db()
        _seed_admin_if_needed()
    except Exception as e:
        logger.error(f"Startup error: {e}")
        logger.warning("Continuing — some features may not work")
    logger.info("WebSocket logging system initialized")
    yield


# Create FastAPI app
app = FastAPI(
    title="PDF Requirements Extractor API - OpenRouter",
    description="Extract requirements from technical specifications using OpenRouter AI models (Claude, GPT, Gemini, Qwen)",
    version="3.0.0",
    lifespan=lifespan,
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


# Initialize manager AFTER class definition
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
            sys.stderr.write(f"WebSocket logging error: {e}\n")


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
        "version": "3.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint for monitoring.
    
    Returns:
        Dictionary with health status and current timestamp.
    """
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


# ========== Auth Endpoints ==========


class LoginRequest(BaseModel):
    """Login request body."""
    email: str = Field(..., description="User email")
    password: str = Field(..., description="Password")


class LoginResponse(BaseModel):
    """Login response with JWT."""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    user: Dict[str, Any] = Field(..., description="User info")


@app.post("/api/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest, db=Depends(get_db)):
    """Authenticate user and return JWT token."""
    from src.auth.password import verify_password
    from src.auth.jwt import create_access_token

    user = crud.get_user_by_email(db, request.email)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(data={"sub": str(user.id)})
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user={
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
        },
    )


@app.get("/api/auth/me")
async def get_me(current_user=Depends(get_current_user)):
    """Get current authenticated user."""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "is_active": current_user.is_active,
    }


# ========== Users Management (admin only) ==========


class CreateUserRequest(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = None
    role: str = "user"


class UpdateUserRequest(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


def _user_to_dict(user) -> Dict[str, Any]:
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


@app.get("/api/users")
async def list_users(
    db=Depends(get_db),
    _current=Depends(get_current_user),
):
    """List all users. Any authenticated user can view (for assignee pickers)."""
    users = crud.list_users(db)
    return [_user_to_dict(u) for u in users]


@app.post("/api/users", status_code=201)
async def create_user(
    request: CreateUserRequest,
    db=Depends(get_db),
    _current=Depends(require_admin),
):
    """Create a new user. Admin only."""
    from src.auth.password import hash_password

    if crud.get_user_by_email(db, request.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    if request.role not in ("admin", "manager", "user"):
        raise HTTPException(status_code=400, detail="Invalid role")
    user = crud.create_user(
        db,
        email=request.email,
        hashed_password=hash_password(request.password),
        full_name=request.full_name,
        role=request.role,
    )
    return _user_to_dict(user)


@app.put("/api/users/{user_id}")
async def update_user(
    user_id: int,
    request: UpdateUserRequest,
    db=Depends(get_db),
    _current=Depends(require_admin),
):
    """Update user. Admin only."""
    from src.auth.password import hash_password
    from src.database.models import User as UserModel

    user = crud.update_user(
        db,
        user_id,
        full_name=request.full_name,
        role=request.role,
        is_active=request.is_active,
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if request.password:
        db.query(UserModel).filter(UserModel.id == user_id).update(
            {"hashed_password": hash_password(request.password)}
        )
        db.commit()
        db.refresh(user)

    return _user_to_dict(user)


@app.delete("/api/users/{user_id}", status_code=204)
async def delete_user(
    user_id: int,
    db=Depends(get_db),
    current_user=Depends(require_admin),
):
    """Deactivate (soft-delete) a user. Admin only."""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")
    user = crud.update_user(db, user_id, is_active=False)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")


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


async def send_progress(step: str, progress: int, message: str, section_id: Optional[int] = None, **kwargs) -> None:
    """Send progress update to all connected WebSocket clients.
    
    Broadcasts progress information to connected clients and logs to console
    and file. Handles cases where no clients are connected.
    
    Args:
        step: Name of the current processing step (e.g., 'upload', 'pdf', 'extract').
        progress: Progress percentage (0-100).
        message: Human-readable progress message.
        section_id: Optional section identifier for parallel processing context.
        **kwargs: Additional metadata to include in the progress message.
    """
    progress_msg = {
        "type": "progress",
        "step": step,
        "progress": progress,
        "message": message,
        "timestamp": datetime.now().isoformat()
    }
    
    # Add section context if provided
    if section_id is not None:
        progress_msg["section_id"] = section_id
    
    # Add any additional metadata
    progress_msg.update(kwargs)
    
    # Log to file only (removed print() duplication)
    logger.info(f"[PROGRESS] {progress}% - {message}" + (f" (section {section_id})" if section_id else ""))
    
    # Send to WebSocket
    if len(manager.active_connections) > 0:
        await manager.send_message(progress_msg)
    else:
        logger.warning("[PROGRESS] No active WebSocket connections!")


async def send_metric(metric_name: str, value: Any, section: Optional[str] = None, **kwargs) -> None:
    """Send structured metric to all connected WebSocket clients.
    
    Broadcasts structured metric data for real-time monitoring and analytics.
    
    Args:
        metric_name: Name of the metric (e.g., 'requirements_extracted', 'ai_call_complete').
        value: Metric value (number, string, etc.).
        section: Optional section identifier.
        **kwargs: Additional metric metadata (e.g., tokens, cost, duration).
    """
    metric_msg = {
        "type": "metric",
        "metric_name": metric_name,
        "value": value,
        "timestamp": datetime.now().isoformat()
    }
    
    if section is not None:
        metric_msg["section"] = section
    
    metric_msg.update(kwargs)
    
    logger.debug(f"[METRIC] {metric_name}={value}" + (f" section={section}" if section else ""))
    
    if len(manager.active_connections) > 0:
        await manager.send_message(metric_msg)


@app.post("/api/extract", response_model=ExtractionResult)
async def extract_requirements(
    file: UploadFile = File(..., description="PDF file containing technical specifications"),
    generate_word: bool = Form(True),
    model: str = Form("claude-sonnet-4.5", description="AI model identifier"),
    project_id: Optional[str] = Form(None, description="Project ID to associate document with"),
    _current=Depends(require_manager),
) -> ExtractionResult:
    """Extract requirements from uploaded PDF using OpenRouter AI models.

    Delegates to ExtractionService which encapsulates the full pipeline.
    Progress updates are sent via WebSocket in real-time.
    """
    from src.extraction_service import ExtractionService

    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    logger.info(f"[UPLOAD] Starting upload: {file.filename}")

    current_loop = asyncio.get_running_loop()

    # Setup WebSocket logging for this extraction session
    ws_handler = WebSocketHandler(manager, current_loop)
    ws_handler.setLevel(logging.INFO)
    ws_handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
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


# ========== Database API Endpoints ==========

@app.get("/api/documents")
async def get_all_documents(
    skip: int = 0,
    limit: int = 100,
    project_id: Optional[int] = Query(None, description="Filter by project"),
    db=Depends(get_db),
    _current=Depends(get_current_user),
):
    """Get all documents with pagination. Optionally filter by project."""
    try:
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
async def get_document(document_id: int, db=Depends(get_db)):
    """Get document by ID with full metadata.
    
    Args:
        document_id: Document ID
    
    Returns:
        Document with metadata
    """
    try:
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
    assignee_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 5000,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
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

        # Resolve assignee_id filter: "me" → current user's id
        assignee_filter: Optional[int] = None
        if assignee_id == "me":
            assignee_filter = current_user.id
        elif assignee_id:
            try:
                assignee_filter = int(assignee_id)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid assignee_id")

        requirements = crud.get_requirements_by_document(
            db=db,
            document_id=document_id,
            status=status,
            type=req_type,
            assignee_id=assignee_filter,
            skip=skip,
            limit=limit,
        )
        
        return {
            "requirements": [
                {
                    "id": req.id,
                    "requirement_id": req.requirement_id,
                    "text": req.text,
                    "type": req.type,
                    "priority": req.priority,
                    "page_number": req.page_number,
                    "status": req.status,
                    "assignee_id": req.assignee_id,
                    "ai_suggested": req.ai_suggested,
                    "human_edited": req.human_edited,
                    "edit_reason": req.edit_reason,
                    "edited_at": req.edited_at.isoformat() if req.edited_at else None,
                    "section_id": req.section_id,
                    "section_number": req.section.section_number if req.section else None,
                    "section_title": req.section.title if req.section else None,
                    "subitems": req.subitems if hasattr(req, 'subitems') else None,
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
async def get_metrics(document_id: int, db=Depends(get_db)):
    """Get coverage metrics for a document.
    
    Args:
        document_id: Document ID
    
    Returns:
        Coverage metrics with statistics
    """
    try:
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
async def get_requirement(requirement_id: int, db=Depends(get_db), _current=Depends(get_current_user)):
    """Get requirement by ID with full details.
    
    Args:
        requirement_id: Requirement ID
    
    Returns:
        Requirement with full metadata including audit trail
    """
    try:
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
async def accept_requirement_endpoint(requirement_id: int, db=Depends(get_db), _current=Depends(require_manager)):
    """Accept a requirement (mark as accepted).
    
    Marks the requirement as accepted, meaning the AI-suggested text
    is correct and approved by human reviewer.
    
    Args:
        requirement_id: Requirement ID to accept
    
    Returns:
        Updated requirement with status 'accepted'
    """
    try:
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
    request: Optional[RejectRequirementRequest] = None,
    db=Depends(get_db),
    _current=Depends(require_manager),
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
    request: EditRequirementRequest,
    db=Depends(get_db),
    _current=Depends(require_manager),
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


class AssignRequest(BaseModel):
    assignee_id: Optional[int] = None


@app.post("/api/requirements/{requirement_id}/assign")
async def assign_requirement(
    requirement_id: int,
    request: AssignRequest,
    db=Depends(get_db),
    current_user=Depends(require_manager),
):
    """Assign (or unassign) an executor to a requirement. Manager/admin only."""
    from src.database.models import Requirement as ReqModel

    req = db.query(ReqModel).filter(ReqModel.id == requirement_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Requirement not found")

    if request.assignee_id is not None:
        assignee = crud.get_user_by_id(db, request.assignee_id)
        if not assignee:
            raise HTTPException(status_code=404, detail="User not found")

    req.assignee_id = request.assignee_id
    db.commit()
    db.refresh(req)

    assignee_info = None
    if req.assignee_id:
        u = crud.get_user_by_id(db, req.assignee_id)
        assignee_info = {"id": u.id, "full_name": u.full_name, "email": u.email} if u else None

    return {"requirement_id": requirement_id, "assignee": assignee_info}


# ========== Execution Status Endpoint ==========

# Manager statuses (review pipeline): pending, accepted, rejected, modified
# Executor statuses (work tracking):   in_progress, done, blocked
EXECUTION_STATUSES = {"in_progress", "done", "blocked"}
MANAGER_STATUSES = {"pending", "accepted", "rejected", "modified"}
ALL_STATUSES = EXECUTION_STATUSES | MANAGER_STATUSES


class SetStatusRequest(BaseModel):
    status: str


@app.post("/api/requirements/{requirement_id}/set-status")
async def set_requirement_status(
    requirement_id: int,
    request: SetStatusRequest,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Update requirement execution status.

    - Execution statuses (in_progress / done / blocked): any authenticated user,
      but only for requirements assigned to them (unless admin/manager).
    - Manager statuses (accepted / rejected / modified): manager+ only.
      Use the dedicated /accept, /reject, /edit endpoints for those.
    """
    from src.database.models import Requirement as ReqModel

    if request.status not in ALL_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Allowed: {sorted(ALL_STATUSES)}",
        )

    req = db.query(ReqModel).filter(ReqModel.id == requirement_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Requirement not found")

    # Execution statuses: user can only update their own requirements
    if request.status in EXECUTION_STATUSES:
        if current_user.role == "user" and req.assignee_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="You can only update status of requirements assigned to you",
            )
    else:
        # Manager statuses require manager+ role
        if current_user.role not in ("admin", "manager"):
            raise HTTPException(status_code=403, detail="Manager role required")

    req.status = request.status
    db.commit()
    db.refresh(req)
    return {"requirement_id": requirement_id, "status": req.status}


# ========== Comments Endpoints ==========


class CommentRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)


def _comment_to_dict(comment, user=None) -> Dict[str, Any]:
    return {
        "id": comment.id,
        "requirement_id": comment.requirement_id,
        "user_id": comment.user_id,
        "author_name": user.full_name or user.email if user else None,
        "text": comment.text,
        "created_at": comment.created_at.isoformat() if comment.created_at else None,
    }


@app.get("/api/requirements/{requirement_id}/comments")
async def get_comments(
    requirement_id: int,
    db=Depends(get_db),
    _current=Depends(get_current_user),
):
    """List comments for a requirement."""
    comments = crud.get_comments(db, requirement_id)
    result = []
    for c in comments:
        user = crud.get_user_by_id(db, c.user_id) if c.user_id else None
        result.append(_comment_to_dict(c, user))
    return result


@app.post("/api/requirements/{requirement_id}/comments", status_code=201)
async def add_comment(
    requirement_id: int,
    request: CommentRequest,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Add a comment to a requirement."""
    from src.database.models import Requirement as ReqModel

    req = db.query(ReqModel).filter(ReqModel.id == requirement_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Requirement not found")

    comment = crud.create_comment(db, requirement_id, current_user.id, request.text)
    return _comment_to_dict(comment, current_user)


@app.delete("/api/comments/{comment_id}", status_code=204)
async def delete_comment(
    comment_id: int,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Delete own comment (or admin deletes any)."""
    from src.database.models import Comment as CommentModel

    comment = db.query(CommentModel).filter(CommentModel.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not allowed")

    deleted = crud.delete_comment(db, comment_id, current_user.id)
    if not deleted and current_user.role == "admin":
        # Admin force-delete
        db.delete(comment)
        db.commit()


@app.get("/api/documents/{document_id}/pdf")
async def get_document_pdf(document_id: int, db=Depends(get_db)):
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
        document = crud.get_document(db, document_id)
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        file_path = Path(document.file_path)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="PDF file not found")
        
        return FileResponse(
            path=file_path,
            media_type="application/pdf",
            headers={"Content-Disposition": "inline"},
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
    project_ids = [p.id for p in projects]
    counts = crud.get_project_counts(db, project_ids) if project_ids else {}
    result = []
    for p in projects:
        c = counts.get(p.id, {"doc_count": 0, "req_count": 0})
        result.append({
            "id": p.id,
            "name": p.name,
            "code": p.code,
            "description": p.description,
            "status": p.status,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            "documents_count": c["doc_count"],
            "requirements_count": c["req_count"],
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
    doc_ids = [d.id for d in documents]
    req_counts = crud.get_document_req_counts(db, doc_ids) if doc_ids else {}
    docs_data = []
    for doc in documents:
        req_count = req_counts.get(doc.id, 0)
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
    background_tasks: BackgroundTasks,
    db=Depends(get_db),
):
    """Generate Word document from database data on-the-fly."""
    from src.word_exporter import generate_word_from_db

    document = crud.get_document(db, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        sections = crud.get_sections_by_document(db, document_id)
        all_requirements = crud.get_requirements_by_document(db, document_id)
        metrics = crud.get_coverage_metrics(db, document_id)

        tmp_path = generate_word_from_db(document, sections, all_requirements, metrics)
        if tmp_path is None:
            raise HTTPException(status_code=500, detail="python-docx not available")

        background_tasks.add_task(os.unlink, tmp_path)
        return FileResponse(
            tmp_path,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=f"{document.filename}_requirements.docx",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[EXPORT] Word generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/documents/{document_id}/export/json")
async def export_json(
    document_id: int,
    background_tasks: BackgroundTasks,
    db=Depends(get_db),
):
    """
    Generate JSON registry from database data on-the-fly.
    
    Args:
        document_id: Document ID
        
    Returns:
        JSON response with requirements registry
    """
    try:
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
                        "section_number": section.section_number,
                        "section_title": section.title,
                        "subitems": req.subitems or [],
                        "status": req.status,
                        "human_edited": req.human_edited,
                        "edit_reason": req.edit_reason,
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
        
        background_tasks.add_task(os.unlink, temp_file.name)
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
    background_tasks: BackgroundTasks,
    db=Depends(get_db),
):
    """
    Generate TXT usage report from database data on-the-fly.
    
    Args:
        document_id: Document ID
        
    Returns:
        TXT file with processing statistics
    """
    try:
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
            "РЕЕСТР ТРЕБОВАНИЙ",
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

        assigned_ids: set = set()
        for section in sections:
            section_requirements = [r for r in all_requirements if r.section_id == section.id]
            assigned_ids.update(r.id for r in section_requirements)

            lines.append(f"{'─' * 60}")
            lines.append(f"Раздел {section.section_number}: {section.title}")
            lines.append(f"Страницы: {section.page_start} – {section.page_end}  |  Требований: {len(section_requirements)}")
            lines.append(f"{'─' * 60}")
            lines.append("")

            for req in section_requirements:
                display_text = req.human_edited or req.text or ""
                lines.append(f"[{req.requirement_id}] стр.{req.page_number or '?'}  [{req.type or '—'}]  [{req.priority or '—'}]  [{req.status}]")
                lines.append(f"  {display_text}")
                if req.subitems:
                    for item in req.subitems:
                        lines.append(f"    • {item}")
                lines.append("")

        # Orphan requirements (section_id is NULL)
        orphans = [r for r in all_requirements if r.id not in assigned_ids]
        if orphans:
            lines.extend([f"{'─' * 60}", f"Требования без раздела  ({len(orphans)} шт.)", f"{'─' * 60}", ""])
            for req in orphans:
                display_text = req.human_edited or req.text or ""
                lines.append(f"[{req.requirement_id}] стр.{req.page_number or '?'}  [{req.type or '—'}]  [{req.priority or '—'}]  [{req.status}]")
                lines.append(f"  {display_text}")
                if req.subitems:
                    for item in req.subitems:
                        lines.append(f"    • {item}")
                lines.append("")

        lines.append("=" * 80)
        
        # Save to temporary file
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
        temp_file.write('\n'.join(lines))
        temp_file.close()
        
        logger.info(f"[EXPORT] TXT report generated: {temp_file.name}")
        
        background_tasks.add_task(os.unlink, temp_file.name)
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
