"""Test filesystem exploration utilities."""

import tempfile
from pathlib import Path
import pytest

from src.utils.filesystem_exploration import (
  get_file_info,
  list_directory_tree,
  get_file_content,
  search_files_by_pattern,
  search_file_contents,
)
# FileInfo type is tested through the functions that use it


class TestGetFileInfo:
  """Test get_file_info function."""

  @pytest.fixture
  def temp_dir(self) -> Path:
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmp_dir:
      yield Path(tmp_dir)

  def test_get_file_info_text_file(self, temp_dir: Path) -> None:
    """Test file info for a text file."""
    test_file = temp_dir / "test.txt"
    test_file.write_text("line 1\nline 2\ntest content")

    info = get_file_info(str(test_file))

    assert info["name"] == "test.txt"
    assert info["line_count"] == 3
    assert "B" in info["size"] or "KB" in info["size"]

  def test_get_file_info_empty_file(self, temp_dir: Path) -> None:
    """Test file info for an empty file."""
    empty_file = temp_dir / "empty.txt"
    empty_file.touch()

    info = get_file_info(str(empty_file))

    assert info["name"] == "empty.txt"
    assert info["line_count"] == 0
    assert info["size"] == "0B"

  def test_get_file_info_binary_file(self, temp_dir: Path) -> None:
    """Test file info for a binary file."""
    binary_file = temp_dir / "binary.bin"
    binary_file.write_bytes(b"\x00\x01\x02\x03")

    info = get_file_info(str(binary_file))

    assert info["name"] == "binary.bin"
    assert info["line_count"] == 0  # Binary file should have 0 lines
    assert "B" in info["size"]

  def test_get_file_info_nonexistent(self, temp_dir: Path) -> None:
    """Test file info for nonexistent path."""
    nonexistent = temp_dir / "nonexistent.txt"

    with pytest.raises(ValueError, match="Path does not exist"):
      get_file_info(str(nonexistent))

  def test_get_file_info_directory(self, temp_dir: Path) -> None:
    """Test file info raises error for directory."""
    with pytest.raises(ValueError, match="Path is not a file"):
      get_file_info(str(temp_dir))


class TestListDirectoryTree:
  """Test list_directory_tree function."""

  @pytest.fixture
  def sample_directory(self, tmp_path: Path) -> Path:
    """Create sample directory structure for testing."""
    # Create directory structure
    (tmp_path / "file1.txt").write_text("content1")
    (tmp_path / "file2.java").write_text("public class Test {}")

    subdir1 = tmp_path / "subdir1"
    subdir1.mkdir()
    (subdir1 / "nested1.txt").write_text("nested content")

    subdir2 = tmp_path / "subdir2"
    subdir2.mkdir()
    (subdir2 / "nested2.java").write_text("public class Nested {}")

    deep_dir = subdir1 / "deep"
    deep_dir.mkdir()
    (deep_dir / "deep_file.txt").write_text("deep content")

    return tmp_path

  def test_list_directory_tree_basic(self, sample_directory: Path) -> None:
    """Test basic directory tree listing."""
    result = list_directory_tree(str(sample_directory))

    assert result["path"] == ""
    assert result["max_depth"] == 1
    assert len(result["files"]) == 2  # file1.txt, file2.java
    assert len(result["folders"]) == 2  # subdir1, subdir2

    # Check file names
    file_names = {f["name"] for f in result["files"]}
    assert file_names == {"file1.txt", "file2.java"}

    # Check folder names
    folder_names = {f["name"] for f in result["folders"]}
    assert folder_names == {"subdir1", "subdir2"}

  def test_list_directory_tree_max_depth_2(self, sample_directory: Path) -> None:
    """Test directory tree listing with max depth 2."""
    result = list_directory_tree(str(sample_directory), max_depth=2)

    assert result["max_depth"] == 2

    # Find subdir1 in folders
    subdir1 = next(f for f in result["folders"] if f["name"] == "subdir1")
    assert len(subdir1["files"]) == 1  # nested1.txt
    assert len(subdir1["folders"]) == 1  # deep

  def test_list_directory_tree_start_path(self, sample_directory: Path) -> None:
    """Test directory tree listing from specific start path."""
    result = list_directory_tree(str(sample_directory), start_path="subdir1")

    assert result["path"] == "subdir1"
    assert len(result["files"]) == 1  # nested1.txt
    assert len(result["folders"]) == 1  # deep

  def test_list_directory_tree_no_files(self, sample_directory: Path) -> None:
    """Test directory tree listing without files."""
    result = list_directory_tree(str(sample_directory), include_files=False)

    assert len(result["files"]) == 0
    assert len(result["folders"]) == 2

  def test_list_directory_tree_nonexistent_start(self, sample_directory: Path) -> None:
    """Test directory tree with nonexistent start path."""
    with pytest.raises(ValueError, match="Start path does not exist"):
      list_directory_tree(str(sample_directory), start_path="nonexistent")


class TestGetFileContent:
  """Test get_file_content function."""

  @pytest.fixture
  def sample_file(self, tmp_path: Path) -> Path:
    """Create sample file for testing."""
    file_path = tmp_path / "sample.txt"
    content = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n"
    file_path.write_text(content)
    return file_path

  @pytest.fixture
  def base_dir(self, tmp_path: Path) -> Path:
    """Create base directory with sample file."""
    file_path = tmp_path / "sample.txt"
    content = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n"
    file_path.write_text(content)
    return tmp_path

  def test_get_file_content_full_file(self, base_dir: Path) -> None:
    """Test reading full file content."""
    result = get_file_content(str(base_dir), "sample.txt")

    assert result["file_info"]["name"] == "sample.txt"
    assert result["content"]["start_line"] == 1
    assert result["content"]["end_line"] == 5
    assert "Line 1" in result["content"]["source_code"]
    assert "Line 5" in result["content"]["source_code"]

  def test_get_file_content_line_range(self, base_dir: Path) -> None:
    """Test reading specific line range."""
    result = get_file_content(str(base_dir), "sample.txt", start_line=2, end_line=4)

    assert result["content"]["start_line"] == 2
    assert result["content"]["end_line"] == 4
    assert "Line 2" in result["content"]["source_code"]
    assert "Line 4" in result["content"]["source_code"]
    assert "Line 1" not in result["content"]["source_code"]
    assert "Line 5" not in result["content"]["source_code"]

  def test_get_file_content_start_line_only(self, base_dir: Path) -> None:
    """Test reading from specific start line."""
    result = get_file_content(str(base_dir), "sample.txt", start_line=3)

    assert result["content"]["start_line"] == 3
    assert result["content"]["end_line"] == 5
    assert "Line 3" in result["content"]["source_code"]
    assert "Line 5" in result["content"]["source_code"]
    assert "Line 1" not in result["content"]["source_code"]

  def test_get_file_content_nonexistent_file(self, base_dir: Path) -> None:
    """Test reading nonexistent file."""
    with pytest.raises(FileNotFoundError, match="File does not exist"):
      get_file_content(str(base_dir), "nonexistent.txt")


class TestSearchFilesByPattern:
  """Test search_files_by_pattern function."""

  @pytest.fixture
  def sample_directory(self, tmp_path: Path) -> Path:
    """Create sample directory with various files."""
    (tmp_path / "Test.java").write_text("public class Test {}")
    (tmp_path / "Utils.java").write_text("public class Utils {}")
    (tmp_path / "readme.txt").write_text("readme content")
    (tmp_path / "config.xml").write_text("<config></config>")

    subdir = tmp_path / "com" / "example"
    subdir.mkdir(parents=True)
    (subdir / "Main.java").write_text("public class Main {}")
    (subdir / "helper.py").write_text("def help(): pass")

    return tmp_path

  def test_search_files_by_pattern_glob_java(self, sample_directory: Path) -> None:
    """Test searching Java files with glob pattern."""
    result = search_files_by_pattern(str(sample_directory), "*.java", "glob")

    java_files = {f["name"] for f in result["files"]}
    assert "Test.java" in java_files
    assert "Utils.java" in java_files
    assert "readme.txt" not in java_files

  def test_search_files_by_pattern_regex(self, sample_directory: Path) -> None:
    """Test searching with regex pattern."""
    result = search_files_by_pattern(str(sample_directory), r".*\.java$", "regex")

    java_files = {f["name"] for f in result["files"]}
    assert "Test.java" in java_files
    assert "Utils.java" in java_files
    assert len(result["files"]) >= 2

  def test_search_files_by_pattern_max_depth(self, sample_directory: Path) -> None:
    """Test searching with max depth limit."""
    # Search with max_depth=0 (only root)
    result = search_files_by_pattern(
      str(sample_directory), "*.java", "glob", max_depth=0
    )

    java_files = {f["name"] for f in result["files"]}
    assert "Test.java" in java_files
    assert "Utils.java" in java_files
    # Main.java should not be found as it's in subdir

  def test_search_files_by_pattern_glob_simple(self, sample_directory: Path) -> None:
    """Test searching with simple glob patterns."""
    # Search for exact filename
    result = search_files_by_pattern(str(sample_directory), "Test.java", "glob")
    assert len(result["files"]) == 1
    assert result["files"][0]["name"] == "Test.java"

    # Search with glob pattern
    result = search_files_by_pattern(str(sample_directory), "*.java", "glob")
    java_files = {f["name"] for f in result["files"]}
    assert "Test.java" in java_files
    assert "Utils.java" in java_files
    assert "Main.java" in java_files  # should find in subdirectories too
    assert "readme.txt" not in java_files

    # Search with partial glob pattern
    result = search_files_by_pattern(str(sample_directory), "Test*", "glob")
    assert len(result["files"]) == 1
    assert result["files"][0]["name"] == "Test.java"

  def test_search_files_by_pattern_start_path(self, sample_directory: Path) -> None:
    """Test searching from specific start path."""
    result = search_files_by_pattern(
      str(sample_directory), "*", "glob", start_path="com/example"
    )

    file_names = {f["name"] for f in result["files"]}
    assert "Main.java" in file_names
    assert "helper.py" in file_names
    assert "Test.java" not in file_names


class TestSearchFileContents:
  """Test search_file_contents function."""

  @pytest.fixture
  def sample_directory(self, tmp_path: Path) -> Path:
    """Create sample directory with files containing searchable content."""
    (tmp_path / "class1.java").write_text(
      "package com.example;\n"
      "public class Test {\n"
      "    public void method() {\n"
      '        System.out.println("Hello World");\n'
      "    }\n"
      "}\n"
    )

    (tmp_path / "class2.java").write_text(
      "package com.example;\n"
      "public class Utils {\n"
      '    private static final String HELLO = "Hello";\n'
      "    public String getGreeting() {\n"
      '        return HELLO + " World";\n'
      "    }\n"
      "}\n"
    )

    (tmp_path / "readme.txt").write_text(
      "This is a readme file.\nIt contains some information.\nHello everyone!\n"
    )

    return tmp_path

  def test_search_file_contents_string(self, sample_directory: Path) -> None:
    """Test searching file contents with string query."""
    result = search_file_contents(str(sample_directory), "Hello", "string")

    assert result["search_config"]["query"] == "Hello"
    assert result["search_config"]["query_type"] == "string"
    assert len(result["matches"]) >= 2  # Should match in multiple files

    # Check that matches contain the search term
    for file_path, matches in result["matches"].items():
      for match in matches:
        assert "Hello" in match["content"]

  def test_search_file_contents_regex(self, sample_directory: Path) -> None:
    """Test searching file contents with regex query."""
    result = search_file_contents(
      str(sample_directory), r"public\s+class\s+\w+", "regex"
    )

    assert result["search_config"]["query_type"] == "regex"

    # Should match class declarations
    found_classes = False
    for file_path, matches in result["matches"].items():
      if matches:
        found_classes = True
        break

    assert found_classes

  def test_search_file_contents_with_context(self, sample_directory: Path) -> None:
    """Test searching with context lines."""
    result = search_file_contents(
      str(sample_directory), "println", "string", context_before=1, context_after=1
    )

    assert result["search_config"]["context_before"] == 1
    assert result["search_config"]["context_after"] == 1

    # Check that context is included
    for file_path, matches in result["matches"].items():
      for match in matches:
        lines = match["content"].split("\n")
        assert len(lines) >= 3  # At least match line + context

  def test_search_file_contents_max_results(self, sample_directory: Path) -> None:
    """Test searching with max results limit."""
    result = search_file_contents(
      str(sample_directory), "public", "string", max_results=1
    )

    # Should limit total matches across all files
    total_matches = sum(len(matches) for matches in result["matches"].values())
    assert total_matches <= 1

  def test_search_file_contents_nonexistent_start(self, sample_directory: Path) -> None:
    """Test searching from nonexistent start path."""
    with pytest.raises(ValueError, match="Start path does not exist"):
      search_file_contents(
        str(sample_directory), "test", "string", start_path="nonexistent"
      )
