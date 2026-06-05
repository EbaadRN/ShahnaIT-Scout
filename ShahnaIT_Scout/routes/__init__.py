# routes/__init__.py
from .candidates import candidates_bp
from .jobs import jobs_bp
from .analyze import analyze_bp
from .export import export_bp
from .documents import documents_bp

__all__ = ['candidates_bp', 'jobs_bp', 'analyze_bp', 'export_bp', 'documents_bp']
