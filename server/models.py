"""models.py - Pydantic request/response models for CWS online server.

Side convention: 1 = Union, 2 = Confederate (matches UNION/CONFEDERATE constants in cws_globals.py).
"""

from pydantic import BaseModel
from typing import Optional


class CreateGameRequest(BaseModel):
    side: int = 1  # creator's side: 1=Union, 2=Confederate


class CreateGameResponse(BaseModel):
    game_code: str
    token: str
    side: int


class JoinRequest(BaseModel):
    pass  # no body needed


class JoinResponse(BaseModel):
    token: str
    side: int


class GameStatusResponse(BaseModel):
    status: str
    current_side: int
    turn_number: int


class TurnSubmitRequest(BaseModel):
    turn_number: int
    state: dict


class PhaseRequest(BaseModel):
    phase: str = "events"
    label: str = ""


class TurnPollResponse(BaseModel):
    ready: bool
    state: Optional[dict] = None
    turn_number: int
    phase: str = "playing"
    phase_label: str = ""
