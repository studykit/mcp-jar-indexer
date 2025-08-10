"""Tests for git_handler module."""

import os
import shutil
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from git import GitCommandError

from src.core.git_handler import (
  GitHandler,
  GitError,
  GitCloneFailedError,
  GitRefNotFoundError,
  GitAuthenticationError,
  GitWorktreeError,
)
from src.core.storage import StorageManager


class TestGitHandler:
  """Test cases for GitHandler."""

  def setup_method(self):
    """Set up test environment."""
    self.temp_dir = tempfile.mkdtemp()
    self.storage = StorageManager(self.temp_dir)
    self.git_handler = GitHandler(self.storage)

  def teardown_method(self):
    """Clean up test environment."""
    if os.path.exists(self.temp_dir):
      shutil.rmtree(self.temp_dir)

  def test_init(self):
    """Test GitHandler initialization."""
    assert self.git_handler.storage_manager == self.storage
    assert isinstance(self.git_handler.storage_manager, StorageManager)

  def test_is_git_repository_ssh_format(self):
    """Test Git repository detection for SSH format URLs."""
    # SSH format with .git suffix
    assert self.git_handler.is_git_repository("git@github.com:user/repo.git")

    # SSH format without .git suffix
    assert self.git_handler.is_git_repository("git@github.com:user/repo")

    # SSH with custom port
    assert self.git_handler.is_git_repository("git@github.com:22:user/repo.git")

  def test_is_git_repository_https_format(self):
    """Test Git repository detection for HTTPS format URLs."""
    # HTTPS format with .git suffix
    assert self.git_handler.is_git_repository("https://github.com/user/repo.git")

    # HTTPS format without .git suffix (should return False)
    assert not self.git_handler.is_git_repository("https://github.com/user/repo")

    # HTTPS with different host
    assert self.git_handler.is_git_repository("https://gitlab.com/user/repo.git")

  def test_is_git_repository_file_format(self):
    """Test Git repository detection for file:// URLs."""
    # Create a mock .git directory
    git_dir = Path(self.temp_dir) / "test-repo" / ".git"
    git_dir.mkdir(parents=True)

    # File URL pointing to directory with .git
    assert self.git_handler.is_git_repository(f"file://{self.temp_dir}/test-repo")

    # File URL pointing to .git directory directly
    assert self.git_handler.is_git_repository(f"file://{git_dir}")

    # File URL pointing to non-git directory
    non_git_dir = Path(self.temp_dir) / "not-git"
    non_git_dir.mkdir()
    assert not self.git_handler.is_git_repository(f"file://{non_git_dir}")

  def test_is_git_repository_invalid_formats(self):
    """Test Git repository detection for invalid formats."""
    assert not self.git_handler.is_git_repository("http://example.com/repo")
    assert not self.git_handler.is_git_repository("ftp://example.com/repo.git")
    assert not self.git_handler.is_git_repository("invalid-url")
    assert not self.git_handler.is_git_repository("")

  @patch("subprocess.run")
  def test_clone_bare_repository_success(self, mock_subprocess):
    """Test successful bare repository cloning."""
    # Mock successful subprocess call
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stderr = ""
    mock_result.stdout = "Cloning into bare repository..."
    mock_subprocess.return_value = mock_result

    git_uri = "https://github.com/user/repo.git"
    group_id = "com.example"
    artifact_id = "test-lib"

    result_path = self.git_handler.clone_bare_repository(git_uri, group_id, artifact_id)

    expected_path = self.storage.get_git_bare_path(group_id, artifact_id)
    assert result_path == expected_path

    # Verify subprocess was called with correct arguments
    mock_subprocess.assert_called_once()
    call_args = mock_subprocess.call_args[0][0]
    assert "git" in call_args
    assert "clone" in call_args
    assert "--bare" in call_args
    assert git_uri in call_args

  @patch("subprocess.run")
  def test_clone_bare_repository_already_exists(self, mock_subprocess):
    """Test bare repository cloning when repository already exists."""
    git_uri = "https://github.com/user/repo.git"
    group_id = "com.example"
    artifact_id = "test-lib"

    # Create the bare repository directory
    bare_path = self.storage.get_git_bare_path(group_id, artifact_id)
    bare_path.mkdir(parents=True)

    result_path = self.git_handler.clone_bare_repository(git_uri, group_id, artifact_id)

    assert result_path == bare_path
    # Subprocess should not be called if directory exists
    mock_subprocess.assert_not_called()

  @patch("subprocess.run")
  def test_clone_bare_repository_auth_failure(self, mock_subprocess):
    """Test bare repository cloning with authentication failure."""
    mock_result = Mock()
    mock_result.returncode = 1
    mock_result.stderr = "Authentication failed for 'https://github.com/user/repo.git'"
    mock_result.stdout = ""
    mock_subprocess.return_value = mock_result

    git_uri = "https://github.com/user/repo.git"
    group_id = "com.example"
    artifact_id = "test-lib"

    with pytest.raises(GitAuthenticationError) as exc_info:
      self.git_handler.clone_bare_repository(git_uri, group_id, artifact_id)

    assert "Git authentication failed" in str(exc_info.value)

  @patch("subprocess.run")
  def test_clone_bare_repository_clone_failure(self, mock_subprocess):
    """Test bare repository cloning with general failure."""
    mock_result = Mock()
    mock_result.returncode = 1
    mock_result.stderr = "Repository not found"
    mock_subprocess.return_value = mock_result

    git_uri = "https://github.com/user/nonexistent.git"
    group_id = "com.example"
    artifact_id = "test-lib"

    with pytest.raises(GitCloneFailedError) as exc_info:
      self.git_handler.clone_bare_repository(git_uri, group_id, artifact_id)

    assert "Git clone failed" in str(exc_info.value)

  @patch("subprocess.run")
  def test_clone_bare_repository_timeout(self, mock_subprocess):
    """Test bare repository cloning with timeout."""
    mock_subprocess.side_effect = subprocess.TimeoutExpired("git", 300)

    git_uri = "https://github.com/user/repo.git"
    group_id = "com.example"
    artifact_id = "test-lib"

    with pytest.raises(GitCloneFailedError) as exc_info:
      self.git_handler.clone_bare_repository(git_uri, group_id, artifact_id)

    assert "timed out" in str(exc_info.value)

  @patch("src.core.git_handler.Repo")
  def test_create_worktree_success(self, mock_repo_class):
    """Test successful worktree creation."""
    group_id = "com.example"
    artifact_id = "test-lib"
    version = "1.0.0"
    git_ref = "main"

    # Create bare repository directory
    bare_path = self.storage.get_git_bare_path(group_id, artifact_id)
    bare_path.mkdir(parents=True)

    # Mock repository and git operations
    mock_repo = Mock()
    mock_git = Mock()
    mock_repo.git = mock_git
    mock_repo_class.return_value = mock_repo

    # Mock the private methods
    self.git_handler._validate_git_ref = Mock(return_value=True)

    result_path = self.git_handler.create_worktree(
      group_id, artifact_id, version, git_ref
    )

    expected_path = self.storage.get_code_path(group_id, artifact_id, version)
    assert result_path == expected_path

    # Verify worktree command was called
    mock_git.worktree.assert_called_once_with("add", str(expected_path), git_ref)

  @patch("src.core.git_handler.Repo")
  def test_create_worktree_no_bare_repo(self, mock_repo_class):
    """Test worktree creation when bare repository doesn't exist."""
    group_id = "com.example"
    artifact_id = "test-lib"
    version = "1.0.0"

    with pytest.raises(GitWorktreeError) as exc_info:
      self.git_handler.create_worktree(group_id, artifact_id, version)

    assert "Bare repository not found" in str(exc_info.value)

  @patch("src.core.git_handler.Repo")
  def test_create_worktree_already_exists(self, mock_repo_class):
    """Test worktree creation when worktree already exists."""
    group_id = "com.example"
    artifact_id = "test-lib"
    version = "1.0.0"

    # Create bare repository and worktree directories
    bare_path = self.storage.get_git_bare_path(group_id, artifact_id)
    bare_path.mkdir(parents=True)
    worktree_path = self.storage.get_code_path(group_id, artifact_id, version)
    worktree_path.mkdir(parents=True)

    result_path = self.git_handler.create_worktree(group_id, artifact_id, version)

    assert result_path == worktree_path
    # Repo should not be called if worktree already exists
    mock_repo_class.assert_not_called()

  @patch("src.core.git_handler.Repo")
  def test_create_worktree_invalid_git_ref(self, mock_repo_class):
    """Test worktree creation with invalid git reference."""
    group_id = "com.example"
    artifact_id = "test-lib"
    version = "1.0.0"
    git_ref = "nonexistent-branch"

    # Create bare repository directory
    bare_path = self.storage.get_git_bare_path(group_id, artifact_id)
    bare_path.mkdir(parents=True)

    # Mock repository
    mock_repo = Mock()
    mock_repo_class.return_value = mock_repo

    # Mock the private methods
    self.git_handler._get_default_branch = Mock(return_value="main")
    self.git_handler._validate_git_ref = Mock(return_value=False)

    with pytest.raises(GitRefNotFoundError) as exc_info:
      self.git_handler.create_worktree(group_id, artifact_id, version, git_ref)

    assert f"Git reference '{git_ref}' not found" in str(exc_info.value)

  @patch("src.core.git_handler.Repo")
  def test_update_repository_success(self, mock_repo_class):
    """Test successful repository update."""
    group_id = "com.example"
    artifact_id = "test-lib"

    # Create bare repository directory
    bare_path = self.storage.get_git_bare_path(group_id, artifact_id)
    bare_path.mkdir(parents=True)

    # Mock repository and remote
    mock_repo = Mock()
    mock_remote = Mock()
    mock_repo.remote.return_value = mock_remote
    mock_repo_class.return_value = mock_repo

    result = self.git_handler.update_repository(group_id, artifact_id)

    assert result is True
    mock_repo.remote.assert_called_once_with("origin")
    mock_remote.fetch.assert_called_once()

  @patch("src.core.git_handler.Repo")
  def test_update_repository_no_bare_repo(self, mock_repo_class):
    """Test repository update when bare repository doesn't exist."""
    group_id = "com.example"
    artifact_id = "test-lib"

    result = self.git_handler.update_repository(group_id, artifact_id)

    assert result is False
    mock_repo_class.assert_not_called()

  @patch("src.core.git_handler.Repo")
  def test_remove_worktree_success(self, mock_repo_class):
    """Test successful worktree removal."""
    group_id = "com.example"
    artifact_id = "test-lib"
    version = "1.0.0"

    # Create bare repository and worktree directories
    bare_path = self.storage.get_git_bare_path(group_id, artifact_id)
    bare_path.mkdir(parents=True)
    worktree_path = self.storage.get_code_path(group_id, artifact_id, version)
    worktree_path.mkdir(parents=True)

    # Mock repository
    mock_repo = Mock()
    mock_git = Mock()
    mock_repo.git = mock_git
    mock_repo_class.return_value = mock_repo

    result = self.git_handler.remove_worktree(group_id, artifact_id, version)

    assert result is True
    mock_git.worktree.assert_called_once_with("remove", str(worktree_path), "--force")

  def test_remove_worktree_not_exists(self):
    """Test worktree removal when worktree doesn't exist."""
    group_id = "com.example"
    artifact_id = "test-lib"
    version = "1.0.0"

    result = self.git_handler.remove_worktree(group_id, artifact_id, version)

    assert result is True  # Should return True if worktree doesn't exist

  @patch("src.core.git_handler.Repo")
  def test_list_worktrees_success(self, mock_repo_class):
    """Test successful worktree listing."""
    group_id = "com.example"
    artifact_id = "test-lib"

    # Create bare repository directory
    bare_path = self.storage.get_git_bare_path(group_id, artifact_id)
    bare_path.mkdir(parents=True)

    # Mock repository and worktree output
    mock_repo = Mock()
    mock_git = Mock()
    mock_git.worktree.return_value = (
      "worktree /path/to/worktree1\n"
      "branch refs/heads/main\n"
      "HEAD abc123def456\n\n"
      "worktree /path/to/worktree2\n"
      "branch refs/heads/develop\n"
      "HEAD def456abc123\n"
    )
    mock_repo.git = mock_git
    mock_repo_class.return_value = mock_repo

    result = self.git_handler.list_worktrees(group_id, artifact_id)

    assert len(result) == 2
    assert result[0]["path"] == "/path/to/worktree1"
    assert result[0]["branch"] == "refs/heads/main"
    assert result[0]["head"] == "abc123def456"

    assert result[1]["path"] == "/path/to/worktree2"
    assert result[1]["branch"] == "refs/heads/develop"
    assert result[1]["head"] == "def456abc123"

  def test_list_worktrees_no_bare_repo(self):
    """Test worktree listing when bare repository doesn't exist."""
    group_id = "com.example"
    artifact_id = "test-lib"

    result = self.git_handler.list_worktrees(group_id, artifact_id)

    assert result == []

  @patch("src.core.git_handler.Repo")
  def test_get_default_branch(self, mock_repo_class):
    """Test getting default branch name."""
    mock_repo = Mock()
    mock_git = Mock()

    # Test successful symbolic-ref resolution
    mock_git.symbolic_ref.return_value = "refs/remotes/origin/main"
    mock_repo.git = mock_git

    result = self.git_handler._get_default_branch(mock_repo)
    assert result == "main"

  @patch("src.core.git_handler.Repo")
  def test_get_default_branch_fallback(self, mock_repo_class):
    """Test getting default branch name with fallback logic."""
    mock_repo = Mock()
    mock_git = Mock()

    # Mock symbolic-ref to fail, but rev-parse to succeed for 'main'
    mock_git.symbolic_ref.side_effect = GitCommandError("symbolic-ref", "failed")
    mock_git.rev_parse.side_effect = [
      GitCommandError("rev-parse", "failed"),
      None,
    ]  # Fail for 'main', succeed for 'master'
    mock_repo.git = mock_git

    result = self.git_handler._get_default_branch(mock_repo)
    assert result == "master"

  @patch("src.core.git_handler.Repo")
  def test_validate_git_ref_success(self, mock_repo_class):
    """Test successful git reference validation."""
    mock_repo = Mock()
    mock_git = Mock()
    mock_git.rev_parse.return_value = "abc123def456"  # Successful resolution
    mock_repo.git = mock_git

    result = self.git_handler._validate_git_ref(mock_repo, "main")
    assert result is True

  @patch("src.core.git_handler.Repo")
  def test_validate_git_ref_with_origin_prefix(self, mock_repo_class):
    """Test git reference validation with origin prefix fallback."""
    mock_repo = Mock()
    mock_git = Mock()
    # First call fails, second call with origin prefix succeeds
    mock_git.rev_parse.side_effect = [
      GitCommandError("rev-parse", "failed"),
      "abc123def456",
    ]
    mock_repo.git = mock_git

    result = self.git_handler._validate_git_ref(mock_repo, "feature-branch")
    assert result is True

  @patch("src.core.git_handler.Repo")
  def test_validate_git_ref_failure(self, mock_repo_class):
    """Test git reference validation failure."""
    mock_repo = Mock()
    mock_git = Mock()
    mock_git.rev_parse.side_effect = GitCommandError("rev-parse", "failed")
    mock_repo.git = mock_git

    result = self.git_handler._validate_git_ref(mock_repo, "nonexistent-ref")
    assert result is False

  def test_prepare_auth_args_ssh_key(self):
    """Test authentication argument preparation with SSH key."""
    auth_config = {"ssh_key": "/path/to/ssh/key"}

    result = self.git_handler._prepare_auth_args(auth_config)

    assert len(result) == 2
    assert result[0] == "-c"
    assert "core.sshCommand=ssh -i /path/to/ssh/key" in result[1]
    assert "StrictHostKeyChecking=no" in result[1]

  def test_prepare_auth_args_username_token(self):
    """Test authentication argument preparation with username/token."""
    auth_config = {"username": "user", "token": "token123"}

    result = self.git_handler._prepare_auth_args(auth_config)

    # For now, username/token auth returns empty list (handled in URL)
    assert result == []

  def test_prepare_auth_args_empty(self):
    """Test authentication argument preparation with no auth config."""
    auth_config = {}

    result = self.git_handler._prepare_auth_args(auth_config)

    assert result == []

  def test_apply_auth_config_ssh_key(self):
    """Test applying SSH key authentication configuration."""
    mock_config_writer = Mock()
    auth_config = {"ssh_key": "/path/to/ssh/key"}

    self.git_handler._apply_auth_config(mock_config_writer, auth_config)

    mock_config_writer.set_value.assert_called_once_with(
      "core", "sshCommand", "ssh -i /path/to/ssh/key -o StrictHostKeyChecking=no"
    )

  def test_apply_auth_config_no_ssh_key(self):
    """Test applying authentication configuration without SSH key."""
    mock_config_writer = Mock()
    auth_config = {"username": "user", "token": "token123"}

    self.git_handler._apply_auth_config(mock_config_writer, auth_config)

    # Should not call set_value if no SSH key
    mock_config_writer.set_value.assert_not_called()


class TestGitExceptions:
  """Test cases for Git exception classes."""

  def test_git_error_base_class(self):
    """Test GitError base exception class."""
    error = GitError("test error")
    assert str(error) == "test error"
    assert isinstance(error, Exception)

  def test_git_clone_failed_error(self):
    """Test GitCloneFailedError exception class."""
    error = GitCloneFailedError("clone failed")
    assert str(error) == "clone failed"
    assert isinstance(error, GitError)

  def test_git_ref_not_found_error(self):
    """Test GitRefNotFoundError exception class."""
    error = GitRefNotFoundError("ref not found")
    assert str(error) == "ref not found"
    assert isinstance(error, GitError)

  def test_git_authentication_error(self):
    """Test GitAuthenticationError exception class."""
    error = GitAuthenticationError("auth failed")
    assert str(error) == "auth failed"
    assert isinstance(error, GitError)

  def test_git_worktree_error(self):
    """Test GitWorktreeError exception class."""
    error = GitWorktreeError("worktree error")
    assert str(error) == "worktree error"
    assert isinstance(error, GitError)
