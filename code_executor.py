"""Code executor for MCP code mode pattern with sandboxing"""

import io
import signal
from contextlib import redirect_stdout, redirect_stderr
from typing import Optional, Dict, Any


# Restricted builtins - remove dangerous functions
SAFE_BUILTINS = {
    'abs': abs,
    'all': all,
    'any': any,
    'bool': bool,
    'dict': dict,
    'enumerate': enumerate,
    'float': float,
    'int': int,
    'len': len,
    'list': list,
    'max': max,
    'min': min,
    'print': print,
    'range': range,
    'str': str,
    'sum': sum,
    'tuple': tuple,
    'zip': zip,
    'isinstance': isinstance,
    'type': type,
    'getattr': getattr,
    'hasattr': hasattr,
}


class TimeoutException(Exception):
    """Raised when code execution times out"""
    pass


def timeout_handler(signum, frame):
    """Signal handler for timeout"""
    raise TimeoutException("Code execution timed out")


def execute_code(
    code: str,
    capture_output: bool = True,
    globals_dict: Optional[Dict[str, Any]] = None,
    timeout: int = 30,
    allow_imports: bool = True
) -> dict:
    """Execute Python code with sandboxing.

    Args:
        code: Python code to execute
        capture_output: Whether to capture stdout/stderr
        globals_dict: Additional globals to inject (e.g., tool registry)
        timeout: Maximum execution time in seconds (default: 30)
        allow_imports: Whether to allow import statements (default: True)

    Note:
        Timeout only works on Unix/macOS. Windows does not support signal.SIGALRM.
    """
    result = {
        'success': False,
        'stdout': '',
        'stderr': '',
        'variables': {},
        'error': None
    }

    try:
        # Setup restricted builtins
        exec_globals = {
            '__builtins__': SAFE_BUILTINS if not allow_imports else __builtins__,
        }

        # Merge with provided globals (e.g., tools registry)
        if globals_dict:
            exec_globals.update(globals_dict)

        exec_locals = {}

        # Set timeout alarm (Unix/macOS only)
        if hasattr(signal, 'SIGALRM'):
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(timeout)

        try:
            if capture_output:
                stdout = io.StringIO()
                stderr = io.StringIO()
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    # Check if code uses async
                    if 'await ' in code or 'async ' in code:
                        # Wrap in async function
                        wrapped_code = f"""
async def __main__():
{chr(10).join('    ' + line for line in code.split(chr(10)))}
    return locals()

import asyncio
import nest_asyncio
# Allow nested event loops (needed when called from async context)
nest_asyncio.apply()
# Run the async function
__result__ = asyncio.run(__main__())
"""
                        exec(wrapped_code, exec_globals, exec_locals)
                        if '__result__' in exec_locals:
                            exec_locals.update(exec_locals['__result__'])
                    else:
                        exec(code, exec_globals, exec_locals)

                result['stdout'] = stdout.getvalue()
                result['stderr'] = stderr.getvalue()
            else:
                exec(code, exec_globals, exec_locals)

            # Extract result variable if exists
            if 'result' in exec_locals:
                result['variables']['result'] = exec_locals['result']

            result['success'] = True

        finally:
            # Cancel alarm
            if hasattr(signal, 'SIGALRM'):
                signal.alarm(0)

    except TimeoutException:
        result['error'] = f"Execution timed out after {timeout} seconds"
        result['success'] = False
    except Exception as e:
        result['error'] = str(e)
        result['success'] = False

    return result
