import os

def is_safe_path(basedir, path, follow_symlinks=True):
    """
    Validates that a file path is within the expected base directory.
    Prevents directory traversal attacks.
    
    Args:
        basedir: The base directory that should contain the path
        path: The path to validate
        follow_symlinks: Whether to follow symbolic links when resolving paths
        
    Returns:
        bool: True if the path is safe, False otherwise
    """
    if follow_symlinks:
        return os.path.realpath(path).startswith(os.path.realpath(basedir))
    return os.path.abspath(path).startswith(os.path.abspath(basedir)) 