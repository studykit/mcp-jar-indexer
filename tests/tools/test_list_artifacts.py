"""Tests for list_artifacts MCP tool."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.tools.list_artifacts import (
  LIST_ARTIFACTS_TOOL,
  check_version_constraint,
  get_artifact_status,
  handle_list_artifacts,
  list_artifacts,
  parse_version_filter,
  scan_all_artifacts,
)
from src.core.storage import StorageManager


class TestParseVersionFilter:
  """Test version filter parsing."""

  def test_exact_version(self) -> None:
    """Test parsing exact version."""
    constraints = parse_version_filter("5.3.21")
    assert constraints == [("==", "5.3.21")]

  def test_greater_than(self) -> None:
    """Test parsing greater than constraint."""
    constraints = parse_version_filter(">5.3.0")
    assert constraints == [(">", "5.3.0")]

  def test_greater_than_or_equal(self) -> None:
    """Test parsing greater than or equal constraint."""
    constraints = parse_version_filter(">=5.3.0")
    assert constraints == [(">=", "5.3.0")]

  def test_less_than(self) -> None:
    """Test parsing less than constraint."""
    constraints = parse_version_filter("<6.0.0")
    assert constraints == [("<", "6.0.0")]

  def test_less_than_or_equal(self) -> None:
    """Test parsing less than or equal constraint."""
    constraints = parse_version_filter("<=6.0.0")
    assert constraints == [("<=", "6.0.0")]

  def test_multiple_constraints(self) -> None:
    """Test parsing multiple constraints."""
    constraints = parse_version_filter(">=5.0.0,<6.0.0")
    assert constraints == [(">=", "5.0.0"), ("<", "6.0.0")]

  def test_with_equals_sign(self) -> None:
    """Test parsing with explicit equals sign."""
    constraints = parse_version_filter("=5.3.21")
    assert constraints == [("==", "5.3.21")]


class TestCheckVersionConstraint:
  """Test version constraint checking."""

  def test_exact_match(self) -> None:
    """Test exact version match."""
    constraints = [("==", "5.3.21")]
    assert check_version_constraint("5.3.21", constraints) is True
    assert check_version_constraint("5.3.20", constraints) is False

  def test_greater_than(self) -> None:
    """Test greater than constraint."""
    constraints = [(">", "5.3.0")]
    assert check_version_constraint("5.3.1", constraints) is True
    assert check_version_constraint("5.3.0", constraints) is False
    assert check_version_constraint("5.2.9", constraints) is False

  def test_greater_than_or_equal(self) -> None:
    """Test greater than or equal constraint."""
    constraints = [(">=", "5.3.0")]
    assert check_version_constraint("5.3.0", constraints) is True
    assert check_version_constraint("5.3.1", constraints) is True
    assert check_version_constraint("5.2.9", constraints) is False

  def test_less_than(self) -> None:
    """Test less than constraint."""
    constraints = [("<", "6.0.0")]
    assert check_version_constraint("5.9.9", constraints) is True
    assert check_version_constraint("6.0.0", constraints) is False
    assert check_version_constraint("6.0.1", constraints) is False

  def test_less_than_or_equal(self) -> None:
    """Test less than or equal constraint."""
    constraints = [("<=", "6.0.0")]
    assert check_version_constraint("6.0.0", constraints) is True
    assert check_version_constraint("5.9.9", constraints) is True
    assert check_version_constraint("6.0.1", constraints) is False

  def test_multiple_constraints(self) -> None:
    """Test multiple constraints."""
    constraints = [(">=", "5.0.0"), ("<", "6.0.0")]
    assert check_version_constraint("5.5.0", constraints) is True
    assert check_version_constraint("4.9.9", constraints) is False
    assert check_version_constraint("6.0.0", constraints) is False

  def test_non_semver_version(self) -> None:
    """Test with non-semantic version strings."""
    constraints = [("==", "4.1.79.Final")]
    assert check_version_constraint("4.1.79.Final", constraints) is True
    assert check_version_constraint("4.1.78.Final", constraints) is False


class TestGetArtifactStatus:
  """Test artifact status determination."""

  def test_no_source(self, tmp_path: Path) -> None:
    """Test status when no source exists."""
    storage_manager = StorageManager(str(tmp_path))
    storage_manager.ensure_directories()

    status = get_artifact_status(storage_manager, "org.test", "test-artifact", "1.0.0")
    assert status == ""

  def test_jar_source_only(self, tmp_path: Path) -> None:
    """Test status with JAR source only."""
    storage_manager = StorageManager(str(tmp_path))
    storage_manager.ensure_directories()

    # Create JAR source
    jar_path = storage_manager.get_source_jar_path("org.test", "test-artifact", "1.0.0")
    jar_path.mkdir(parents=True, exist_ok=True)
    (jar_path / "test-artifact-1.0.0-sources.jar").touch()

    status = get_artifact_status(storage_manager, "org.test", "test-artifact", "1.0.0")
    assert status == "source-jar"

  def test_indexed_source(self, tmp_path: Path) -> None:
    """Test status with indexed source."""
    storage_manager = StorageManager(str(tmp_path))
    storage_manager.ensure_directories()

    # Create JAR source
    jar_path = storage_manager.get_source_jar_path("org.test", "test-artifact", "1.0.0")
    jar_path.mkdir(parents=True, exist_ok=True)
    (jar_path / "test-artifact-1.0.0-sources.jar").touch()

    # Create code directory with index file
    code_path = storage_manager.get_code_path("org.test", "test-artifact", "1.0.0")
    code_path.mkdir(parents=True, exist_ok=True)
    (code_path / ".indexed").touch()

    status = get_artifact_status(storage_manager, "org.test", "test-artifact", "1.0.0")
    assert "source-jar" in status
    # Note: 'index' status is not available in Phase 1 implementation

  def test_file_searchable_source(self, tmp_path: Path) -> None:
    """Test status with file-searchable source code."""
    storage_manager = StorageManager(str(tmp_path))
    storage_manager.ensure_directories()

    # Create JAR source
    jar_path = storage_manager.get_source_jar_path("org.test", "test-artifact", "1.0.0")
    jar_path.mkdir(parents=True, exist_ok=True)
    (jar_path / "test-artifact-1.0.0-sources.jar").touch()

    # Create code directory with source files
    code_path = storage_manager.get_code_path("org.test", "test-artifact", "1.0.0")
    code_path.mkdir(parents=True, exist_ok=True)
    (code_path / ".indexed").touch()
    (code_path / "TestClass.java").touch()

    status = get_artifact_status(storage_manager, "org.test", "test-artifact", "1.0.0")
    assert "source-jar" in status
    assert "file-searchable" in status
    # Note: 'index' status is not available in Phase 1 implementation

  def test_git_source(self, tmp_path: Path) -> None:
    """Test status with Git source."""
    storage_manager = StorageManager(str(tmp_path))
    storage_manager.ensure_directories()

    # Create Git bare repository
    git_path = storage_manager.get_git_bare_path("org.test", "test-artifact")
    git_path.mkdir(parents=True, exist_ok=True)
    (git_path / "HEAD").touch()

    # Create code directory with source files
    code_path = storage_manager.get_code_path("org.test", "test-artifact", "1.0.0")
    code_path.mkdir(parents=True, exist_ok=True)
    (code_path / "TestClass.java").touch()

    status = get_artifact_status(storage_manager, "org.test", "test-artifact", "1.0.0")
    assert "source-git" in status
    assert "file-searchable" in status


class TestScanAllArtifacts:
  """Test scanning all artifacts."""

  def test_scan_empty_storage(self, tmp_path: Path) -> None:
    """Test scanning empty storage."""
    storage_manager = StorageManager(str(tmp_path))
    storage_manager.ensure_directories()

    artifacts = scan_all_artifacts(storage_manager)
    assert artifacts == []

  def test_scan_jar_artifacts(self, tmp_path: Path) -> None:
    """Test scanning JAR artifacts."""
    storage_manager = StorageManager(str(tmp_path))
    storage_manager.ensure_directories()

    # Create JAR artifacts
    jar_path1 = storage_manager.get_source_jar_path("org.test", "artifact1", "1.0.0")
    jar_path1.mkdir(parents=True, exist_ok=True)
    (jar_path1 / "artifact1-1.0.0-sources.jar").touch()

    jar_path2 = storage_manager.get_source_jar_path("org.test", "artifact2", "2.0.0")
    jar_path2.mkdir(parents=True, exist_ok=True)
    (jar_path2 / "artifact2-2.0.0-sources.jar").touch()

    artifacts = scan_all_artifacts(storage_manager)
    assert len(artifacts) == 2

    # Check artifact details
    artifact_coords = [
      (a["group_id"], a["artifact_id"], a["version"]) for a in artifacts
    ]
    assert ("org.test", "artifact1", "1.0.0") in artifact_coords
    assert ("org.test", "artifact2", "2.0.0") in artifact_coords

  def test_scan_git_artifacts(self, tmp_path: Path) -> None:
    """Test scanning Git artifacts."""
    storage_manager = StorageManager(str(tmp_path))
    storage_manager.ensure_directories()

    # Create Git repository
    git_path = storage_manager.get_git_bare_path("org.test", "git-artifact")
    git_path.mkdir(parents=True, exist_ok=True)
    (git_path / "HEAD").touch()

    # Create multiple versions in code directory
    code_path1 = storage_manager.get_code_path("org.test", "git-artifact", "1.0.0")
    code_path1.mkdir(parents=True, exist_ok=True)
    (code_path1 / "TestClass.java").touch()

    code_path2 = storage_manager.get_code_path("org.test", "git-artifact", "2.0.0")
    code_path2.mkdir(parents=True, exist_ok=True)
    (code_path2 / "TestClass.java").touch()

    artifacts = scan_all_artifacts(storage_manager)
    assert len(artifacts) == 2

    # Check artifact details
    artifact_coords = [
      (a["group_id"], a["artifact_id"], a["version"]) for a in artifacts
    ]
    assert ("org.test", "git-artifact", "1.0.0") in artifact_coords
    assert ("org.test", "git-artifact", "2.0.0") in artifact_coords

  def test_scan_no_duplicates(self, tmp_path: Path) -> None:
    """Test that scanning doesn't create duplicates."""
    storage_manager = StorageManager(str(tmp_path))
    storage_manager.ensure_directories()

    # Create artifact in multiple locations
    jar_path = storage_manager.get_source_jar_path("org.test", "artifact", "1.0.0")
    jar_path.mkdir(parents=True, exist_ok=True)
    (jar_path / "artifact-1.0.0-sources.jar").touch()

    code_path = storage_manager.get_code_path("org.test", "artifact", "1.0.0")
    code_path.mkdir(parents=True, exist_ok=True)
    (code_path / "TestClass.java").touch()

    artifacts = scan_all_artifacts(storage_manager)
    assert len(artifacts) == 1
    assert artifacts[0]["group_id"] == "org.test"
    assert artifacts[0]["artifact_id"] == "artifact"
    assert artifacts[0]["version"] == "1.0.0"


class TestListArtifacts:
  """Test list_artifacts function."""

  @pytest.mark.asyncio
  async def test_list_all_artifacts(self, tmp_path: Path) -> None:
    """Test listing all artifacts without filters."""
    storage_manager = StorageManager(str(tmp_path))
    storage_manager.ensure_directories()

    # Create test artifacts
    jar_path1 = storage_manager.get_source_jar_path("org.test", "artifact1", "1.0.0")
    jar_path1.mkdir(parents=True, exist_ok=True)
    (jar_path1 / "artifact1-1.0.0-sources.jar").touch()

    jar_path2 = storage_manager.get_source_jar_path("com.example", "artifact2", "2.0.0")
    jar_path2.mkdir(parents=True, exist_ok=True)
    (jar_path2 / "artifact2-2.0.0-sources.jar").touch()

    with patch("src.tools.list_artifacts.StorageManager") as mock_storage:
      mock_storage.return_value = storage_manager

      result = await list_artifacts()

      assert result["status"] == "success"
      assert result["pagination"]["total_count"] == 2
      assert len(result["artifacts"]) == 2

  @pytest.mark.asyncio
  async def test_list_with_group_filter(self, tmp_path: Path) -> None:
    """Test listing with group filter."""
    storage_manager = StorageManager(str(tmp_path))
    storage_manager.ensure_directories()

    # Create test artifacts
    jar_path1 = storage_manager.get_source_jar_path("org.test", "artifact1", "1.0.0")
    jar_path1.mkdir(parents=True, exist_ok=True)
    (jar_path1 / "artifact1-1.0.0-sources.jar").touch()

    jar_path2 = storage_manager.get_source_jar_path("com.example", "artifact2", "2.0.0")
    jar_path2.mkdir(parents=True, exist_ok=True)
    (jar_path2 / "artifact2-2.0.0-sources.jar").touch()

    with patch("src.tools.list_artifacts.StorageManager") as mock_storage:
      mock_storage.return_value = storage_manager

      result = await list_artifacts(group_filter="org.test")

      assert result["status"] == "success"
      assert result["pagination"]["total_count"] == 1
      assert len(result["artifacts"]) == 1
      assert result["artifacts"][0]["group_id"] == "org.test"

  @pytest.mark.asyncio
  async def test_list_with_artifact_filter(self, tmp_path: Path) -> None:
    """Test listing with artifact filter."""
    storage_manager = StorageManager(str(tmp_path))
    storage_manager.ensure_directories()

    # Create test artifacts
    jar_path1 = storage_manager.get_source_jar_path("org.test", "artifact1", "1.0.0")
    jar_path1.mkdir(parents=True, exist_ok=True)
    (jar_path1 / "artifact1-1.0.0-sources.jar").touch()

    jar_path2 = storage_manager.get_source_jar_path("org.test", "other", "2.0.0")
    jar_path2.mkdir(parents=True, exist_ok=True)
    (jar_path2 / "other-2.0.0-sources.jar").touch()

    with patch("src.tools.list_artifacts.StorageManager") as mock_storage:
      mock_storage.return_value = storage_manager

      result = await list_artifacts(artifact_filter="artifact")

      assert result["status"] == "success"
      assert result["pagination"]["total_count"] == 1
      assert len(result["artifacts"]) == 1
      assert result["artifacts"][0]["artifact_id"] == "artifact1"

  @pytest.mark.asyncio
  async def test_list_with_version_filter(self, tmp_path: Path) -> None:
    """Test listing with version filter."""
    storage_manager = StorageManager(str(tmp_path))
    storage_manager.ensure_directories()

    # Create test artifacts with different versions
    for version in ["1.0.0", "1.5.0", "2.0.0", "2.5.0"]:
      jar_path = storage_manager.get_source_jar_path("org.test", "artifact", version)
      jar_path.mkdir(parents=True, exist_ok=True)
      (jar_path / f"artifact-{version}-sources.jar").touch()

    with patch("src.tools.list_artifacts.StorageManager") as mock_storage:
      mock_storage.return_value = storage_manager

      # Test with range filter
      result = await list_artifacts(version_filter=">=1.5.0,<2.5.0")

      assert result["status"] == "success"
      assert result["pagination"]["total_count"] == 2
      versions = [a["version"] for a in result["artifacts"]]
      assert "1.5.0" in versions
      assert "2.0.0" in versions
      assert "1.0.0" not in versions
      assert "2.5.0" not in versions

  @pytest.mark.asyncio
  async def test_list_with_status_filter(self, tmp_path: Path) -> None:
    """Test listing with status filter."""
    storage_manager = StorageManager(str(tmp_path))
    storage_manager.ensure_directories()

    # Create artifact with only source
    jar_path1 = storage_manager.get_source_jar_path("org.test", "artifact1", "1.0.0")
    jar_path1.mkdir(parents=True, exist_ok=True)
    (jar_path1 / "artifact1-1.0.0-sources.jar").touch()

    # Create artifact with source and index
    jar_path2 = storage_manager.get_source_jar_path("org.test", "artifact2", "2.0.0")
    jar_path2.mkdir(parents=True, exist_ok=True)
    (jar_path2 / "artifact2-2.0.0-sources.jar").touch()
    code_path2 = storage_manager.get_code_path("org.test", "artifact2", "2.0.0")
    code_path2.mkdir(parents=True, exist_ok=True)
    (code_path2 / ".indexed").touch()
    (code_path2 / "TestClass.java").touch()

    with patch("src.tools.list_artifacts.StorageManager") as mock_storage:
      mock_storage.return_value = storage_manager

      # Filter for file-searchable artifacts
      result = await list_artifacts(status_filter="file-searchable")

      assert result["status"] == "success"
      # Note: Due to code directory scanning, we might get multiple artifacts
      # Find the correct artifact2
      artifact2_found = False
      for artifact in result["artifacts"]:
        if artifact["artifact_id"] == "artifact2" and artifact["version"] == "2.0.0":
          artifact2_found = True
          assert "file-searchable" in artifact["status"]
          break
      assert artifact2_found, "artifact2 with version 2.0.0 not found"

  @pytest.mark.asyncio
  async def test_list_with_pagination(self, tmp_path: Path) -> None:
    """Test listing with pagination."""
    storage_manager = StorageManager(str(tmp_path))
    storage_manager.ensure_directories()

    # Create multiple artifacts
    for i in range(5):
      jar_path = storage_manager.get_source_jar_path(
        "org.test", f"artifact{i}", "1.0.0"
      )
      jar_path.mkdir(parents=True, exist_ok=True)
      (jar_path / f"artifact{i}-1.0.0-sources.jar").touch()

    with patch("src.tools.list_artifacts.StorageManager") as mock_storage:
      mock_storage.return_value = storage_manager

      # Get first page
      result = await list_artifacts(page=1, page_size=2)

      assert result["status"] == "success"
      assert result["pagination"]["page"] == 1
      assert result["pagination"]["total_count"] == 5
      assert result["pagination"]["total_pages"] == 3
      assert len(result["artifacts"]) == 2

      # Get second page
      result = await list_artifacts(page=2, page_size=2)

      assert result["pagination"]["page"] == 2
      assert len(result["artifacts"]) == 2

      # Get last page
      result = await list_artifacts(page=3, page_size=2)

      assert result["pagination"]["page"] == 3
      assert len(result["artifacts"]) == 1

  @pytest.mark.asyncio
  async def test_list_error_handling(self):
    """Test error handling in list_artifacts."""
    with patch("src.tools.list_artifacts.StorageManager") as mock_storage:
      mock_storage.side_effect = Exception("Storage error")

      result = await list_artifacts()

      assert result["status"] == "internal_error"
      assert "Storage error" in result["message"]
      assert result["artifacts"] == []


class TestHandleListArtifacts:
  """Test handle_list_artifacts MCP handler."""

  @pytest.mark.asyncio
  async def test_handle_success(self, tmp_path: Path) -> None:
    """Test successful MCP tool call."""
    storage_manager = StorageManager(str(tmp_path))
    storage_manager.ensure_directories()

    jar_path = storage_manager.get_source_jar_path("org.test", "artifact", "1.0.0")
    jar_path.mkdir(parents=True, exist_ok=True)
    (jar_path / "artifact-1.0.0-sources.jar").touch()

    with patch("src.tools.list_artifacts.StorageManager") as mock_storage:
      mock_storage.return_value = storage_manager

      result = await handle_list_artifacts({})

      assert len(result) == 1
      assert result[0].type == "text"

      data = json.loads(result[0].text)
      assert data["status"] == "success"
      assert len(data["artifacts"]) == 1

  @pytest.mark.asyncio
  async def test_handle_with_filters(self, tmp_path: Path) -> None:
    """Test MCP tool call with filters."""
    storage_manager = StorageManager(str(tmp_path))
    storage_manager.ensure_directories()

    # Create multiple artifacts
    for version in ["1.0.0", "2.0.0", "3.0.0"]:
      jar_path = storage_manager.get_source_jar_path("org.test", "artifact", version)
      jar_path.mkdir(parents=True, exist_ok=True)
      (jar_path / f"artifact-{version}-sources.jar").touch()

    with patch("src.tools.list_artifacts.StorageManager") as mock_storage:
      mock_storage.return_value = storage_manager

      arguments = {
        "group_filter": "org.test",
        "version_filter": ">=2.0.0",
        "page": 1,
        "page_size": 10,
      }

      result = await handle_list_artifacts(arguments)

      assert len(result) == 1
      data = json.loads(result[0].text)
      assert data["status"] == "success"
      assert len(data["artifacts"]) == 2
      versions = [a["version"] for a in data["artifacts"]]
      assert "2.0.0" in versions
      assert "3.0.0" in versions

  @pytest.mark.asyncio
  async def test_handle_error(self):
    """Test MCP tool call error handling."""
    with patch("src.tools.list_artifacts.list_artifacts") as mock_list:
      mock_list.side_effect = Exception("Test error")

      result = await handle_list_artifacts({})

      assert len(result) == 1
      data = json.loads(result[0].text)
      assert data["status"] == "internal_error"
      assert "Test error" in data["message"]


class TestToolDefinition:
  """Test MCP tool definition."""

  def test_tool_metadata(self) -> None:
    """Test tool metadata is correct."""
    assert LIST_ARTIFACTS_TOOL.name == "list_artifacts"
    assert (
      LIST_ARTIFACTS_TOOL.description is not None
      and "List all artifacts" in LIST_ARTIFACTS_TOOL.description
    )
    assert LIST_ARTIFACTS_TOOL.inputSchema["type"] == "object"

  def test_tool_parameters(self) -> None:
    """Test tool parameter definitions."""
    properties = LIST_ARTIFACTS_TOOL.inputSchema["properties"]

    # Check pagination parameters
    assert "page" in properties
    assert properties["page"]["type"] == "integer"
    assert properties["page"]["minimum"] == 1

    assert "page_size" in properties
    assert properties["page_size"]["type"] == "integer"
    assert properties["page_size"]["maximum"] == 100

    # Check filter parameters
    assert "group_filter" in properties
    assert properties["group_filter"]["type"] == "string"

    assert "artifact_filter" in properties
    assert properties["artifact_filter"]["type"] == "string"

    assert "version_filter" in properties
    assert properties["version_filter"]["type"] == "string"

    assert "status_filter" in properties
    assert properties["status_filter"]["type"] == "string"

  def test_no_required_parameters(self) -> None:
    """Test that no parameters are required."""
    assert LIST_ARTIFACTS_TOOL.inputSchema["required"] == []
