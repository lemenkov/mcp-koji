"""MCP server for Fedora Koji."""
import argparse
import asyncio
from fastmcp import FastMCP
from .client import KojiClient

import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("Koji MCP Server")
koji_client = KojiClient()


@mcp.tool()
async def get_user_info(username: str) -> str:
    """
    Get Koji user information.
    
    Args:
        username: Koji username (e.g., 'peter')
    """
    user = koji_client.get_user(username)
    
    if not user:
        return f"User '{username}' not found in Koji"
    
    response = f"**{user.get('name')}** (ID: {user.get('id')})\n"
    if user.get('krb_principals'):
        response += f"Kerberos: {', '.join(user.get('krb_principals'))}\n"
    response += f"Status: {'Active' if user.get('status') == 0 else 'Blocked'}\n"
    
    return response


@mcp.tool()
async def list_user_builds(
    username: str,
    state: str | None = None,
    limit: int = 20,
) -> str:
    """
    List builds for a specific user.
    
    Args:
        username: Koji username
        state: Filter by state (building, complete, failed, canceled)
        limit: Maximum number of results (default: 20)
    """
    # Get user ID first
    user = koji_client.get_user(username)
    if not user:
        return f"User '{username}' not found in Koji"
    
    # Map state names to IDs
    state_map = {
        'building': 0,
        'complete': 1,
        'failed': 3,
        'canceled': 4,
    }
    
    state_id = None
    if state:
        state_id = state_map.get(state.lower())
        if state_id is None:
            return f"Invalid state. Use: building, complete, failed, or canceled"
    
    builds = koji_client.list_builds(
        user_id=user['id'],
        state=state_id,
        limit=limit,
    )
    
    if not builds:
        return f"No builds found for user '{username}'"
    
    response = f"Found {len(builds)} builds for {username}:\n\n"
    
    for build in builds:
        nvr = build.get('nvr', 'N/A')
        state_name = ['BUILDING', 'COMPLETE', 'DELETED', 'FAILED', 'CANCELED'][build.get('state', 1)]
        build_id = build.get('build_id', 'N/A')
        
        response += f"**{nvr}** (ID: {build_id})\n"
        response += f"  State: {state_name}\n"
        if build.get('completion_time'):
            response += f"  Completed: {build.get('completion_time')}\n"
        response += "\n"
    
    return response


@mcp.tool()
async def get_build_info(build_id: int) -> str:
    """
    Get detailed information about a specific build.
    
    Args:
        build_id: Koji build ID
    """
    try:
        build = koji_client.get_build(build_id)
    except ValueError as e:
        return str(e)
    
    if not build:
        return f"Build ID {build_id} not found"
    
    response = f"**{build.get('nvr')}** (ID: {build.get('build_id')})\n\n"
    response += f"Package: {build.get('package_name')}\n"
    response += f"Version: {build.get('version')}-{build.get('release')}\n"
    
    state_name = ['BUILDING', 'COMPLETE', 'DELETED', 'FAILED', 'CANCELED'][build.get('state', 1)]
    response += f"State: {state_name}\n"
    
    if build.get('owner_name'):
        response += f"Owner: {build.get('owner_name')}\n"
    
    if build.get('task_id'):
        response += f"Task ID: {build.get('task_id')}\n"
    
    if build.get('creation_time'):
        response += f"Created: {build.get('creation_time')}\n"
    
    if build.get('completion_time'):
        response += f"Completed: {build.get('completion_time')}\n"
    
    return response


@mcp.tool()
async def get_latest_builds(tag: str, package: str | None = None) -> str:
    """
    Get latest builds in a specific tag.
    
    Args:
        tag: Tag name (e.g., 'f40-updates', 'rawhide')
        package: Optional package name to filter
    """
    try:
        builds = koji_client.get_latest_builds(tag, package=package)
    except ValueError as e:
        return str(e)
    
    if not builds:
        if package:
            return f"No builds found for package '{package}' in tag '{tag}'"
        else:
            return f"No builds found in tag '{tag}'"
    
    response = f"Latest builds in '{tag}'"
    if package:
        response += f" for package '{package}'"
    response += f" ({len(builds)} builds):\n\n"
    
    for build in builds[:20]:  # Limit to 20 for display
        nvr = build.get('nvr', 'N/A')
        build_id = build.get('build_id', 'N/A')
        owner = build.get('owner_name', 'N/A')
        
        response += f"**{nvr}** (ID: {build_id})\n"
        response += f"  Owner: {owner}\n"
        if build.get('completion_time'):
            response += f"  Completed: {build.get('completion_time')}\n"
        response += "\n"
    
    if len(builds) > 20:
        response += f"\n... and {len(builds) - 20} more builds"
    
    return response


@mcp.tool()
async def list_build_tags(build_id: int) -> str:
    """
    List tags for a specific build.
    
    Args:
        build_id: Koji build ID
    """
    tags = koji_client.list_tags(build_id=build_id)
    
    if not tags:
        return f"No tags found for build ID {build_id}"
    
    response = f"Tags for build {build_id}:\n\n"
    
    for tag in tags:
        response += f"- {tag.get('name')}\n"
    
    return response


@mcp.tool()
async def get_task_info(task_id: int) -> str:
    """
    Get information about a Koji task.
    
    Args:
        task_id: Koji task ID
    """
    task = koji_client.get_task_info(task_id)
    
    if not task:
        return f"Task ID {task_id} not found"
    
    response = f"**Task {task.get('id')}**\n\n"
    response += f"Method: {task.get('method')}\n"
    
    state_names = ['FREE', 'OPEN', 'CLOSED', 'CANCELED', 'ASSIGNED', 'FAILED']
    state = task.get('state', 0)
    if 0 <= state < len(state_names):
        response += f"State: {state_names[state]}\n"
    
    if task.get('owner_name'):
        response += f"Owner: {task.get('owner_name')}\n"
    
    if task.get('arch'):
        response += f"Architecture: {task.get('arch')}\n"
    
    if task.get('create_time'):
        response += f"Created: {task.get('create_time')}\n"
    
    if task.get('completion_time'):
        response += f"Completed: {task.get('completion_time')}\n"
    
    return response
@mcp.tool()
async def list_task_logs(task_id: int) -> str:
    """
    List available log files for a Koji task.
    
    Args:
        task_id: Koji task ID
    """
    result = koji_client.list_task_output(task_id)
    
    if "error" in result:
        return f"Error listing logs for task {task_id}: {result['error']}"
    
    files = result.get("files", [])
    
    if not files:
        return f"No log files found for task {task_id}"
    
    response = f"Available log files for task {task_id}:\n\n"
    
    # Common log files and their descriptions
    log_descriptions = {
        "build.log": "Main build log",
        "root.log": "Root/mock environment log",
        "state.log": "Build state changes",
        "installed_pkgs.log": "Installed packages list",
        "hw_info.log": "Hardware information",
    }
    
    for filename in sorted(files):
        desc = log_descriptions.get(filename, "")
        if desc:
            response += f"- **{filename}** - {desc}\n"
        else:
            response += f"- {filename}\n"
    
    return response


@mcp.tool()
async def get_task_log(
    task_id: int,
    filename: str = "build.log",
    lines: int = 100,
    from_end: bool = True,
) -> str:
    """
    Get contents of a task log file.
    
    Args:
        task_id: Koji task ID
        filename: Log filename (default: 'build.log')
        lines: Number of lines to show (default: 100)
        from_end: If True, show last N lines; if False, show first N lines
    """
    # Download a reasonable chunk (512KB should be enough for most logs)
    size = 512 * 1024
    offset = 0
    
    content = koji_client.download_task_output(task_id, filename, offset, size)
    
    if content.startswith("Error downloading"):
        return content
    
    # Split into lines and get requested portion
    log_lines = content.strip().split('\n')
    
    if from_end:
        log_lines = log_lines[-lines:] if len(log_lines) > lines else log_lines
    else:
        log_lines = log_lines[:lines]
    
    response = f"**{filename}** for task {task_id}"
    if from_end:
        response += f" (last {len(log_lines)} lines):\n\n"
    else:
        response += f" (first {len(log_lines)} lines):\n\n"
    
    response += "```\n"
    response += '\n'.join(log_lines)
    response += "\n```"
    
    return response


def main():
    """Run the MCP server."""
    parser = argparse.ArgumentParser(description="Koji MCP Server")
    parser.add_argument("--koji-url", 
                       default="https://koji.fedoraproject.org/kojihub",
                       help="Koji hub URL")
    parser.add_argument("--host", default="127.0.0.1", 
                       help="Host to listen on")
    parser.add_argument("--port", type=int, default=8803, 
                       help="Port to listen on")
    args = parser.parse_args()
    
    global koji_client
    koji_client = KojiClient(koji_url=args.koji_url)
    
    # Run the server
    mcp.run(transport="http", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
