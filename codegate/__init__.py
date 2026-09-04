"""CodeGate: Python resource-leak analyzer."""

__version__ = "0.1.0"
from .analyzer import analyze_file, analyze_source
from .config import DEFAULT_RESOURCES, ResourceSpec

__all__ = ["analyze_file", "analyze_source", "DEFAULT_RESOURCES", "ResourceSpec", "__version__"]
