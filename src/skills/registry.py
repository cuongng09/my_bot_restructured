"""
skills/registry.py — Bộ quản lý tập trung và tự động nạp (Auto-discovery) cho các Plugins / Skills.
Cung cấp cơ chế Plug & Play: tự động quét thư mục skills, đăng ký tool cho Ollama và dispatch lệnh.
"""

from __future__ import annotations

import importlib
import inspect
import os
import pkgutil
from pathlib import Path
from typing import Dict, List, Optional, Type

import httpx

try:
    from core.logger import logger
except ImportError:
    from core.logger import logger

try:
    from skills.base import BaseSkill
except ImportError:
    from skills.base import BaseSkill


class SkillRegistry:
    """Quản lý vòng đời, đăng ký và điều phối cho toàn bộ các Skills."""

    def __init__(self):
        self._skills: Dict[str, BaseSkill] = {}
        self._commands: Dict[str, BaseSkill] = {}
        self._http_client: Optional[httpx.AsyncClient] = None

    def register(self, skill: BaseSkill) -> None:
        """Đăng ký một Skill instance vào registry."""
        if not skill.name:
            logger.warning(f"⚠️ Bỏ qua skill không có tên: {skill}")
            return

        self._skills[skill.name] = skill

        if skill.command:
            cmd_clean = skill.command.lower().lstrip("/")
            self._commands[cmd_clean] = skill

        if self._http_client and hasattr(skill, "set_http_client"):
            skill.set_http_client(self._http_client)

        logger.info(f"🧩 Đã nạp Skill: '{skill.name}' (Lệnh: /{skill.command or 'None'}, Enabled: {skill.enabled})")

    def unregister(self, name: str) -> Optional[BaseSkill]:
        """Gỡ bỏ một skill khỏi registry."""
        skill = self._skills.pop(name, None)
        if skill and skill.command:
            self._commands.pop(skill.command.lower().lstrip("/"), None)
        return skill

    def get(self, name: str) -> Optional[BaseSkill]:
        """Lấy skill theo tên định danh."""
        skill = self._skills.get(name)
        if skill and skill.enabled:
            return skill
        return None

    def get_by_command(self, command: str) -> Optional[BaseSkill]:
        """Lấy skill theo tên lệnh Telegram (vd: 'weather', 'news')."""
        cmd_clean = command.lower().lstrip("/")
        skill = self._commands.get(cmd_clean)
        if skill and skill.enabled:
            return skill
        return None

    def list_all(self, only_enabled: bool = True) -> List[BaseSkill]:
        """Lấy danh sách tất cả các skills."""
        if only_enabled:
            return [s for s in self._skills.values() if s.enabled]
        return list(self._skills.values())

    def set_http_client(self, client: httpx.AsyncClient) -> None:
        """Inject HTTP client dùng chung cho toàn bộ các skills trong hệ thống."""
        self._http_client = client
        for skill in self._skills.values():
            if hasattr(skill, "set_http_client"):
                skill.set_http_client(client)

    def get_ollama_tools(self) -> List[dict]:
        """Xuất danh sách schema công cụ cho Ollama / OpenAI Tool Calling."""
        tools = []
        for skill in self.list_all(only_enabled=True):
            if skill.parameters_schema:
                tools.append(skill.to_ollama_tool())
        return tools

    def auto_discover(self, package_dir: Optional[str] = None) -> int:
        """
        Tự động quét và phát hiện các class kế thừa BaseSkill trong thư mục skills
        và các thư mục module con như skills_module/.
        Thêm một file mới vào thư mục skills/ hoặc skills/skills_module/ là hệ thống tự động nhận diện.
        """
        if package_dir is None:
            package_dir = os.path.dirname(__file__)

        loaded_count = 0
        package_path = Path(package_dir)

        # Quét tất cả file .py trong thư mục skills và thư mục con (skills_module)
        module_targets: List[str] = []
        for _, module_name, is_pkg in pkgutil.iter_modules([str(package_path)]):
            if module_name in ("base", "registry", "__init__"):
                continue
            if is_pkg:
                # Quét thư mục con (ví dụ skills_module)
                sub_path = package_path / module_name
                for _, sub_name, sub_is_pkg in pkgutil.iter_modules([str(sub_path)]):
                    if not sub_is_pkg and sub_name not in ("__init__", "base"):
                        module_targets.append(f"{module_name}.{sub_name}")
            else:
                module_targets.append(module_name)

        for mod_target in module_targets:
            try:
                module = None
                for prefix in ("skills.", "my_bot.skills.", ""):
                    try:
                        module = importlib.import_module(f"{prefix}{mod_target}")
                        break
                    except ModuleNotFoundError:
                        continue
                if module is None:
                    raise ModuleNotFoundError(f"Không thể import module '{mod_target}'")

                for _, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, BaseSkill) and obj is not BaseSkill:
                        already_registered = any(isinstance(s, obj) for s in self._skills.values())
                        if not already_registered:
                            instance = obj(http_client=self._http_client)
                            self.register(instance)
                            loaded_count += 1
            except Exception as e:
                logger.warning(f"⚠️ Lỗi khi nạp plugin từ module '{mod_target}': {e}")

        return loaded_count


# Instance singleton dùng chung toàn hệ thống
default_registry = SkillRegistry()
