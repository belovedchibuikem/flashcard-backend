"""
Models package - exports all models including media models
"""
# Import media models directly from the media.py file to avoid conflict with app/models.py
import sys
import os
import importlib.util

# Get the path to media.py
_current_dir = os.path.dirname(__file__)
_media_path = os.path.join(_current_dir, 'media.py')

if os.path.exists(_media_path):
    spec = importlib.util.spec_from_file_location("app.models.media", _media_path)
    media_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(media_module)
    MediaAttachment = media_module.MediaAttachment
    ImageAnnotation = media_module.ImageAnnotation
    InteractiveDiagram = media_module.InteractiveDiagram
else:
    raise ImportError(f"Could not find media.py at {_media_path}")

# Re-export for convenience
__all__ = ['MediaAttachment', 'ImageAnnotation', 'InteractiveDiagram']
