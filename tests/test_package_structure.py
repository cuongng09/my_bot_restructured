"""
tests/test_package_structure.py — Kiểm tra tính toàn vẹn của cấu trúc src/.
"""

import unittest


class TestPackageStructure(unittest.TestCase):
    def test_import_core_modules(self):
        from core import (
            logger,
            db,
            llm_engine,
            reasoning,
            context_manager,
            tencent_memory,
            local_voice,
            utils,
        )
        self.assertIsNotNone(logger)
        self.assertIsNotNone(db)
        self.assertIsNotNone(llm_engine)
        self.assertIsNotNone(reasoning)

    def test_skills_auto_discovery(self):
        from skills.registry import default_registry
        skills = default_registry.list_all(only_enabled=False)
        skill_names = {s.name for s in skills}
        # Kiểm tra các skill cơ bản và skill trong skills_module (crypto)
        self.assertTrue({"weather", "news", "crypto"}.issubset(skill_names))

    def test_import_handlers(self):
        from handlers import (
            handle_text,
            handle_voice,
            handle_media,
            cmd_ui,
            handle_callback_query,
            cmd_start,
            cmd_help,
        )
        self.assertTrue(callable(handle_text))
        self.assertTrue(callable(handle_voice))

    def test_webapp_app_instance(self):
        from webapp.main import app, run_server
        self.assertIsNotNone(app)
        self.assertTrue(callable(run_server))

