from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, Path
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from uuid import UUID, uuid4
from datetime import datetime

# Initialize FastAPI app with metadata and tags
app = FastAPI(
    title="Simple Notes API",
    description="A minimal FastAPI backend providing CRUD operations for notes.",
    version="1.0.0",
    openapi_tags=[
        {"name": "health", "description": "Service health and readiness endpoints."},
        {"name": "notes", "description": "CRUD endpoints for managing notes."},
    ],
)

# Enable permissive CORS for demo purposes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------
# Pydantic Models
# -------------------------
class NoteBase(BaseModel):
    """Base fields for a note."""
    title: str = Field(..., description="The title of the note", min_length=1, max_length=200)
    content: str = Field(..., description="The content/body of the note", min_length=1)


class NoteCreate(NoteBase):
    """Payload schema for creating a note."""
    pass


class NoteUpdate(BaseModel):
    """Payload schema for updating a note."""
    title: Optional[str] = Field(None, description="Updated title of the note", min_length=1, max_length=200)
    content: Optional[str] = Field(None, description="Updated content of the note", min_length=1)


class Note(NoteBase):
    """Represents a note resource."""
    id: UUID = Field(..., description="Unique identifier for the note")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


# -------------------------
# In-memory storage
# -------------------------
# Simple in-memory store. For production, replace with a database.
NOTES_STORE: Dict[UUID, Note] = {}


def _now() -> datetime:
    """Return current UTC time with timezone-naive ISO consistency."""
    # Using datetime.utcnow() to avoid timezone complications for this simple demo
    return datetime.utcnow()


# -------------------------
# Health Endpoint
# -------------------------
# PUBLIC_INTERFACE
@app.get("/health", tags=["health"], summary="Health Check", description="Returns service health status.")
def health_check() -> Dict[str, str]:
    """This endpoint returns the health status of the service.
    Returns:
        JSON object indicating service is healthy.
    """
    return {"status": "ok"}


# Backward-compatible root endpoint to match existing openapi.json
# PUBLIC_INTERFACE
@app.get("/", tags=["health"], summary="Health Check (root)", description="Returns service health at root path for backward compatibility.")
def root_health_check() -> Dict[str, str]:
    """This endpoint returns the health status (root path).
    Returns:
        JSON object indicating service is healthy.
    """
    return {"status": "ok"}


# -------------------------
# Notes Endpoints (CRUD)
# -------------------------

# PUBLIC_INTERFACE
@app.get(
    "/notes",
    response_model=List[Note],
    tags=["notes"],
    summary="List notes",
    description="Retrieve all notes currently stored in the service.",
)
def list_notes() -> List[Note]:
    """List all notes in the in-memory store.
    Returns:
        A list of Note objects.
    """
    return list(NOTES_STORE.values())


# PUBLIC_INTERFACE
@app.post(
    "/notes",
    response_model=Note,
    status_code=201,
    tags=["notes"],
    summary="Create a note",
    description="Create a new note with a generated UUID and timestamps.",
)
def create_note(payload: NoteCreate) -> Note:
    """Create a new note.
    Args:
        payload: The NoteCreate payload containing title and content.
    Returns:
        The newly created Note object with id and timestamps.
    """
    note_id = uuid4()
    now = _now()
    note = Note(id=note_id, title=payload.title, content=payload.content, created_at=now, updated_at=now)
    NOTES_STORE[note_id] = note
    return note


# PUBLIC_INTERFACE
@app.get(
    "/notes/{note_id}",
    response_model=Note,
    tags=["notes"],
    summary="Get a note",
    description="Retrieve a single note by its UUID.",
)
def get_note(
    note_id: UUID = Path(..., description="The UUID of the note to retrieve"),
) -> Note:
    """Get a note by ID.
    Args:
        note_id: UUID of the note.
    Returns:
        The Note object.
    Raises:
        HTTPException 404 if note not found.
    """
    note = NOTES_STORE.get(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


# PUBLIC_INTERFACE
@app.put(
    "/notes/{note_id}",
    response_model=Note,
    tags=["notes"],
    summary="Update a note",
    description="Update the title and/or content of an existing note.",
)
def update_note(
    payload: NoteUpdate,
    note_id: UUID = Path(..., description="The UUID of the note to update"),
) -> Note:
    """Update an existing note.
    Args:
        note_id: UUID of the note to update.
        payload: Partial payload with fields to update.
    Returns:
        The updated Note object.
    Raises:
        HTTPException 404 if note not found.
        HTTPException 400 if no fields are provided to update.
    """
    existing = NOTES_STORE.get(note_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Note not found")

    if payload.title is None and payload.content is None:
        raise HTTPException(status_code=400, detail="At least one of 'title' or 'content' must be provided")

    updated = existing.model_copy()
    if payload.title is not None:
        updated.title = payload.title
    if payload.content is not None:
        updated.content = payload.content
    updated.updated_at = _now()
    NOTES_STORE[note_id] = updated
    return updated


# PUBLIC_INTERFACE
@app.delete(
    "/notes/{note_id}",
    status_code=204,
    tags=["notes"],
    summary="Delete a note",
    description="Delete a note by its UUID.",
    responses={
        204: {"description": "Note deleted successfully"},
        404: {"description": "Note not found"},
    },
)
def delete_note(
    note_id: UUID = Path(..., description="The UUID of the note to delete"),
) -> None:
    """Delete a note by ID.
    Args:
        note_id: UUID of the note.
    Raises:
        HTTPException 404 if note not found.
    """
    if note_id not in NOTES_STORE:
        raise HTTPException(status_code=404, detail="Note not found")
    del NOTES_STORE[note_id]
    # 204 No Content, return None
    return None
