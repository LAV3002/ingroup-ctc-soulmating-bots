from __future__ import annotations

from telegram.ext import filters

from config import ADMIN_USER_IDS

admin_filter = filters.User(user_id=list(ADMIN_USER_IDS))
private_filter = filters.ChatType.PRIVATE
