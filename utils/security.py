"""
Security and sanitization utilities for the IntelliDoc application.
"""
import os
import re
from typing import Optional
from werkzeug.utils import secure_filename
import uuid

def sanitize_filename(filename: str, fallback_prefix: str = "document") -> str:
    """
    Sanitizes a filename to make it safe for filesystem and URL storage.
    Prevents path traversal, directory creations, and dangerous shell inputs.
    
    Args:
        filename: The input filename to sanitize
        fallback_prefix: Prefix to use if sanitization yields empty string
        
    Returns:
        A safe string filename.
    """
    if not filename or not isinstance(filename, str):
        return f"{fallback_prefix}_{uuid.uuid4().hex[:8]}"

    # Remove null bytes
    filename = filename.replace('\x00', '')

    # Standard sanitization via werkzeug
    safe_name = secure_filename(filename)

    # If the filename becomes empty (e.g., purely Unicode or special chars)
    if not safe_name or safe_name in ('.', '..'):
        # Keep extension if present
        ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        if ext and re.match(r'^[a-z0-9]+$', ext):
            safe_name = f"{fallback_prefix}_{uuid.uuid4().hex[:8]}.{ext}"
        else:
            safe_name = f"{fallback_prefix}_{uuid.uuid4().hex[:8]}"

    return safe_name

def safe_join(directory: str, *pathnames: str) -> str:
    """
    Safely joins directory path with target pathnames, raising ValueError
    if the resulting path resolves to a location outside the directory prefix.
    
    Args:
        directory: The base directory
        *pathnames: Additional path components to join
        
    Returns:
        An absolute path inside the base directory.
    
    Raises:
        ValueError: If path resolves outside base directory or base is invalid.
    """
    if not directory:
        raise ValueError("Directory base must be specified")
        
    base = os.path.abspath(directory)
    joined = os.path.abspath(os.path.join(base, *pathnames))
    
    # Check that joined path starts with the base path
    # Using commonpath is safer than startswith because it avoids prefix injection
    # e.g., /app/uploads_other vs /app/uploads
    try:
        common = os.path.commonpath([base, joined])
        if common != base:
            raise ValueError(f"Path traversal detected: {joined} is outside {base}")
    except ValueError as e:
        raise ValueError(f"Path traversal detected: {e}")
        
    return joined

def validate_file_signature(file_bytes: bytes, filename: str) -> bool:
    """
    Validates file headers (magic bytes) against its filename extension to prevent spoofing.
    
    Args:
        file_bytes: The leading bytes or full bytes of the file.
        filename: The filename with extension.
        
    Returns:
        True if the file content matches standard headers for that extension, False otherwise.
    """
    if not filename or '.' not in filename:
        return False
        
    ext = filename.rsplit('.', 1)[1].lower()
    
    # We only need the first 8-16 bytes for magic number detection
    header = file_bytes[:16]
    
    # Map extensions to their allowed magic numbers
    if ext == 'pdf':
        return header.startswith(b'%PDF')
    elif ext in ('png',):
        return header.startswith(b'\x89PNG\r\n\x1a\n')
    elif ext in ('jpg', 'jpeg'):
        return header.startswith(b'\xff\xd8\xff')
    elif ext == 'gif':
        return header.startswith(b'GIF87a') or header.startswith(b'GIF89a')
    elif ext in ('docx', 'xlsx', 'pptx'):
        # Modern Office files are ZIP archives
        return header.startswith(b'PK\x03\x04')
    elif ext in ('doc', 'xls'):
        # Legacy Office files are OLECF files
        return header.startswith(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1')
    elif ext == 'txt':
        # Text files shouldn't contain null bytes and should decode cleanly as UTF-8
        try:
            # Check a portion of the text
            text_sample = file_bytes[:4096]
            if b'\x00' in text_sample:
                return False
            text_sample.decode('utf-8')
            return True
        except UnicodeDecodeError:
            try:
                text_sample.decode('ascii')
                return True
            except UnicodeDecodeError:
                return False
                
    # Fallback to extension checks
    return True
