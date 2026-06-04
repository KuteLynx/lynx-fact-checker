"""
filter_loader — Carga verificaia-filter.py como módulo Python
a pesar del guión en el nombre del archivo.
"""

import importlib.machinery
import importlib.util
from pathlib import Path

FILTER_PATH = Path(__file__).parent / "scripts" / "verificaia-filter.py"

loader = importlib.machinery.SourceFileLoader("verificaia_filter", str(FILTER_PATH))
spec = importlib.util.spec_from_loader("verificaia_filter", loader, origin=str(FILTER_PATH))
mod = importlib.util.module_from_spec(spec)
loader.exec_module(mod)

filtrar = mod.filtrar
