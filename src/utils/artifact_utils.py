"""Maven artifact management utilities."""

import os
import json
from pathlib import Path

from ..types.core_types import RegisteredSourceInfo
from .validation import validate_maven_coordinates


def get_artifact_code_path(group_id: str, artifact_id: str, version: str) -> str:
  """Convert Maven coordinates to artifact code directory path.

  Args:
    group_id: Maven group ID (e.g., 'org.springframework')
    artifact_id: Maven artifact ID (e.g., 'spring-core')
    version: Maven version (e.g., '5.3.21')

  Returns:
    Relative path to artifact code directory

  Raises:
    ValueError: If Maven coordinates are invalid
  """
  # Validate Maven coordinates
  validate_maven_coordinates(group_id, artifact_id, version)

  # Convert group_id dots to path separators (org.springframework -> org/springframework)
  group_path = group_id.replace(".", "/")

  # Construct path: group_path/artifact_id/version
  artifact_path = f"{group_path}/{artifact_id}/{version}"

  return artifact_path


def is_artifact_code_available(group_id: str, artifact_id: str, version: str) -> bool:
  """Check if artifact source code exists in code/ directory.

  Args:
    group_id: Maven group ID
    artifact_id: Maven artifact ID
    version: Maven version

  Returns:
    True if code directory exists and contains sources

  Raises:
    ValueError: If Maven coordinates are invalid
  """
  # Get the artifact code path
  artifact_path = get_artifact_code_path(group_id, artifact_id, version)

  # Get the base directory from environment or use default ~/.jar-indexer
  base_dir = os.path.expanduser(os.environ.get("JAR_INDEXER_HOME", "~/.jar-indexer"))
  code_dir = os.path.join(base_dir, "code", artifact_path)

  # Check if the code directory exists and has content
  code_path = Path(code_dir)
  if not code_path.exists():
    return False

  if not code_path.is_dir():
    return False

  # Check if directory has any content (should have sources)
  try:
    contents = list(code_path.iterdir())
    return len(contents) > 0
  except OSError:
    return False


def is_artifact_code_indexed(group_id: str, artifact_id: str, version: str) -> bool:
  """Check if artifact is fully indexed (has .jar-indexer/index.json).

  Args:
    group_id: Maven group ID
    artifact_id: Maven artifact ID
    version: Maven version

  Returns:
    True if artifact is fully indexed

  Raises:
    ValueError: If Maven coordinates are invalid
  """
  # Get the artifact code path
  artifact_path = get_artifact_code_path(group_id, artifact_id, version)

  # Get the base directory from environment or use default ~/.jar-indexer
  base_dir = os.path.expanduser(os.environ.get("JAR_INDEXER_HOME", "~/.jar-indexer"))
  code_dir = os.path.join(base_dir, "code", artifact_path)

  code_path = Path(code_dir)
  if not code_path.exists() or not code_path.is_dir():
    return False

  # Check for .jar-indexer/index.json (Phase 1 indexing requirement)
  index_dir = code_path / ".jar-indexer"
  index_file = index_dir / "index.json"

  if not index_file.exists() or not index_file.is_file():
    return False

  # Verify index file is valid JSON
  try:
    with open(index_file, "r") as f:
      json.load(f)
    return True
  except (json.JSONDecodeError, OSError):
    return False


def get_registered_source_info(
  group_id: str, artifact_id: str, version: str
) -> RegisteredSourceInfo | None:
  """Retrieve registered source information for an artifact.

  Args:
    group_id: Maven group ID
    artifact_id: Maven artifact ID
    version: Maven version

  Returns:
    RegisteredSourceInfo if source is registered, None otherwise

  Raises:
    ValueError: If Maven coordinates are invalid
  """
  # Get the artifact path
  artifact_path = get_artifact_code_path(group_id, artifact_id, version)

  # Get the base directory from environment or use default ~/.jar-indexer
  base_dir = os.path.expanduser(os.environ.get("JAR_INDEXER_HOME", "~/.jar-indexer"))
  base_path = Path(base_dir)

  # Check different source types to determine what's registered

  # 1. Check for JAR source in source-jar/ directory
  jar_dir = base_path / "source-jar" / artifact_path
  if jar_dir.exists() and jar_dir.is_dir():
    # Look for JAR files
    jar_files = list(jar_dir.glob("*.jar"))
    if jar_files:
      jar_file = jar_files[0]  # Take the first JAR file found
      return RegisteredSourceInfo(
        group_id=group_id,
        artifact_id=artifact_id,
        version=version,
        source_uri=f"file://{jar_file.absolute()}",  # Reconstruct likely source URI
        git_ref=None,
        source_type="jar",
        local_path=f"source-jar/{artifact_path}",
      )

  # 2. Check for compressed directory source in source-dir/ directory
  source_dir = base_path / "source-dir" / artifact_path
  if source_dir.exists() and source_dir.is_dir():
    # Look for 7z files
    archive_files = list(source_dir.glob("*.7z"))
    if archive_files:
      return RegisteredSourceInfo(
        group_id=group_id,
        artifact_id=artifact_id,
        version=version,
        source_uri=f"file://{archive_files[0].absolute()}",  # Use archive path
        git_ref=None,
        source_type="directory",
        local_path=f"source-dir/{artifact_path}",
      )

  # 3. Check for Git source by looking for git-bare and code directories
  git_bare_path = artifact_path.rsplit("/", 1)[0]  # Remove version for git-bare path
  git_bare_dir = base_path / "git-bare" / git_bare_path
  code_dir = base_path / "code" / artifact_path

  if git_bare_dir.exists() and code_dir.exists():
    # This is likely a Git source
    # Try to determine git_ref by checking if there's a metadata file or other indicators
    git_ref = None

    # Check if there's a metadata file that might contain git_ref info
    metadata_file = code_dir / ".jar-indexer" / "metadata.json"
    if metadata_file.exists():
      try:
        with open(metadata_file, "r") as f:
          metadata = json.load(f)
          git_ref = metadata.get("git_ref")
      except (json.JSONDecodeError, OSError):
        pass

    # If no git_ref found in metadata, use default 'main'
    if git_ref is None:
      git_ref = "main"

    return RegisteredSourceInfo(
      group_id=group_id,
      artifact_id=artifact_id,
      version=version,
      source_uri="git://unknown",  # Cannot reliably reconstruct original Git URI
      git_ref=git_ref,
      source_type="git",
      local_path=f"code/{artifact_path}",
    )

  # 4. Check for directory source (code directory exists but no git-bare or compressed source)
  if code_dir.exists() and code_dir.is_dir():
    return RegisteredSourceInfo(
      group_id=group_id,
      artifact_id=artifact_id,
      version=version,
      source_uri=f"file://{code_dir.absolute()}",  # Use current code directory path
      git_ref=None,
      source_type="directory",
      local_path=f"code/{artifact_path}",
    )

  # No registered source found
  return None
