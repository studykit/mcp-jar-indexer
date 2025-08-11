"""Utilities for searching Maven and Gradle local caches for source JAR files."""

import os
import glob
from pathlib import Path
from typing import Optional, List


def get_maven_cache_paths() -> List[Path]:
  """Get Maven local repository cache paths."""
  paths: List[Path] = []

  # Default Maven local repository
  maven_home = Path.home() / ".m2" / "repository"
  if maven_home.exists():
    paths.append(maven_home)

  # Check M2_HOME environment variable
  m2_home = os.environ.get("M2_HOME")
  if m2_home:
    m2_repo = Path(m2_home) / "repository"
    if m2_repo.exists() and m2_repo not in paths:
      paths.append(m2_repo)

  return paths


def get_gradle_cache_paths() -> List[Path]:
  """Get Gradle cache paths."""
  paths: List[Path] = []

  # Default Gradle cache directory
  gradle_home = Path.home() / ".gradle" / "caches"
  if gradle_home.exists():
    paths.append(gradle_home)

  # Check GRADLE_HOME environment variable
  gradle_home_env = os.environ.get("GRADLE_HOME")
  if gradle_home_env:
    gradle_cache = Path(gradle_home_env) / "caches"
    if gradle_cache.exists() and gradle_cache not in paths:
      paths.append(gradle_cache)

  return paths


def search_maven_source_jars(
  group_id: str, artifact_id: str, version_filter: Optional[str] = None
) -> List[str]:
  """Search for source JARs in Maven local repositories."""
  maven_paths = get_maven_cache_paths()
  results: List[str] = []

  for maven_path in maven_paths:
    # Convert group_id dots to directory separators
    group_path = group_id.replace(".", "/")
    artifact_path = maven_path / group_path / artifact_id

    if not artifact_path.exists():
      continue

    if version_filter:
      # Search for specific version
      source_jar_path = (
        artifact_path / version_filter / f"{artifact_id}-{version_filter}-sources.jar"
      )
      if source_jar_path.exists() and source_jar_path.is_file():
        results.append(str(source_jar_path.absolute()))
    else:
      # Search all versions
      for version_dir in artifact_path.iterdir():
        if version_dir.is_dir():
          source_jar_path = version_dir / f"{artifact_id}-{version_dir.name}-sources.jar"
          if source_jar_path.exists() and source_jar_path.is_file():
            results.append(str(source_jar_path.absolute()))

  return results


def search_gradle_source_jars(
  group_id: str, artifact_id: str, version_filter: Optional[str] = None
) -> List[str]:
  """Search for source JARs in Gradle caches."""
  gradle_paths = get_gradle_cache_paths()
  results: List[str] = []

  for gradle_path in gradle_paths:
    # Gradle cache structure: modules-2/files-2.1/group_id/artifact_id/version/hash/artifact_id-version-sources.jar
    artifact_path = gradle_path / "modules-2" / "files-2.1" / group_id / artifact_id

    if not artifact_path.exists():
      continue

    if version_filter:
      # Search for specific version
      version_path = artifact_path / version_filter
      if version_path.exists():
        pattern = str(version_path / "*" / f"{artifact_id}-{version_filter}-sources.jar")
        matches = glob.glob(pattern)
        for match in matches:
          results.append(str(Path(match).absolute()))
    else:
      # Search all versions
      for version_dir in artifact_path.iterdir():
        if version_dir.is_dir():
          pattern = str(version_dir / "*" / f"{artifact_id}-{version_dir.name}-sources.jar")
          matches = glob.glob(pattern)
          for match in matches:
            results.append(str(Path(match).absolute()))

  return results


def search_cached_artifacts(
  group_id: str, artifact_id: str, version_filter: Optional[str] = None, cache_types: str = "maven,gradle"
) -> List[str]:
  """
  Search for source JAR files in Maven/Gradle local caches.

  Args:
    group_id: Maven group ID
    artifact_id: Maven artifact ID
    version_filter: Optional version filter (if None, searches all versions)
    cache_types: Comma-separated cache types to search ("maven", "gradle", "maven,gradle")

  Returns:
    List of absolute paths to found source JARs (empty if not found)
  """
  cache_list = [cache.strip().lower() for cache in cache_types.split(",")]
  results: List[str] = []

  # Search Maven cache first if requested
  if "maven" in cache_list:
    maven_results = search_maven_source_jars(group_id, artifact_id, version_filter)
    results.extend(maven_results)

  # Search Gradle cache if requested
  if "gradle" in cache_list:
    gradle_results = search_gradle_source_jars(group_id, artifact_id, version_filter)
    results.extend(gradle_results)

  # Remove duplicates while preserving order
  seen: set[str] = set()
  unique_results: List[str] = []
  for path in results:
    if path not in seen:
      seen.add(path)
      unique_results.append(path)

  return unique_results
