from __future__ import annotations

from telegram import Update

from datingbot.application import build_application


def main() -> None:
    app = build_application()
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
