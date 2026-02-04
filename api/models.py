"""Modeles Pydantic pour validation des donnees."""

from typing import Optional
from pydantic import BaseModel, Field, HttpUrl, field_validator


class CaptureRequest(BaseModel):
    """Requete de capture de screenshot."""

    url: str = Field(..., description="URL du site a capturer")
    full_page: bool = Field(False, description="Capture full-page ou viewport")
    device: Optional[str] = Field("desktop", description="Type de device (desktop, tablet, phone)")
    width: Optional[int] = Field(None, ge=200, le=3840, description="Largeur custom viewport")
    height: Optional[int] = Field(None, ge=200, le=2160, description="Hauteur custom viewport")
    delay: int = Field(0, ge=0, le=30, description="Delai avant capture (secondes)")
    click: Optional[str] = Field(None, max_length=200, description="Selecteur CSS d'element a cliquer")
    hide: Optional[str] = Field(None, max_length=500, description="Selecteurs CSS d'elements a masquer")
    grab_html: bool = Field(False, description="Capturer le HTML source")

    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Valide que l'URL a un format minimal acceptable."""
        v = v.strip()
        if not v:
            raise ValueError("URL ne peut pas etre vide")
        # Le reste de la validation se fait dans security.py
        return v

    @field_validator('device')
    @classmethod
    def validate_device(cls, v: Optional[str]) -> str:
        """Valide le type de device."""
        if v is None:
            return "desktop"
        v = v.lower()
        if v not in ["desktop", "tablet", "phone"]:
            raise ValueError("Device doit etre: desktop, tablet ou phone")
        return v


class CaptureResponse(BaseModel):
    """Reponse de capture."""

    session_id: str
    screenshot: str = Field(..., description="Screenshot encode en base64")
    screenshot_format: str = "png"
    network_logs: list
    dom_elements: dict
    final_url: str
    capture_config: dict
    html_source: Optional[str] = None


class HealthResponse(BaseModel):
    """Reponse health check."""

    status: str
    version: str
    active_sessions: int
    active_contexts: int
    memory_percent: float
    memory_used_mb: int
    memory_available_mb: int


class ErrorResponse(BaseModel):
    """Reponse d'erreur standardisee."""

    error: str
    detail: Optional[str] = None
    session_id: Optional[str] = None
