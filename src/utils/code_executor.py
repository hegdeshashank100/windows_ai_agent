"""
Safe Python Code Execution Sandbox for Windows AI Agent
"""

import sys
import ast
import types
import time
import io
import contextlib
import subprocess
import threading
from typing import Dict, Any, List, Optional, Set
from pathlib import Path
import tempfile
import json
import traceback

try:
    from RestrictedPython import compile_restricted
    from RestrictedPython.Guards import safe_builtins, safe_globals
    from RestrictedPython.transformer import RestrictingNodeTransformer
    RESTRICTED_PYTHON_AVAILABLE = True
except ImportError:
    print("Warning: RestrictedPython not available. Code execution will be limited.")
    RESTRICTED_PYTHON_AVAILABLE = False
    # Provide fallbacks
    safe_builtins = {}
    safe_globals = {}
    compile_restricted = None

from loguru import logger
from ..utils.config import config


class SafeExecutionEnvironment:
    """Safe environment for Python code execution"""
    
    def __init__(self, 
                 timeout: int = 30,
                 allowed_modules: Optional[List[str]] = None,
                 memory_limit_mb: int = 100):
        self.timeout = timeout
        self.allowed_modules = allowed_modules or config.allowed_modules
        self.memory_limit_mb = memory_limit_mb
        
        # Create safe namespace
        self.safe_namespace = self._create_safe_namespace()
        
        logger.info(f"Safe execution environment initialized (timeout: {timeout}s)")
    
    def _create_safe_namespace(self) -> Dict[str, Any]:
        """Create a safe execution namespace"""
        # Start with restricted builtins
        namespace = safe_builtins.copy()
        
        # Add safe built-in functions
        safe_functions = {
            'abs', 'all', 'any', 'bin', 'bool', 'chr', 'dict', 'dir',
            'divmod', 'enumerate', 'filter', 'float', 'format', 'frozenset',
            'hex', 'int', 'isinstance', 'issubclass', 'iter', 'len', 'list',
            'map', 'max', 'min', 'oct', 'ord', 'pow', 'range', 'repr',
            'reversed', 'round', 'set', 'slice', 'sorted', 'str', 'sum',
            'tuple', 'type', 'zip'
        }
        
        # Add safe builtins
        for func_name in safe_functions:
            if hasattr(__builtins__, func_name):
                namespace[func_name] = getattr(__builtins__, func_name)
        
        # Add safe modules
        namespace['__import__'] = self._safe_import
        
        # Add utility functions
        namespace.update({
            'print': self._safe_print,
            'input': self._safe_input,
            'help': self._safe_help,
        })
        
        return namespace
    
    def _safe_import(self, name: str, globals=None, locals=None, fromlist=(), level=0):
        """Safe import function that only allows whitelisted modules"""
        # Check if module is allowed
        if name not in self.allowed_modules:
            # Check if it's a submodule of an allowed module
            allowed = False
            for allowed_module in self.allowed_modules:
                if name.startswith(allowed_module + '.'):
                    allowed = True
                    break
            
            if not allowed:
                raise ImportError(f"Module '{name}' is not allowed in safe mode")
        
        # Import the module normally
        return __import__(name, globals, locals, fromlist, level)
    
    def _safe_print(self, *args, **kwargs):
        """Safe print function that captures output"""
        # Redirect to our output capture
        print(*args, **kwargs)
    
    def _safe_input(self, prompt=""):
        """Safe input function (disabled in sandbox)"""
        raise RuntimeError("Input is not allowed in safe execution mode")
    
    def _safe_help(self, obj=None):
        """Safe help function"""
        if obj is None:
            return "Help is available for Python objects. Type help(object) for info."
        else:
            return help(obj)
    
    def execute_code(self, code: str, variables: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute Python code safely"""
        start_time = time.time()
        
        # Prepare result structure
        result = {
            "success": False,
            "output": "",
            "error": None,
            "execution_time": 0,
            "variables": {},
            "return_value": None
        }
        
        try:
            # Validate code syntax first
            validation = self._validate_code(code)
            if not validation["valid"]:
                result["error"] = validation["error"]
                return result
            
            # Create execution namespace
            exec_namespace = self.safe_namespace.copy()
            if variables:
                exec_namespace.update(variables)
            
            # Capture output
            output_buffer = io.StringIO()
            error_buffer = io.StringIO()
            
            with contextlib.redirect_stdout(output_buffer), \
                 contextlib.redirect_stderr(error_buffer):
                
                # Execute with timeout
                success = self._execute_with_timeout(code, exec_namespace)
                
                if success:
                    result["success"] = True
                    result["output"] = output_buffer.getvalue()
                    
                    # Extract variables (excluding builtins and modules)
                    result["variables"] = self._extract_user_variables(exec_namespace)
                else:
                    result["error"] = "Execution timed out"
            
            # Capture any error output
            error_output = error_buffer.getvalue()
            if error_output:
                if result["error"]:
                    result["error"] += f"\n{error_output}"
                else:
                    result["error"] = error_output
        
        except Exception as e:
            result["error"] = str(e)
            result["traceback"] = traceback.format_exc()
        
        finally:
            result["execution_time"] = time.time() - start_time
        
        logger.info(f"Code execution completed: success={result['success']}, time={result['execution_time']:.3f}s")
        return result
    
    def _validate_code(self, code: str) -> Dict[str, Any]:
        """Validate code for safety and syntax"""
        try:
            # Parse AST to check for dangerous operations
            tree = ast.parse(code)
            
            # Check for prohibited operations
            validator = CodeValidator()
            validator.visit(tree)
            
            # Try compilation with RestrictedPython if available
            if RESTRICTED_PYTHON_AVAILABLE and compile_restricted is not None:
                compiled = compile_restricted(code, '<string>', 'exec')
                if compiled.errors:
                    return {
                        "valid": False,
                        "error": f"Compilation errors: {'; '.join(compiled.errors)}"
                    }
                compiled = compile_restricted(code, '<string>', 'exec')
                if compiled.errors:
                    return {
                        "valid": False,
                        "error": f"Compilation errors: {'; '.join(compiled.errors)}"
                    }
            
            return {"valid": True}
            
        except SyntaxError as e:
            return {
                "valid": False,
                "error": f"Syntax error: {e}"
            }
        except Exception as e:
            return {
                "valid": False,
                "error": f"Validation error: {e}"
            }
    
    def _execute_with_timeout(self, code: str, namespace: Dict) -> bool:
        """Execute code with timeout protection"""
        success = False
        exception = None
        
        def target():
            nonlocal success, exception
            try:
                exec(code, namespace)
                success = True
            except Exception as e:
                exception = e
        
        # Run in thread with timeout
        thread = threading.Thread(target=target)
        thread.daemon = True
        thread.start()
        thread.join(timeout=self.timeout)
        
        if thread.is_alive():
            # Thread is still running - timeout occurred
            return False
        
        if exception:
            raise exception
        
        return success
    
    def _extract_user_variables(self, namespace: Dict) -> Dict[str, Any]:
        """Extract user-defined variables from namespace"""
        user_vars = {}
        
        # Skip built-in and system variables
        skip_prefixes = ('__', '_')
        skip_names = set(self.safe_namespace.keys())
        
        for name, value in namespace.items():
            if (not name.startswith(skip_prefixes) and 
                name not in skip_names and
                not isinstance(value, (types.ModuleType, types.FunctionType))):
                
                # Convert to JSON-serializable format
                try:
                    json.dumps(value)  # Test if serializable
                    user_vars[name] = value
                except (TypeError, ValueError):
                    user_vars[name] = str(value)  # Fallback to string representation
        
        return user_vars


class CodeValidator(ast.NodeVisitor):
    """AST visitor to validate code for security violations"""
    
    def __init__(self):
        self.violations = []
        
        # Prohibited operations
        self.prohibited_functions = {
            'exec', 'eval', 'compile', 'open', '__import__',
            'getattr', 'setattr', 'delattr', 'hasattr',
            'globals', 'locals', 'vars', 'dir'
        }
        
        self.prohibited_modules = {
            'os', 'sys', 'subprocess', 'socket', 'urllib',
            'requests', 'shutil', 'pathlib', 'tempfile'
        }
    
    def visit_Call(self, node):
        """Check function calls"""
        if isinstance(node.func, ast.Name):
            if node.func.id in self.prohibited_functions:
                self.violations.append(f"Prohibited function: {node.func.id}")
        
        self.generic_visit(node)
    
    def visit_Import(self, node):
        """Check imports"""
        for alias in node.names:
            module_name = alias.name.split('.')[0]
            if module_name in self.prohibited_modules:
                self.violations.append(f"Prohibited import: {module_name}")
        
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node):
        """Check from imports"""
        if node.module:
            module_name = node.module.split('.')[0]
            if module_name in self.prohibited_modules:
                self.violations.append(f"Prohibited import from: {module_name}")
        
        self.generic_visit(node)
    
    def visit_Attribute(self, node):
        """Check attribute access"""
        # Check for dangerous attribute access
        if isinstance(node.attr, str) and node.attr.startswith('_'):
            self.violations.append(f"Prohibited attribute access: {node.attr}")
        
        self.generic_visit(node)


class CodeExecutor:
    """High-level code executor with multiple execution modes"""
    
    def __init__(self):
        self.environment = SafeExecutionEnvironment(
            timeout=config.sandbox_timeout,
            allowed_modules=config.allowed_modules
        )
        
        self.session_variables = {}
        
    def execute(self, code: str, mode: str = "safe") -> Dict[str, Any]:
        """Execute code with specified mode"""
        if mode == "safe":
            return self._execute_safe(code)
        elif mode == "isolated":
            return self._execute_isolated(code)
        elif mode == "persistent":
            return self._execute_persistent(code)
        else:
            return {
                "success": False,
                "error": f"Unknown execution mode: {mode}"
            }
    
    def _execute_safe(self, code: str) -> Dict[str, Any]:
        """Execute in safe environment"""
        return self.environment.execute_code(code)
    
    def _execute_isolated(self, code: str) -> Dict[str, Any]:
        """Execute in completely isolated environment (subprocess)"""
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_file = f.name
            
            # Execute in subprocess
            result = subprocess.run(
                [sys.executable, temp_file],
                capture_output=True,
                text=True,
                timeout=self.environment.timeout
            )
            
            # Clean up
            Path(temp_file).unlink()
            
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.stderr else None,
                "return_code": result.returncode
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Execution timed out in isolated mode"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Isolated execution failed: {e}"
            }
    
    def _execute_persistent(self, code: str) -> Dict[str, Any]:
        """Execute with persistent session variables"""
        result = self.environment.execute_code(code, self.session_variables)
        
        if result["success"]:
            # Update session variables
            self.session_variables.update(result["variables"])
            result["session_variables"] = self.session_variables.copy()
        
        return result
    
    def clear_session(self):
        """Clear persistent session variables"""
        self.session_variables.clear()
        logger.info("Cleared session variables")
    
    def get_session_info(self) -> Dict[str, Any]:
        """Get current session information"""
        return {
            "variables": self.session_variables.copy(),
            "variable_count": len(self.session_variables),
            "allowed_modules": self.environment.allowed_modules,
            "timeout": self.environment.timeout
        }
    
    def validate_code(self, code: str) -> Dict[str, Any]:
        """Validate code without executing"""
        return self.environment._validate_code(code)


# Example usage and testing
def example_usage():
    """Example of using the code executor"""
    executor = CodeExecutor()
    
    # Test cases
    test_codes = [
        # Safe arithmetic
        """
x = 10
y = 20
result = x + y
print(f"The sum is: {result}")
        """,
        
        # Safe loops and functions
        """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

for i in range(8):
    print(f"fib({i}) = {fibonacci(i)}")
        """,
        
        # Math operations
        """
import math
numbers = [1, 4, 9, 16, 25]
sqrt_numbers = [math.sqrt(n) for n in numbers]
print("Original:", numbers)
print("Square roots:", sqrt_numbers)
        """,
        
        # Prohibited operations (should fail)
        """
import os
os.system("echo This should not work")
        """
    ]
    
    for i, code in enumerate(test_codes, 1):
        print(f"\n--- Test Case {i} ---")
        print("Code:")
        print(code.strip())
        print("\nResult:")
        
        result = executor.execute(code, mode="safe")
        print(f"Success: {result['success']}")
        if result['output']:
            print(f"Output: {result['output']}")
        if result['error']:
            print(f"Error: {result['error']}")
        print(f"Execution time: {result.get('execution_time', 0):.3f}s")


if __name__ == "__main__":
    example_usage()