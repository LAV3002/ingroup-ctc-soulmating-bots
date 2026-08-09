from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Profile:
    user_id: int
    chat_id: int
    name: str
    phone: str
    username: str | None
    gender: str
    age: int
    looking_for: str
    hobbies: str
    dream: str
    photo_file_id: str | None = None
    answers: dict[str, str] = field(default_factory=dict)
