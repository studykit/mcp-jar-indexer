"""Storage management for JAR Indexer MCP Server."""

import os
from pathlib import Path
from typing import Optional


class StorageManager:
    """Manages storage directory structure and paths for JAR indexer."""
    
    def __init__(self, base_path: Optional[str] = None):
        """Initialize storage manager.
        
        Args:
            base_path: Base directory path. Defaults to ~/.jar-indexer
        """
        if base_path is None:
            base_path = os.path.expanduser("~/.jar-indexer")
        self.base_path = Path(base_path)
        
    def get_home_dir(self) -> Path:
        """Get the home directory for jar-indexer."""
        return self.base_path
        
    def get_code_dir(self) -> Path:
        """Get the code directory path."""
        return self.base_path / "code"
        
    def get_source_jar_dir(self) -> Path:
        """Get the source-jar directory path."""
        return self.base_path / "source-jar"
        
    def get_git_bare_dir(self) -> Path:
        """Get the git-bare directory path."""
        return self.base_path / "git-bare"
        
    def create_maven_path(self, group_id: str, artifact_id: str, version: Optional[str] = None) -> str:
        """Create Maven coordinate based path.
        
        Args:
            group_id: Maven group ID (e.g., 'org.springframework')
            artifact_id: Maven artifact ID (e.g., 'spring-core')
            version: Maven version (e.g., '5.3.21')
            
        Returns:
            Path string based on Maven coordinates
        """
        # Convert dots to slashes for group_id
        group_path = group_id.replace('.', '/')
        
        if version:
            return f"{group_path}/{artifact_id}/{version}"
        else:
            return f"{group_path}/{artifact_id}"
            
    def get_code_path(self, group_id: str, artifact_id: str, version: str) -> Path:
        """Get full code directory path for given Maven coordinates."""
        maven_path = self.create_maven_path(group_id, artifact_id, version)
        return self.get_code_dir() / maven_path
        
    def get_source_jar_path(self, group_id: str, artifact_id: str, version: str) -> Path:
        """Get full source-jar directory path for given Maven coordinates."""
        maven_path = self.create_maven_path(group_id, artifact_id, version)
        return self.get_source_jar_dir() / maven_path
        
    def get_git_bare_path(self, group_id: str, artifact_id: str) -> Path:
        """Get full git-bare directory path for given Maven coordinates."""
        maven_path = self.create_maven_path(group_id, artifact_id)
        return self.get_git_bare_dir() / maven_path
        
    def ensure_directories(self) -> None:
        """Create storage directory structure if it doesn't exist."""
        directories = [
            self.get_home_dir(),
            self.get_code_dir(),
            self.get_source_jar_dir(),
            self.get_git_bare_dir()
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            
    def validate_directory_permissions(self) -> bool:
        """Validate that directories have proper permissions."""
        self.ensure_directories()
        
        directories = [
            self.get_home_dir(),
            self.get_code_dir(),
            self.get_source_jar_dir(),
            self.get_git_bare_dir()
        ]
        
        for directory in directories:
            if not directory.exists():
                return False
            if not os.access(directory, os.R_OK | os.W_OK | os.X_OK):
                return False
                
        return True