"""Tests for cache_utils module."""

import os
import tempfile
from pathlib import Path
from typing import Iterable
from unittest.mock import patch

import pytest

from src.utils.cache_utils import (
  get_gradle_cache_paths,
  get_maven_cache_paths,
  search_cached_artifacts,
  search_gradle_source_jars,
  search_maven_source_jars,
)


class TestCacheUtils:
  """Test cases for cache utilities."""

  @pytest.fixture
  def temp_maven_repo(self) -> Iterable[Path]:
    """Create temporary Maven repository."""
    with tempfile.TemporaryDirectory() as temp_dir:
      maven_repo = Path(temp_dir) / ".m2" / "repository"
      maven_repo.mkdir(parents=True, exist_ok=True)
      yield maven_repo

  @pytest.fixture
  def temp_gradle_cache(self) -> Iterable[Path]:
    """Create temporary Gradle cache."""
    with tempfile.TemporaryDirectory() as temp_dir:
      gradle_cache = Path(temp_dir) / ".gradle" / "caches"
      gradle_cache.mkdir(parents=True, exist_ok=True)
      yield gradle_cache

  def test_get_maven_cache_paths_default(self, temp_maven_repo: Path) -> None:
    """Test getting default Maven cache paths."""
    with patch("pathlib.Path.home", return_value=temp_maven_repo.parent.parent):
      paths = get_maven_cache_paths()
      assert len(paths) == 1
      assert paths[0] == temp_maven_repo

  def test_get_maven_cache_paths_with_m2_home(self, temp_maven_repo: Path) -> None:
    """Test getting Maven cache paths with M2_HOME."""
    m2_home = temp_maven_repo.parent.parent / "custom_maven"
    m2_home.mkdir(parents=True, exist_ok=True)
    custom_repo = m2_home / "repository"
    custom_repo.mkdir(parents=True, exist_ok=True)

    with patch.dict(os.environ, {"M2_HOME": str(m2_home)}), patch(
      "pathlib.Path.home", return_value=Path("/nonexistent")
    ):
      paths = get_maven_cache_paths()
      assert custom_repo in paths

  def test_get_gradle_cache_paths_default(self, temp_gradle_cache: Path) -> None:
    """Test getting default Gradle cache paths."""
    with patch(
      "pathlib.Path.home", return_value=temp_gradle_cache.parent.parent
    ):
      paths = get_gradle_cache_paths()
      assert len(paths) == 1
      assert paths[0] == temp_gradle_cache

  def test_get_gradle_cache_paths_with_gradle_home(
    self, temp_gradle_cache: Path
  ) -> None:
    """Test getting Gradle cache paths with GRADLE_HOME."""
    gradle_home = temp_gradle_cache.parent.parent / "custom_gradle"
    gradle_home.mkdir(parents=True, exist_ok=True)
    custom_cache = gradle_home / "caches"
    custom_cache.mkdir(parents=True, exist_ok=True)

    with patch.dict(os.environ, {"GRADLE_HOME": str(gradle_home)}), patch(
      "pathlib.Path.home", return_value=Path("/nonexistent")
    ):
      paths = get_gradle_cache_paths()
      assert custom_cache in paths

  def test_search_maven_source_jars_specific_version(
    self, temp_maven_repo: Path
  ) -> None:
    """Test successful Maven source JAR search for specific version."""
    # Create Maven repository structure
    group_path = temp_maven_repo / "org" / "springframework" / "spring-core" / "5.3.21"
    group_path.mkdir(parents=True, exist_ok=True)

    source_jar = group_path / "spring-core-5.3.21-sources.jar"
    source_jar.write_text("mock jar content")

    with patch(
      "src.utils.cache_utils.get_maven_cache_paths", return_value=[temp_maven_repo]
    ):
      result = search_maven_source_jars(
        "org.springframework", "spring-core", "5.3.21"
      )

      assert len(result) == 1
      assert result[0] == str(source_jar.absolute())

  def test_search_maven_source_jars_all_versions(
    self, temp_maven_repo: Path
  ) -> None:
    """Test Maven source JAR search for all versions."""
    # Create multiple versions
    versions = ["5.3.21", "6.0.0", "6.0.1"]
    expected_jars: list[str] = []

    for version in versions:
      group_path = (
        temp_maven_repo / "org" / "springframework" / "spring-core" / version
      )
      group_path.mkdir(parents=True, exist_ok=True)
      source_jar = group_path / f"spring-core-{version}-sources.jar"
      source_jar.write_text("mock jar content")
      expected_jars.append(str(source_jar.absolute()))

    with patch(
      "src.utils.cache_utils.get_maven_cache_paths", return_value=[temp_maven_repo]
    ):
      result = search_maven_source_jars("org.springframework", "spring-core", None)

      assert len(result) == 3
      assert set(result) == set(expected_jars)

  def test_search_maven_source_jars_not_found(self, temp_maven_repo: Path) -> None:
    """Test Maven source JAR not found."""
    with patch(
      "src.utils.cache_utils.get_maven_cache_paths", return_value=[temp_maven_repo]
    ):
      result = search_maven_source_jars("org.example", "nonexistent", "1.0.0")

      assert result == []

  def test_search_gradle_source_jars_specific_version(
    self, temp_gradle_cache: Path
  ) -> None:
    """Test successful Gradle source JAR search for specific version."""
    # Create Gradle cache structure
    gradle_path = (
      temp_gradle_cache
      / "modules-2"
      / "files-2.1"
      / "org.springframework"
      / "spring-core"
      / "5.3.21"
      / "abc123def456"
    )
    gradle_path.mkdir(parents=True, exist_ok=True)

    source_jar = gradle_path / "spring-core-5.3.21-sources.jar"
    source_jar.write_text("mock jar content")

    with patch(
      "src.utils.cache_utils.get_gradle_cache_paths", return_value=[temp_gradle_cache]
    ):
      result = search_gradle_source_jars(
        "org.springframework", "spring-core", "5.3.21"
      )

      assert len(result) == 1
      assert result[0] == str(source_jar.absolute())

  def test_search_gradle_source_jars_all_versions(
    self, temp_gradle_cache: Path
  ) -> None:
    """Test Gradle source JAR search for all versions."""
    versions = ["5.3.21", "6.0.0"]
    expected_jars: list[str] = []

    for version in versions:
      gradle_path = (
        temp_gradle_cache
        / "modules-2"
        / "files-2.1"
        / "org.springframework"
        / "spring-core"
        / version
        / f"hash_{version}"
      )
      gradle_path.mkdir(parents=True, exist_ok=True)
      source_jar = gradle_path / f"spring-core-{version}-sources.jar"
      source_jar.write_text("mock jar content")
      expected_jars.append(str(source_jar.absolute()))

    with patch(
      "src.utils.cache_utils.get_gradle_cache_paths", return_value=[temp_gradle_cache]
    ):
      result = search_gradle_source_jars("org.springframework", "spring-core", None)

      assert len(result) == 2
      assert set(result) == set(expected_jars)

  def test_search_gradle_source_jars_not_found(
    self, temp_gradle_cache: Path
  ) -> None:
    """Test Gradle source JAR not found."""
    with patch(
      "src.utils.cache_utils.get_gradle_cache_paths", return_value=[temp_gradle_cache]
    ):
      result = search_gradle_source_jars("org.example", "nonexistent", "1.0.0")

      assert result == []

  def test_search_cached_artifacts_maven_only(self, temp_maven_repo: Path) -> None:
    """Test searching cached source JAR in Maven only."""
    # Create Maven source JAR
    group_path = temp_maven_repo / "org" / "springframework" / "spring-core" / "5.3.21"
    group_path.mkdir(parents=True, exist_ok=True)
    source_jar = group_path / "spring-core-5.3.21-sources.jar"
    source_jar.write_text("mock jar content")

    with patch(
      "src.utils.cache_utils.get_maven_cache_paths", return_value=[temp_maven_repo]
    ):
      result = search_cached_artifacts(
        "org.springframework", "spring-core", "5.3.21", "maven"
      )

      assert len(result) == 1
      assert result[0] == str(source_jar.absolute())

  def test_search_cached_artifacts_gradle_only(
    self, temp_gradle_cache: Path
  ) -> None:
    """Test searching cached source JAR in Gradle only."""
    # Create Gradle source JAR
    gradle_path = (
      temp_gradle_cache
      / "modules-2"
      / "files-2.1"
      / "org.springframework"
      / "spring-core"
      / "5.3.21"
      / "abc123def456"
    )
    gradle_path.mkdir(parents=True, exist_ok=True)
    source_jar = gradle_path / "spring-core-5.3.21-sources.jar"
    source_jar.write_text("mock jar content")

    with patch(
      "src.utils.cache_utils.get_gradle_cache_paths", return_value=[temp_gradle_cache]
    ):
      result = search_cached_artifacts(
        "org.springframework", "spring-core", "5.3.21", "gradle"
      )

      assert len(result) == 1
      assert result[0] == str(source_jar.absolute())

  def test_search_cached_artifacts_both_caches(
    self, temp_maven_repo: Path, temp_gradle_cache: Path
  ) -> None:
    """Test searching cached source JAR in both caches."""
    # Create Maven source JAR
    maven_group_path = (
      temp_maven_repo / "org" / "springframework" / "spring-core" / "5.3.21"
    )
    maven_group_path.mkdir(parents=True, exist_ok=True)
    maven_jar = maven_group_path / "spring-core-5.3.21-sources.jar"
    maven_jar.write_text("mock jar content")

    # Create Gradle source JAR
    gradle_path = (
      temp_gradle_cache
      / "modules-2"
      / "files-2.1"
      / "org.springframework"
      / "spring-core"
      / "5.3.21"
      / "abc123def456"
    )
    gradle_path.mkdir(parents=True, exist_ok=True)
    gradle_jar = gradle_path / "spring-core-5.3.21-sources.jar"
    gradle_jar.write_text("mock jar content")

    with patch(
      "src.utils.cache_utils.get_maven_cache_paths", return_value=[temp_maven_repo]
    ), patch(
      "src.utils.cache_utils.get_gradle_cache_paths", return_value=[temp_gradle_cache]
    ):
      result = search_cached_artifacts(
        "org.springframework", "spring-core", "5.3.21", "maven,gradle"
      )

      assert len(result) == 2
      assert str(maven_jar.absolute()) in result
      assert str(gradle_jar.absolute()) in result

  def test_search_cached_artifacts_all_versions(
    self, temp_maven_repo: Path
  ) -> None:
    """Test searching all cached versions."""
    versions = ["5.3.21", "6.0.0", "6.0.1"]
    expected_jars: list[str] = []

    for version in versions:
      group_path = (
        temp_maven_repo / "org" / "springframework" / "spring-core" / version
      )
      group_path.mkdir(parents=True, exist_ok=True)
      source_jar = group_path / f"spring-core-{version}-sources.jar"
      source_jar.write_text("mock jar content")
      expected_jars.append(str(source_jar.absolute()))

    with patch(
      "src.utils.cache_utils.get_maven_cache_paths", return_value=[temp_maven_repo]
    ):
      result = search_cached_artifacts(
        "org.springframework", "spring-core", None, "maven"
      )

      assert len(result) == 3
      assert set(result) == set(expected_jars)

  def test_search_cached_artifacts_not_found(self) -> None:
    """Test searching cached source JAR not found."""
    with patch(
      "src.utils.cache_utils.get_maven_cache_paths", return_value=[]
    ), patch("src.utils.cache_utils.get_gradle_cache_paths", return_value=[]):
      result = search_cached_artifacts(
        "org.example", "nonexistent", "1.0.0", "maven,gradle"
      )

      assert result == []

  def test_search_cached_artifacts_invalid_cache_type(self) -> None:
    """Test searching with invalid cache type."""
    result = search_cached_artifacts(
      "org.springframework", "spring-core", "5.3.21", "invalid"
    )

    assert result == []

  def test_search_cached_artifacts_deduplication(
    self, temp_maven_repo: Path
  ) -> None:
    """Test duplicate removal in search results."""
    # Create same JAR in multiple Maven repositories
    group_path1 = (
      temp_maven_repo / "org" / "springframework" / "spring-core" / "5.3.21"
    )
    group_path1.mkdir(parents=True, exist_ok=True)
    source_jar1 = group_path1 / "spring-core-5.3.21-sources.jar"
    source_jar1.write_text("mock jar content")

    # Create second Maven repo with same structure
    maven_repo2 = temp_maven_repo.parent / "m2_2" / "repository"
    group_path2 = (
      maven_repo2 / "org" / "springframework" / "spring-core" / "5.3.21"
    )
    group_path2.mkdir(parents=True, exist_ok=True)
    source_jar2 = group_path2 / "spring-core-5.3.21-sources.jar"
    source_jar2.write_text("mock jar content")

    with patch(
      "src.utils.cache_utils.get_maven_cache_paths",
      return_value=[temp_maven_repo, maven_repo2],
    ):
      result = search_cached_artifacts(
        "org.springframework", "spring-core", "5.3.21", "maven"
      )

      # Should find both but they are different paths
      assert len(result) == 2
      assert str(source_jar1.absolute()) in result
      assert str(source_jar2.absolute()) in result