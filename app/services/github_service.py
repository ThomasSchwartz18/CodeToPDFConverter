import os
import shutil
import tempfile
from git import Repo
from urllib.parse import urlparse
import requests

class GitHubService:
    def __init__(self):
        self.temp_dir = None

    def is_valid_github_url(self, url):
        """Validate if the URL is a valid GitHub repository URL."""
        try:
            parsed = urlparse(url)
            path_parts = parsed.path.strip('/').split('/')
            return (parsed.netloc == 'github.com' and 
                   len(path_parts) >= 2 and 
                   all(part for part in path_parts[:2]))
        except:
            return False

    def clone_repository(self, github_url):
        """Clone a GitHub repository to a temporary directory."""
        try:
            # Create a temporary directory
            self.temp_dir = tempfile.mkdtemp()
            
            # Clone the repository
            Repo.clone_from(github_url, self.temp_dir)
            
            # Remove .git directory to avoid including version control files
            git_dir = os.path.join(self.temp_dir, '.git')
            if os.path.exists(git_dir):
                shutil.rmtree(git_dir)
            
            return self.temp_dir
        except Exception as e:
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
            raise Exception(f"Failed to clone repository: {str(e)}")

    def cleanup(self):
        """Clean up temporary directory after processing."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            self.temp_dir = None 