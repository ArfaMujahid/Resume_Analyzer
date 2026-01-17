import os
import magic
import hashlib
from pathlib import Path
from typing import Tuple, Optional, List
import logging

logger = logging.getLogger(__name__)

class FileSecurityScanner:
    """Scanner for checking file security and validity"""

    # Allowed MIME types for resume uploads
    ALLOWED_MIME_TYPES = {
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'text/plain',
        'text/rtf'
    }

    # Allowed file extensions
    ALLOWED_EXTENSIONS = {
        '.pdf', '.doc', '.docx', '.txt', '.rtf'
    }

    # Suspicious file patterns
    SUSPICIOUS_PATTERNS = [
        'script', 'executable', 'macro', 'auto_open',
        'autoexec', 'shell', 'powershell', 'cmd',
        'bat', 'vbs', 'js', 'jar', 'app', 'deb',
        'rpm', 'dmg', 'pkg', 'msi', 'exe', 'dll'
    ]

    # Maximum file size (10MB)
    MAX_FILE_SIZE = 10 * 1024 * 1024

    def __init__(self):
        # Initialize python-magic for file type detection
        try:
            self.magic = magic.Magic(mime=True)
        except Exception as e:
            logger.error(f"Failed to initialize python-magic: {e}")
            self.magic = None

    def scan_file(self, file_path: str, original_filename: str = None) -> Tuple[bool, Optional[str], List[str]]:
        """
        Scan a file for security issues

        Args:
            file_path: Path to the file to scan
            original_filename: Original filename from upload

        Returns:
            Tuple of (is_safe, error_message, warnings)
        """
        warnings = []

        try:
            # Check file exists
            if not os.path.exists(file_path):
                return False, "File not found", warnings

            # Check file size
            file_size = os.path.getsize(file_path)
            if file_size > self.MAX_FILE_SIZE:
                return False, f"File too large. Maximum size is {self.MAX_FILE_SIZE // (1024*1024)}MB", warnings

            if file_size == 0:
                return False, "File is empty", warnings

            # Check file extension
            file_ext = Path(original_filename or file_path).suffix.lower()
            if file_ext not in self.ALLOWED_EXTENSIONS:
                return False, f"File type '{file_ext}' not allowed", warnings

            # Check MIME type
            if self.magic:
                try:
                    mime_type = self.magic.from_file(file_path)
                    if mime_type not in self.ALLOWED_MIME_TYPES:
                        return False, f"File type '{mime_type}' not allowed", warnings
                except Exception as e:
                    logger.warning(f"Failed to detect MIME type: {e}")
                    warnings.append("Could not verify file type")

            # Check for suspicious content in filename
            if original_filename:
                filename_lower = original_filename.lower()
                for pattern in self.SUSPICIOUS_PATTERNS:
                    if pattern in filename_lower:
                        return False, f"Suspicious filename detected", warnings

            # Check file header signatures
            is_valid_header, header_error = self._check_file_header(file_path, file_ext)
            if not is_valid_header:
                return False, header_error, warnings

            # Calculate file hash for logging
            file_hash = self._calculate_file_hash(file_path)
            logger.info(f"File scanned successfully: {original_filename}, hash: {file_hash}")

            return True, None, warnings

        except Exception as e:
            logger.error(f"Error scanning file {file_path}: {e}")
            return False, f"Error scanning file: {str(e)}", warnings

    def _check_file_header(self, file_path: str, file_ext: str) -> Tuple[bool, Optional[str]]:
        """Check if file has correct header signature for its type"""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(16)

            # File signatures (magic numbers)
            signatures = {
                '.pdf': b'%PDF',
                '.doc': b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1',
                '.docx': b'PK\x03\x04',
                '.txt': None,  # Text files don't have specific signatures
                '.rtf': b'{\\rtf'
            }

            expected_sig = signatures.get(file_ext)
            if expected_sig is None:
                return True, None  # No signature check needed

            if not header.startswith(expected_sig):
                return False, f"File does not have correct signature for {file_ext} format"

            return True, None

        except Exception as e:
            logger.warning(f"Error checking file header: {e}")
            return False, "Could not verify file format"

    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of file"""
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.error(f"Error calculating file hash: {e}")
            return ""

    def is_suspicious_filename(self, filename: str) -> bool:
        """Check if filename contains suspicious patterns"""
        filename_lower = filename.lower()

        # Check for suspicious patterns
        for pattern in self.SUSPICIOUS_PATTERNS:
            if pattern in filename_lower:
                return True

        # Check for double extensions
        parts = filename.split('.')
        if len(parts) > 2:
            # Check if it's trying to hide executable extension
            if any(ext in parts[-2].lower() for ext in ['exe', 'bat', 'cmd', 'scr']):
                return True

        return False

# Global scanner instance
file_scanner = FileSecurityScanner()