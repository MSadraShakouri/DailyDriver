import importlib
import pkgutil
import unittest

import dailydriver.cli.commands


class TestCommandImports(unittest.TestCase):
    def test_all_command_modules_importable(self):
        """Ensure every module in dailydriver.cli.commands can be imported and has __all__."""
        package = dailydriver.cli.commands
        prefix = package.__name__ + "."
        for importer, modname, ispkg in pkgutil.iter_modules(package.__path__, prefix):
            if modname.endswith("__init__"):
                continue
            mod = importlib.import_module(modname)
            self.assertTrue(hasattr(mod, "__all__"), f"{modname} missing __all__")
            for name in mod.__all__:
                self.assertTrue(hasattr(mod, name), f"{modname} missing symbol {name}")
