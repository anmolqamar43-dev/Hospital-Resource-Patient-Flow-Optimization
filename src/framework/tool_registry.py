"""
Tool Registry and BaseTool abstraction for agent execution.
"""

from typing import Dict, Any, Callable, Optional, List
from dataclasses import dataclass, field
import traceback
import json


@dataclass
class ToolResult:
    success: bool
    data: Any
    message: str = ""
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "message": self.message,
            "error": self.error
        }


class BaseTool:
    """
    Abstract Base Tool for clinical and operational analytical capabilities.
    """
    name: str = "base_tool"
    description: str = "Base tool description"
    required_parameters: List[str] = []

    def execute(self, state: Any, **kwargs) -> ToolResult:
        raise NotImplementedError("Tool execution must be implemented by subclass.")

    def validate_inputs(self, kwargs: Dict[str, Any]) -> Optional[str]:
        for param in self.required_parameters:
            if param not in kwargs:
                return f"Missing required parameter: {param}"
        return None


class ToolRegistry:
    """
    Central registry of callable tools for agents.
    """

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._execution_history: List[Dict[str, Any]] = []

    def register(self, tool: BaseTool):
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, str]]:
        return [{"name": t.name, "description": t.description} for t in self._tools.values()]

    def invoke(self, tool_name: str, state: Any, caller_agent: str = "system", **kwargs) -> ToolResult:
        tool = self._tools.get(tool_name)
        if not tool:
            return ToolResult(success=False, data=None, error=f"Tool '{tool_name}' not found.")

        validation_err = tool.validate_inputs(kwargs)
        if validation_err:
            return ToolResult(success=False, data=None, error=validation_err)

        try:
            result = tool.execute(state, **kwargs)
            self._execution_history.append({
                "tool": tool_name,
                "caller": caller_agent,
                "success": result.success,
                "message": result.message
            })
            return result
        except Exception as e:
            err_msg = f"Exception in tool '{tool_name}': {str(e)}\n{traceback.format_exc()}"
            self._execution_history.append({
                "tool": tool_name,
                "caller": caller_agent,
                "success": False,
                "error": str(e)
            })
            return ToolResult(success=False, data=None, error=err_msg)
