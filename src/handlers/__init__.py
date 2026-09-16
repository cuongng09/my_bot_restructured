"""
Telegram event handlers: commands, text, voice, media, dashboard.
"""

from handlers.commands import *
from handlers.text_handler import handle_text
from handlers.voice_handler import handle_voice
from handlers.media_handler import handle_media
from handlers.dashboard_handler import cmd_ui, handle_callback_query
