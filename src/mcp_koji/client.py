"""Koji API client wrapper."""
import koji
from typing import Optional, List, Dict, Any


class KojiClient:
    """Client for Fedora Koji build system."""
    
    def __init__(self, koji_url: str = "https://koji.fedoraproject.org/kojihub"):
        self.koji_url = koji_url
        self.session = koji.ClientSession(koji_url)
    
    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Get user information by username.
        
        Args:
            username: Koji username
            
        Returns:
            User info dict or None
        """
        return self.session.getUser(username)

    def list_builds(
        self,
        user_id: Optional[int] = None,
        package_id: Optional[int] = None,
        state: Optional[int] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        List builds with optional filters.
        
        Args:
            user_id: Filter by user ID
            package_id: Filter by package ID
            state: Filter by build state (0=building, 1=complete, 3=failed, 4=canceled)
            limit: Maximum number of results
            
        Returns:
            List of build dicts
        """
        # Build kwargs for listBuilds
        kwargs = {}
        if user_id is not None:
            kwargs['userID'] = user_id
        if package_id is not None:
            kwargs['packageID'] = package_id
        if state is not None:
            kwargs['state'] = state
        
        # Add queryOpts
        kwargs['queryOpts'] = {'limit': limit, 'order': '-build_id'}
        
        builds = self.session.listBuilds(**kwargs)
        return builds if builds else []

    def get_build(self, build_id: int) -> Optional[Dict[str, Any]]:
        """
        Get build information by ID.
        
        Args:
            build_id: Build ID
            
        Returns:
            Build info dict or None
        """
        return self.session.getBuild(build_id)
    
    def get_latest_builds(
        self,
        tag: str,
        package: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get latest builds in a tag.
        
        Args:
            tag: Tag name (e.g., 'f40-updates')
            package: Optional package name filter
            
        Returns:
            List of build dicts
        """
        return self.session.getLatestBuilds(tag, package=package)
    
    def list_tags(
        self,
        build_id: Optional[int] = None,
        package: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List tags.
        
        Args:
            build_id: Filter by build ID
            package: Filter by package name
            
        Returns:
            List of tag dicts
        """
        if build_id:
            return self.session.listTags(build=build_id)
        elif package:
            return self.session.listTags(package=package)
        else:
            # Listing all tags can be huge, so don't do it
            return []
    
    def get_task_info(self, task_id: int) -> Optional[Dict[str, Any]]:
        """
        Get task information.
        
        Args:
            task_id: Task ID
            
        Returns:
            Task info dict or None
        """
        return self.session.getTaskInfo(task_id)
    
    def list_tasks(
        self,
        user_id: Optional[int] = None,
        state: Optional[List[int]] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        List tasks.
        
        Args:
            user_id: Filter by user ID
            state: Filter by task states (0=free, 1=open, 2=closed, 3=canceled, 4=assigned, 5=failed)
            limit: Maximum number of results
            
        Returns:
            List of task dicts
        """
        opts = {}
        if user_id is not None:
            opts['owner'] = user_id
        if state is not None:
            opts['state'] = state
        
        return self.session.listTasks(opts=opts)[:limit]

    def list_task_output(self, task_id: int) -> Dict[str, Any]:
        """
        List available output files for a task.
        
        Args:
            task_id: Task ID
            
        Returns:
            Dict with task output file listing
        """
        try:
            # listTaskOutput returns a dict with 'files' key
            result = self.session.listTaskOutput(task_id)
            # Result is actually just a list of filenames
            if isinstance(result, list):
                return {"files": result}
            return result
        except Exception as e:
            return {"error": str(e), "files": []}

    def download_task_output(
        self,
        task_id: int,
        filename: str,
        offset: int = 0,
        size: int = 102400  # 100KB default
    ) -> str:
        """
        Download (part of) a task output file.

        Args:
            task_id: Task ID
            filename: Output filename (e.g., 'build.log', 'root.log')
            offset: Byte offset to start reading from
            size: Maximum bytes to read (default 100KB)

        Returns:
            File content as string
        """
        try:
            # downloadTaskOutput returns raw bytes
            content = self.session.downloadTaskOutput(task_id, filename, offset, size)
            # Decode as UTF-8, replacing invalid chars
            return content.decode('utf-8', errors='replace')
        except Exception as e:
            return f"Error downloading {filename}: {str(e)}"
