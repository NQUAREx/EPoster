from __future__ import annotations

from pydantic import BaseModel, Field


class CommandRequest(BaseModel):
    command: str
    payload: dict | None = None
    source: str = "manual"
    wake_word_detected: bool = False


class WakeRequest(BaseModel):
    source: str = "voice"


class ViewportSize(BaseModel):
    width: int = Field(default=1920, ge=1)
    height: int = Field(default=1080, ge=1)


class AmbilightFrameRequest(BaseModel):
    top: list[list[int]] = Field(default_factory=list)
    right: list[list[int]] = Field(default_factory=list)
    bottom: list[list[int]] = Field(default_factory=list)
    left: list[list[int]] = Field(default_factory=list)
    viewport: ViewportSize = Field(default_factory=ViewportSize)


class CalibrationSampleRequest(BaseModel):
    observed_rgb: list[int] = Field(min_length=3, max_length=3)
