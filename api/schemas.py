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


class RuntimePrayerOverrideRequest(BaseModel):
    suhoor: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    iftar: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")


class RuntimeAccelerationRequest(BaseModel):
    hours_per_second: float = Field(default=1.0, ge=0.1, le=24.0)


class RuntimeBlobOverrideRequest(BaseModel):
    bg: str | None = Field(default=None, min_length=1)
    blob1: str | None = Field(default=None, min_length=1)
    blob2: str | None = Field(default=None, min_length=1)
    blob3: str | None = Field(default=None, min_length=1)
