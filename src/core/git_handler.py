"""Git repository handler for JAR indexer.

This module provides functionality for managing Git repositories including
bare clones, worktree creation, and git reference handling.
"""

import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging

from git import Repo, InvalidGitRepositoryError, GitCommandError

from .storage import StorageManager


logger = logging.getLogger(__name__)


class GitError(Exception):
  """Base class for Git-related errors."""

  pass


class GitCloneFailedError(GitError):
  """Raised when Git clone operation fails."""

  pass


class GitRefNotFoundError(GitError):
  """Raised when requested Git reference is not found."""

  pass


class GitAuthenticationError(GitError):
  """Raised when Git authentication fails."""

  pass


class GitWorktreeError(GitError):
  """Raised when Git worktree operations fail."""

  pass


class GitHandler:
  """Handles Git repository operations for JAR indexer."""

  def __init__(self, storage_manager: StorageManager):
    """Initialize Git handler.

    Args:
        storage_manager: Storage manager instance for path management
    """
    self.storage_manager = storage_manager

  def is_git_repository(self, uri: str) -> bool:
    """Check if URI points to a Git repository.

    Args:
        uri: URI to check

    Returns:
        True if URI appears to be a Git repository
    """
    # SSH format: git@host:user/repo or git@host:user/repo.git
    if uri.startswith("git@"):
      return True

    # HTTPS format ending with .git
    if uri.startswith("https://") and uri.endswith(".git"):
      return True

    # Local directory with .git subdirectory
    if uri.startswith("file://"):
      local_path = Path(uri[7:])  # Remove 'file://' prefix
      return (local_path / ".git").exists() or local_path.name.endswith(".git")

    return False

  def clone_bare_repository(
    self,
    git_uri: str,
    group_id: str,
    artifact_id: str,
    auth_config: Optional[Dict[str, str]] = None,
  ) -> Path:
    """Clone Git repository as bare clone.

    Args:
        git_uri: Git repository URI
        group_id: Maven group ID
        artifact_id: Maven artifact ID
        auth_config: Optional authentication configuration

    Returns:
        Path to created bare repository

    Raises:
        GitCloneFailedError: If clone operation fails
        GitAuthenticationError: If authentication fails
    """
    bare_path = self.storage_manager.get_git_bare_path(group_id, artifact_id)

    # Create parent directories
    bare_path.parent.mkdir(parents=True, exist_ok=True)

    # Check if bare repository already exists
    if bare_path.exists():
      logger.info(f"Bare repository already exists at {bare_path}")
      return bare_path

    try:
      logger.info(f"Cloning bare repository from {git_uri} to {bare_path}")

      # Prepare clone arguments
      clone_args = ["git", "clone", "--bare"]

      # Add authentication if provided
      if auth_config:
        clone_args.extend(self._prepare_auth_args(auth_config))

      clone_args.extend([git_uri, str(bare_path)])

      # Execute clone command
      result = subprocess.run(
        clone_args,
        capture_output=True,
        text=True,
        timeout=300,  # 5 minute timeout
      )

      if result.returncode != 0:
        error_msg = result.stderr or result.stdout or "Unknown git clone error"
        if "Authentication failed" in error_msg or "Permission denied" in error_msg:
          raise GitAuthenticationError(f"Git authentication failed: {error_msg}")
        else:
          raise GitCloneFailedError(f"Git clone failed: {error_msg}")

      logger.info(f"Successfully cloned bare repository to {bare_path}")
      return bare_path

    except subprocess.TimeoutExpired:
      raise GitCloneFailedError("Git clone operation timed out")
    except GitAuthenticationError:
      raise  # Re-raise GitAuthenticationError as-is
    except Exception as e:
      # Clean up partial clone
      if bare_path.exists():
        shutil.rmtree(bare_path)
      raise GitCloneFailedError(f"Failed to clone repository: {str(e)}")

  def create_worktree(
    self, group_id: str, artifact_id: str, version: str, git_ref: Optional[str] = None
  ) -> Path:
    """Create worktree from bare repository.

    Args:
        group_id: Maven group ID
        artifact_id: Maven artifact ID
        version: Maven version
        git_ref: Git reference (branch/tag/commit). Defaults to 'main'

    Returns:
        Path to created worktree

    Raises:
        GitWorktreeError: If worktree creation fails
        GitRefNotFoundError: If specified git_ref is not found
    """
    bare_path = self.storage_manager.get_git_bare_path(group_id, artifact_id)
    worktree_path = self.storage_manager.get_code_path(group_id, artifact_id, version)

    if not bare_path.exists():
      raise GitWorktreeError(f"Bare repository not found at {bare_path}")

    # Create parent directories for worktree
    worktree_path.parent.mkdir(parents=True, exist_ok=True)

    # Check if worktree already exists
    if worktree_path.exists():
      logger.info(f"Worktree already exists at {worktree_path}")
      return worktree_path

    try:
      repo = Repo(bare_path)

      # Determine git reference
      if git_ref is None:
        git_ref = self._get_default_branch(repo)

      # Validate git reference exists
      if not self._validate_git_ref(repo, git_ref):
        raise GitRefNotFoundError(f"Git reference '{git_ref}' not found in repository")

      logger.info(f"Creating worktree at {worktree_path} with ref {git_ref}")

      # Create worktree using GitPython
      repo.git.worktree("add", str(worktree_path), git_ref)

      logger.info(f"Successfully created worktree at {worktree_path}")
      return worktree_path

    except InvalidGitRepositoryError:
      raise GitWorktreeError(f"Invalid Git repository at {bare_path}")
    except GitCommandError as e:
      if "already exists" in str(e):
        logger.info(f"Worktree already exists at {worktree_path}")
        return worktree_path
      else:
        raise GitWorktreeError(f"Failed to create worktree: {str(e)}")
    except GitRefNotFoundError:
      raise  # Re-raise GitRefNotFoundError as-is
    except Exception as e:
      raise GitWorktreeError(f"Unexpected error creating worktree: {str(e)}")

  def update_repository(
    self, group_id: str, artifact_id: str, auth_config: Optional[Dict[str, str]] = None
  ) -> bool:
    """Update existing bare repository.

    Args:
        group_id: Maven group ID
        artifact_id: Maven artifact ID
        auth_config: Optional authentication configuration

    Returns:
        True if update was successful, False otherwise
    """
    bare_path = self.storage_manager.get_git_bare_path(group_id, artifact_id)

    if not bare_path.exists():
      logger.warning(f"Bare repository not found at {bare_path}")
      return False

    try:
      repo = Repo(bare_path)

      # Fetch latest changes
      logger.info(f"Updating bare repository at {bare_path}")

      # Setup authentication if provided
      if auth_config:
        with repo.config_writer() as config:
          self._apply_auth_config(config, auth_config)

      repo.remote("origin").fetch()

      logger.info(f"Successfully updated bare repository at {bare_path}")
      return True

    except Exception as e:
      logger.error(f"Failed to update repository: {str(e)}")
      return False

  def remove_worktree(self, group_id: str, artifact_id: str, version: str) -> bool:
    """Remove worktree.

    Args:
        group_id: Maven group ID
        artifact_id: Maven artifact ID
        version: Maven version

    Returns:
        True if removal was successful, False otherwise
    """
    bare_path = self.storage_manager.get_git_bare_path(group_id, artifact_id)
    worktree_path = self.storage_manager.get_code_path(group_id, artifact_id, version)

    if not worktree_path.exists():
      logger.info(f"Worktree does not exist at {worktree_path}")
      return True

    try:
      if bare_path.exists():
        repo = Repo(bare_path)
        repo.git.worktree("remove", str(worktree_path), "--force")
      else:
        # If bare repo doesn't exist, just remove directory
        shutil.rmtree(worktree_path)

      logger.info(f"Successfully removed worktree at {worktree_path}")
      return True

    except Exception as e:
      logger.error(f"Failed to remove worktree: {str(e)}")
      return False

  def list_worktrees(self, group_id: str, artifact_id: str) -> List[Dict[str, Any]]:
    """List all worktrees for a repository.

    Args:
        group_id: Maven group ID
        artifact_id: Maven artifact ID

    Returns:
        List of worktree information dictionaries
    """
    bare_path = self.storage_manager.get_git_bare_path(group_id, artifact_id)

    if not bare_path.exists():
      return []

    try:
      repo = Repo(bare_path)
      worktrees: List[Dict[str, Any]] = []

      # Get worktree list
      worktree_output = repo.git.worktree("list", "--porcelain")

      current_worktree: Dict[str, Any] = {}
      for line in worktree_output.split("\n"):
        if line.startswith("worktree "):
          if current_worktree:
            worktrees.append(current_worktree)
          current_worktree = {"path": line[9:]}  # Remove 'worktree ' prefix
        elif line.startswith("branch "):
          current_worktree["branch"] = line[7:]  # Remove 'branch ' prefix
        elif line.startswith("HEAD "):
          current_worktree["head"] = line[5:]  # Remove 'HEAD ' prefix

      if current_worktree:
        worktrees.append(current_worktree)

      return worktrees

    except Exception as e:
      logger.error(f"Failed to list worktrees: {str(e)}")
      return []

  def _get_default_branch(self, repo: Repo) -> str:
    """Get the default branch name for repository.

    Args:
        repo: Git repository object

    Returns:
        Default branch name
    """
    try:
      # Try to get remote HEAD reference
      return repo.git.symbolic_ref("refs/remotes/origin/HEAD").replace(
        "refs/remotes/origin/", ""
      )
    except GitCommandError:
      # Fallback to common default branch names
      for branch_name in ["main", "master", "develop"]:
        try:
          repo.git.rev_parse(f"origin/{branch_name}")
          return branch_name
        except GitCommandError:
          continue

      # If no common branches found, use the first available branch
      try:
        branches = [
          ref.name.replace("origin/", "") for ref in repo.remote("origin").refs
        ]
        if branches:
          return branches[0]
      except Exception:
        pass

      return "main"  # Final fallback

  def _validate_git_ref(self, repo: Repo, git_ref: str) -> bool:
    """Validate that git reference exists in repository.

    Args:
        repo: Git repository object
        git_ref: Git reference to validate

    Returns:
        True if reference exists, False otherwise
    """
    try:
      # Try to resolve the reference
      repo.git.rev_parse(git_ref)
      return True
    except GitCommandError:
      # Try with origin prefix for branches
      try:
        repo.git.rev_parse(f"origin/{git_ref}")
        return True
      except GitCommandError:
        return False

  def _prepare_auth_args(self, auth_config: Dict[str, str]) -> List[str]:
    """Prepare authentication arguments for git commands.

    Args:
        auth_config: Authentication configuration

    Returns:
        List of git command arguments for authentication
    """
    args: List[str] = []

    if "ssh_key" in auth_config:
      ssh_key_path = auth_config["ssh_key"]
      args.extend(
        ["-c", f"core.sshCommand=ssh -i {ssh_key_path} -o StrictHostKeyChecking=no"]
      )

    if "username" in auth_config and "token" in auth_config:
      # For HTTPS authentication, we'll handle this in the URL
      pass

    return args

  def _apply_auth_config(self, config_writer: Any, auth_config: Dict[str, str]) -> None:
    """Apply authentication configuration to git config.

    Args:
        config_writer: Git config writer object
        auth_config: Authentication configuration
    """
    if "ssh_key" in auth_config:
      ssh_key_path = auth_config["ssh_key"]
      config_writer.set_value(
        "core", "sshCommand", f"ssh -i {ssh_key_path} -o StrictHostKeyChecking=no"
      )
