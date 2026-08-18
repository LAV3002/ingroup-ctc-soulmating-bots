from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Profile:
    user_id: int
    chat_id: int
    name: str
    username: str | None
    gender: str
    age: int
    looking_for: str
    hobbies: str
    dream: str
    photo_file_id: str | None = None
    verified: bool = False
    verified_by: str | None = None

    def __setstate__(self, state: dict) -> None:
        # Старые pickle-файлы не содержат полей верификации — достраиваем их.
        self.__dict__.setdefault("verified", False)
        self.__dict__.setdefault("verified_by", None)
        self.__dict__.update(state)
