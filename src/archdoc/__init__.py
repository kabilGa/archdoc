"""archdoc: automated context extraction for documentation and testing workflows."""

from archdoc.extractor import extract_module, extract_project, extract_source
from archdoc.models import ModuleInfo, ProjectContext, Symbol

__version__ = "0.2.0"

__all__ = [
    "ModuleInfo",
    "ProjectContext",
    "Symbol",
    "__version__",
    "extract_module",
    "extract_project",
    "extract_source",
]
