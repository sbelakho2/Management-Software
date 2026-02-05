"""
Prompts package for Sensei OS Chatbot.
"""

from sensei.services.ai.chatbot.prompts.role_prompts import (
    BASE_PROMPT,
    ROLE_PROMPTS,
    get_prompt_for_role,
    get_role_level,
)

__all__ = [
    "BASE_PROMPT",
    "ROLE_PROMPTS",
    "get_prompt_for_role",
    "get_role_level",
]
