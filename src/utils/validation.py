"""Validation utilities for JAR Indexer MCP server.

This module provides validation functions for Maven coordinates, URI formats,
and parameter types used throughout the JAR Indexer system.
"""

import re
from typing import Any, Optional
from urllib.parse import urlparse


def validate_maven_coordinates(
  group_id: str, artifact_id: str, version: Optional[str] = None
) -> bool:
  """Validate Maven coordinate components.

  Args:
      group_id: Maven group ID (e.g., 'org.springframework')
      artifact_id: Maven artifact ID (e.g., 'spring-core')
      version: Maven version (e.g., '5.3.21'), optional

  Returns:
      True if coordinates are valid

  Raises:
      ValueError: If any coordinate component is invalid
  """
  # Validate group_id
  if not group_id or not isinstance(group_id, str):
    raise ValueError("group_id must be a non-empty string")

  # Group ID pattern: lowercase letters, numbers, dots, and hyphens
  # Must start with lowercase letter or number
  group_pattern = r"^[a-z0-9]([a-z0-9._-]*[a-z0-9])?$"
  if not re.match(group_pattern, group_id):
    raise ValueError(
      f"Invalid group_id format: {group_id}. Must contain only lowercase letters, numbers, dots, underscores, and hyphens"
    )

  # Validate artifact_id
  if not artifact_id or not isinstance(artifact_id, str):
    raise ValueError("artifact_id must be a non-empty string")

  # Artifact ID pattern: lowercase letters, numbers, dots, hyphens, and underscores
  artifact_pattern = r"^[a-z0-9]([a-z0-9._-]*[a-z0-9])?$"
  if not re.match(artifact_pattern, artifact_id):
    raise ValueError(
      f"Invalid artifact_id format: {artifact_id}. Must contain only lowercase letters, numbers, dots, underscores, and hyphens"
    )

  # Validate version if provided
  if version is not None:
    if not isinstance(version, str) or not version:
      raise ValueError("version must be a non-empty string when provided")

    # Version can be more flexible, allowing alphanumeric, dots, hyphens, and underscores
    # Examples: 5.3.21, 1.0-SNAPSHOT, 2.0.0-M1, main, develop
    version_pattern = r"^[a-zA-Z0-9]([a-zA-Z0-9._-]*[a-zA-Z0-9])?$"
    if not re.match(version_pattern, version):
      raise ValueError(
        f"Invalid version format: {version}. Must contain only letters, numbers, dots, underscores, and hyphens"
      )

  return True


def validate_uri_format(uri: str) -> bool:
  """Validate URI format for supported schemes.

  Args:
      uri: URI to validate

  Returns:
      True if URI format is valid

  Raises:
      ValueError: If URI format is invalid
  """
  if not uri or not isinstance(uri, str):
    raise ValueError("URI must be a non-empty string")

  # Handle SSH Git format: git@host:user/repo
  if uri.startswith("git@"):
    return _validate_ssh_git_uri(uri)

  # Parse standard URI schemes
  try:
    parsed = urlparse(uri)
  except Exception as e:
    raise ValueError(f"Invalid URI format: {e}")

  if parsed.scheme == "file":
    return _validate_file_uri(parsed)
  elif parsed.scheme in ("http", "https"):
    return _validate_http_uri(parsed)
  else:
    raise ValueError(
      f"Unsupported URI scheme: {parsed.scheme}. Supported schemes: file, http, https, git@"
    )


def _validate_ssh_git_uri(uri: str) -> bool:
  """Validate SSH Git URI format: git@host:user/repo"""
  if not uri.startswith("git@"):
    raise ValueError("SSH Git URI must start with 'git@'")

  # Pattern: git@hostname:path/to/repo
  ssh_pattern = r"^git@([a-zA-Z0-9.-]+):([a-zA-Z0-9._/-]+)$"
  if not re.match(ssh_pattern, uri):
    raise ValueError(
      f"Invalid SSH Git URI format: {uri}. Expected format: git@hostname:path/to/repo"
    )

  return True


def _validate_file_uri(parsed) -> bool:
  """Validate file:// URI format"""
  if not parsed.path:
    raise ValueError("file:// URI must have a path")

  # File path should be absolute
  if not parsed.path.startswith("/"):
    raise ValueError("file:// URI must have an absolute path")

  return True


def _validate_http_uri(parsed) -> bool:
  """Validate http/https URI format"""
  if not parsed.netloc:
    raise ValueError("HTTP/HTTPS URI must have a hostname")

  if not parsed.path:
    raise ValueError("HTTP/HTTPS URI must have a path")

  # Must end with .jar or .git for our use cases
  path_lower = parsed.path.lower()
  if not (path_lower.endswith(".jar") or path_lower.endswith(".git")):
    raise ValueError(
      "HTTP/HTTPS URI must end with .jar (JAR file) or .git (Git repository)"
    )

  return True


def validate_parameter_types(**kwargs: Any) -> bool:
  """Validate parameter types for MCP tool arguments.

  Args:
      **kwargs: Parameter name-value pairs to validate

  Returns:
      True if all parameters are valid

  Raises:
      ValueError: If any parameter is invalid
  """
  for param_name, value in kwargs.items():
    if param_name in ("group_id", "artifact_id", "version", "git_ref"):
      if value is not None and not isinstance(value, str):
        raise ValueError(f"{param_name} must be a string, got {type(value).__name__}")

      if param_name in ("group_id", "artifact_id") and (not value or not value.strip()):
        raise ValueError(f"{param_name} cannot be empty")

    elif param_name == "source_uri":
      if not isinstance(value, str):
        raise ValueError(f"source_uri must be a string, got {type(value).__name__}")
      if not value or not value.strip():
        raise ValueError("source_uri cannot be empty")

    elif param_name == "auto_index":
      if not isinstance(value, bool):
        raise ValueError(f"auto_index must be a boolean, got {type(value).__name__}")

  return True


def validate_git_ref(git_ref: str) -> bool:
  """Validate Git reference format.

  Args:
      git_ref: Git reference (branch, tag, or commit hash)

  Returns:
      True if git_ref format is valid

  Raises:
      ValueError: If git_ref format is invalid
  """
  if not git_ref or not isinstance(git_ref, str):
    raise ValueError("git_ref must be a non-empty string")

  git_ref = git_ref.strip()
  if not git_ref:
    raise ValueError("git_ref cannot be empty or whitespace only")

  # Git refs cannot contain certain characters
  invalid_chars = [" ", "~", "^", ":", "?", "*", "[", "\\"]
  for char in invalid_chars:
    if char in git_ref:
      raise ValueError(f"git_ref cannot contain '{char}': {git_ref}")

  # Cannot start or end with slash, dot, or be just dots
  if git_ref.startswith("/") or git_ref.endswith("/"):
    raise ValueError(f"git_ref cannot start or end with '/': {git_ref}")

  if git_ref.startswith(".") or git_ref.endswith("."):
    raise ValueError(f"git_ref cannot start or end with '.': {git_ref}")

  if git_ref in (".", ".."):
    raise ValueError(f"git_ref cannot be '{git_ref}'")

  # Cannot have consecutive slashes or dots
  if "//" in git_ref or ".." in git_ref:
    raise ValueError(f"git_ref cannot contain consecutive '/' or '.': {git_ref}")

  return True
