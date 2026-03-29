"""
Tests for REQ-06: Tool Definition and Registration Framework
"""

import pytest


def test_tool_interface_and_registration():
    """Test that a mock tool can be registered and retrieved"""
    from src.tool_registry import Tool, register_tool, get_tool

    # Create a mock tool
    class MockTool(Tool):
        @property
        def name(self) -> str:
            return "mock"

        @property
        def description(self) -> str:
            return "A mock tool for testing"

        @property
        def parameters(self) -> dict:
            return {
                "type": "object",
                "properties": {"input": {"type": "string", "description": "Test input"}},
                "required": ["input"],
            }

        def execute(self, params: dict) -> str:
            return f"Executed with: {params.get('input')}"

    # Register the tool
    tool = MockTool()
    register_tool(tool)

    # Retrieve the tool
    retrieved = get_tool("mock")
    assert retrieved is tool
    assert retrieved.name == "mock"
    assert retrieved.description == "A mock tool for testing"
    assert "input" in retrieved.parameters["properties"]


def test_openai_tools_schema_format():
    """Test that get_openai_tools_schema returns valid OpenAI format"""
    from src.tool_registry import Tool, register_tool, get_openai_tools_schema

    # Create and register a test tool
    class SchemaTestTool(Tool):
        @property
        def name(self) -> str:
            return "schema_test"

        @property
        def description(self) -> str:
            return "Test tool for schema validation"

        @property
        def parameters(self) -> dict:
            return {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "A file path"}},
                "required": ["path"],
            }

        def execute(self, params: dict) -> str:
            return "ok"

    register_tool(SchemaTestTool())

    # Get the schema
    schema = get_openai_tools_schema()

    # Verify it's a list
    assert isinstance(schema, list)

    # Find our tool in the schema
    tool_entry = None
    for entry in schema:
        if entry.get("function", {}).get("name") == "schema_test":
            tool_entry = entry
            break

    assert tool_entry is not None, "Tool not found in schema"
    assert tool_entry["type"] == "function"
    assert "function" in tool_entry

    function_def = tool_entry["function"]
    assert function_def["name"] == "schema_test"
    assert function_def["description"] == "Test tool for schema validation"
    assert "parameters" in function_def
    assert function_def["parameters"]["type"] == "object"
    assert "path" in function_def["parameters"]["properties"]


def test_duplicate_registration_raises_error():
    """Test that registering a tool with duplicate name raises an error"""
    from src.tool_registry import Tool, register_tool, reset_registry

    # Reset registry to ensure clean state
    reset_registry()

    class DuplicateTool(Tool):
        @property
        def name(self) -> str:
            return "duplicate"

        @property
        def description(self) -> str:
            return "A duplicate tool"

        @property
        def parameters(self) -> dict:
            return {"type": "object", "properties": {}}

        def execute(self, params: dict) -> str:
            return "ok"

    # Register first instance
    register_tool(DuplicateTool())

    # Try to register second instance with same name
    with pytest.raises(ValueError, match="Tool already registered: duplicate"):
        register_tool(DuplicateTool())


def test_get_nonexistent_tool_returns_none():
    """Test that get_tool returns None for unregistered tools"""
    from src.tool_registry import get_tool, reset_registry

    # Reset registry to ensure clean state
    reset_registry()

    # Try to get a non-existent tool
    result = get_tool("nonexistent")
    assert result is None
