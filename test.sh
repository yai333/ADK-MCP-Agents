#!/bin/bash
# Clean test runner that filters out MCP cleanup warnings

echo "Running tests with clean output (filtering MCP cleanup warnings)..."
echo ""

if [ "$1" = "direct" ]; then
    uv run test_direct_agent.py 2>&1 | grep -vE "asyncgen:|Exception Group|Traceback|File \"|anyio|RuntimeError|BaseExceptionGroup|GeneratorExit|Warning: there are non-text"
elif [ "$1" = "code" ]; then
    uv run test_code_mode_agent.py 2>&1 | grep -vE "asyncgen:|Exception Group|Traceback|File \"|anyio|RuntimeError|BaseExceptionGroup|GeneratorExit|Warning: there are non-text"
elif [ "$1" = "all" ]; then
    uv run example.py 2>&1 | grep -vE "asyncgen:|Exception Group|Traceback|File \"|anyio|RuntimeError|BaseExceptionGroup|GeneratorExit|Warning: there are non-text"
else
    echo "Usage: ./test.sh [direct|code|all]"
    echo ""
    echo "  direct - Test direct agent only"
    echo "  code   - Test code mode agent only"
    echo "  all    - Run all tests"
    exit 1
fi
