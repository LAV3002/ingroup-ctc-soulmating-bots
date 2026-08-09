from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Participant:
    chat_id: int
    user_id: int
    name: str
    phone: str
    username: str | None
    table_tag: str
    badge: int
