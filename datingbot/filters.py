from __future__ import annotations

from telegram.ext import filters

from datingbot import config

admin_filter = filters.User(user_id=list(config.ADMIN_USER_IDS))
private_filter = filters.ChatType.PRIVATE
