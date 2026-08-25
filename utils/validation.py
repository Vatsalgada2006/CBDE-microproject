"""
Input validation utilities for the IntelliDoc application.
"""
import re
from typing import Optional, Dict, Any, List
from datetime import datetime

def validate_email(email: str) -> bool:
    """Validate email format."""
    if not email or not isinstance(email, str):
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_password(password: str) -> bool:
    """Validate password strength.
    
    Requirements:
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    """
    if not password or not isinstance(password, str):
        return False
    if len(password) < 8:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'[0-9]', password):
        return False
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False
    return True

def validate_uuid(uuid_string: str) -> bool:
    """Validate UUID format."""
    if not uuid_string or not isinstance(uuid_string, str):
        return False
    pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    return bool(re.match(pattern, uuid_string.lower()))

def validate_filename(filename: str) -> bool:
    """Validate filename for safety.
    
    Checks for:
    - Reasonable length
    - No path traversal attempts
    - No null bytes
    - Reasonable character set
    """
    if not filename or not isinstance(filename, str):
        return False
    if len(filename) > 255:
        return False
    if '\x00' in filename:
        return False
    if '..' in filename or '/' in filename or '\\' in filename:
        return False
    # Allow alphanumeric, spaces, dots, hyphens, underscores
    if not re.match(r'^[a-zA-Z0-9._\- ]+$', filename):
        return False
    return True

def validate_file_content_type(content_type: str) -> bool:
    """Validate file content type."""
    allowed_types = {
        'text/plain',
        'application/pdf',
        'image/png',
        'image/jpeg',
        'image/gif',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    }
    return content_type in allowed_types

def validate_file_extension(filename: str) -> bool:
    """Validate file extension."""
    allowed_extensions = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx'}
    if not filename or '.' not in filename:
        return False
    extension = filename.rsplit('.', 1)[1].lower()
    return extension in allowed_extensions

def sanitize_input(text: str, max_length: Optional[int] = None) -> str:
    """Sanitize input text.
    
    Args:
        text: Input text to sanitize
        max_length: Maximum length (optional)
        
    Returns:
        Sanitized text
    """
    if not isinstance(text, str):
        return ""
    
    # Remove null bytes
    text = text.replace('\x00', '')
    
    # Strip whitespace
    text = text.strip()
    
    # Truncate if max_length specified
    if max_length and len(text) > max_length:
        text = text[:max_length]
    
    return text

def validate_pagination_params(page: Any, limit: Any) -> tuple[int, int]:
    """Validate and normalize pagination parameters."""
    try:
        page_int = int(page) if page else 1
        limit_int = int(limit) if limit else 12
    except (ValueError, TypeError):
        page_int = 1
        limit_int = 12
    
    # Ensure reasonable values
    page_int = max(1, page_int)
    limit_int = max(1, min(limit_int, 100))  # Cap at 100
    
    return page_int, limit_int

def validate_sort_field(sort_field: str, allowed_fields: List[str]) -> str:
    """Validate sort field against allowed fields."""
    if not sort_field or not isinstance(sort_field, str):
        return allowed_fields[0] if allowed_fields else 'created_at'
    
    # Handle prefix for direction (e.g., "-created_at" for descending)
    direction = '-'
    field = sort_field
    if sort_field.startswith('-'):
        field = sort_field[1:]
    
    if field in allowed_fields:
        return sort_field
    return allowed_fields[0] if allowed_fields else 'created_at'

class ValidationError(Exception):
    """Custom exception for validation errors."""
    def __init__(self, message: str, field: Optional[str] = None):
        self.message = message
        self.field = field
        super().__init__(self.message)
