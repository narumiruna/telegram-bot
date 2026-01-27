import subprocess

from agents import function_tool
from loguru import logger


@function_tool
def execute_command(command: str) -> str:
    """Executes a shell command and returns its output.

    Args:
        command (str): The shell command to execute.

    Returns:
        str: The output of the command.
    """
    logger.info("Executing command: {command}", command=command)
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        logger.error("Command failed with error: {error}", error=e.stderr)
        return f"Error executing command: {e.stderr}"

    return result.stdout
