"""
skills package — Hệ thống kỹ năng và plugins dạng mô-đun cho Chat AI Bot.
"""

try:
    from skills.base import BaseSkill, SkillResult
    from skills.registry import SkillRegistry, default_registry
except ImportError:
    from skills.base import BaseSkill, SkillResult
    from skills.registry import SkillRegistry, default_registry

# Tự động quét và nạp toàn bộ skills có trong package
default_registry.auto_discover()

__all__ = ["BaseSkill", "SkillResult", "SkillRegistry", "default_registry"]
