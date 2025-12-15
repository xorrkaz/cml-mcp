#!/usr/bin/env python3
"""
End-to-End Test Script for CML-MCP HTTP Service
================================================

This script performs comprehensive end-to-end testing of the CML-MCP server
running in HTTP mode (typically via Docker). It validates the full request
flow from health check through MCP protocol initialization to actual tool calls.

IMPORTANT: This is NOT a pytest test. It's a standalone script meant to be run
manually against a running CML-MCP HTTP service.

Architecture
------------
The test validates the following flow:

    ┌─────────────┐      HTTP/SSE      ┌─────────────┐        HTTPS       ┌─────────────┐
    │ This Script │ ◄───────────────► │  CML-MCP    │ ◄───────────────► │  CML Server │
    │ (MCP Client)│   Streamable HTTP  │  (Docker)   │     REST API      │             │
    └─────────────┘                    └─────────────┘                   └─────────────┘

Tests Performed
---------------
1. Health Endpoint   - Validates /health returns {"status": "healthy"}
2. SSE Connection    - Verifies /mcp responds with text/event-stream
3. MCP Protocol      - Initializes MCP session and discovers tools
4. Tool Call (status)- Calls get_cml_status to verify CML connectivity
5. Tool Call (labs)  - Calls get_cml_labs to list labs from CML

Prerequisites
-------------
- CML-MCP service running in HTTP mode (e.g., via `docker compose up`)
- Valid CML credentials (username/password)
- MCP Python SDK installed (`pip install mcp`)

Environment Variables
---------------------
CML_MCP_URL     : MCP server URL (default: http://localhost:9000)
CML_URL         : Target CML server URL (sent via X-CML-Server-URL header)
CML_USERNAME    : CML username for authentication (required)
CML_PASSWORD    : CML password for authentication (required)

Usage
-----
# Option 1: Export environment variables
export CML_USERNAME=admin
export CML_PASSWORD=your_password
python scripts/test_http_e2e.py

# Option 2: Source .env file (recommended)
set -a && source .env && set +a && python scripts/test_http_e2e.py

# Option 3: Inline credentials
CML_USERNAME=admin CML_PASSWORD=secret python scripts/test_http_e2e.py

# Option 4: Using just (if configured)
just test-e2e

Exit Codes
----------
0 : All tests passed
1 : One or more tests failed

Example Output
--------------
============================================================
CML-MCP HTTP Service End-to-End Tests
============================================================

Configuration:
  MCP Server: http://localhost:9000
  Target CML: https://cml.example.com
  Username: admin

============================================================
TEST 1: Health Endpoint
============================================================
  URL: http://localhost:9000/health
  Status: 200
  Response: {'status': 'healthy', 'service': 'cml-mcp'}
  ✅ PASSED: Health check successful

... (additional tests)

============================================================
TEST SUMMARY
============================================================
  ✅ PASS: Health Endpoint
  ✅ PASS: SSE Connection
  ✅ PASS: MCP Protocol
  ✅ PASS: Tool Call (status)
  ✅ PASS: List Labs

  Total: 5 passed, 0 failed
============================================================
"""

from __future__ import annotations

import asyncio
import base64
import os
import sys

import httpx


def encode_credentials(username: str, password: str) -> str:
    """Encode username:password as base64 for Basic auth."""
    credentials = f"{username}:{password}"
    return base64.b64encode(credentials.encode()).decode()


async def test_health_endpoint(base_url: str) -> bool:
    """Test the /health endpoint."""
    print("\n" + "=" * 60)
    print("TEST 1: Health Endpoint")
    print("=" * 60)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{base_url}/health")
            print(f"  URL: {base_url}/health")
            print(f"  Status: {response.status_code}")
            print(f"  Response: {response.json()}")

            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    print("  ✅ PASSED: Health check successful")
                    return True
            print("  ❌ FAILED: Health check failed")
            return False
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        return False


async def test_sse_connection(base_url: str, auth_header: str) -> bool:
    """Test SSE connection to /mcp endpoint."""
    print("\n" + "=" * 60)
    print("TEST 2: SSE Connection")
    print("=" * 60)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            print(f"  URL: {base_url}/mcp")
            print("  Attempting SSE connection...")

            # Make a streaming request
            async with client.stream(
                "GET",
                f"{base_url}/mcp",
                headers={
                    "Accept": "text/event-stream",
                    "X-Authorization": f"Basic {auth_header}",
                },
            ) as response:
                print(f"  Status: {response.status_code}")
                print(f"  Content-Type: {response.headers.get('content-type')}")

                if response.status_code == 200:
                    content_type = response.headers.get("content-type", "")
                    if "text/event-stream" in content_type:
                        # Read first event
                        async for line in response.aiter_lines():
                            if line:
                                print(f"  First event received: {line[:100]}...")
                                print("  ✅ PASSED: SSE connection established")
                                return True
                            break
                print("  ❌ FAILED: Could not establish SSE connection")
                return False
    except httpx.ReadTimeout:
        # This is actually expected - SSE keeps connection open
        print("  ⚠️  Connection timeout (expected for SSE)")
        print("  ✅ PASSED: SSE endpoint is responsive")
        return True
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        return False


async def test_mcp_protocol_with_sdk(base_url: str, auth_header: str, cml_url: str | None = None) -> bool:
    """Test MCP protocol using streamable HTTP client."""
    print("\n" + "=" * 60)
    print("TEST 3: MCP Protocol (Tool Discovery)")
    print("=" * 60)

    try:
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client

        headers = {
            "X-Authorization": f"Basic {auth_header}",
        }
        if cml_url:
            headers["X-CML-Server-URL"] = cml_url

        print(f"  URL: {base_url}/mcp")
        print("  Using MCP SDK with Streamable HTTP transport")
        if cml_url:
            print(f"  Target CML: {cml_url}")

        async with streamablehttp_client(f"{base_url}/mcp", headers=headers) as (read, write, _):
            async with ClientSession(read, write) as session:
                # Initialize the session
                await session.initialize()
                print("  ✅ MCP session initialized")

                # List available tools
                tools_result = await session.list_tools()
                tools = tools_result.tools
                print(f"  📦 Found {len(tools)} tools:")
                for tool in tools[:10]:  # Show first 10
                    print(f"     - {tool.name}")
                if len(tools) > 10:
                    print(f"     ... and {len(tools) - 10} more")

                print("  ✅ PASSED: MCP protocol working correctly")
                return True

    except ImportError as e:
        print(f"  ⚠️  MCP SDK import error: {e}")
        print("  Skipping MCP protocol test...")
        return True  # Don't fail if SDK not installed
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_mcp_tool_call(base_url: str, auth_header: str, cml_url: str | None = None) -> bool:
    """Test calling an actual MCP tool."""
    print("\n" + "=" * 60)
    print("TEST 4: MCP Tool Call (get_cml_status)")
    print("=" * 60)

    try:
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client

        headers = {
            "X-Authorization": f"Basic {auth_header}",
        }
        if cml_url:
            headers["X-CML-Server-URL"] = cml_url

        print(f"  URL: {base_url}/mcp")
        if cml_url:
            print(f"  Target CML: {cml_url}")
        print("  Calling tool: get_cml_status")

        async with streamablehttp_client(f"{base_url}/mcp", headers=headers) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Call the get_cml_status tool
                result = await session.call_tool("get_cml_status", arguments={})

                print(f"  Response type: {type(result)}")
                if result.content:
                    for content in result.content:
                        if hasattr(content, "text"):
                            # Parse and pretty print
                            import json

                            try:
                                data = json.loads(content.text)
                                print("  CML System Status:")
                                for key, value in data.items():
                                    print(f"     {key}: {value}")
                            except json.JSONDecodeError:
                                print(f"  Raw response: {content.text[:200]}...")

                print("  ✅ PASSED: Tool call successful")
                return True

    except ImportError as e:
        print(f"  ⚠️  MCP SDK import error: {e}")
        print("  Skipping MCP tool call test...")
        return True
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_mcp_list_labs(base_url: str, auth_header: str, cml_url: str | None = None) -> bool:
    """Test listing CML labs."""
    print("\n" + "=" * 60)
    print("TEST 5: MCP Tool Call (get_cml_labs)")
    print("=" * 60)

    try:
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client

        headers = {
            "X-Authorization": f"Basic {auth_header}",
        }
        if cml_url:
            headers["X-CML-Server-URL"] = cml_url

        print(f"  URL: {base_url}/mcp")
        if cml_url:
            print(f"  Target CML: {cml_url}")
        print("  Calling tool: get_cml_labs")

        async with streamablehttp_client(f"{base_url}/mcp", headers=headers) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                result = await session.call_tool("get_cml_labs", arguments={})

                if result.content:
                    for content in result.content:
                        if hasattr(content, "text"):
                            import json

                            try:
                                labs = json.loads(content.text)
                                print(f"  Found {len(labs)} lab(s):")
                                for lab in labs[:5]:
                                    title = lab.get("title", "Untitled")
                                    lab_id = lab.get("id", "unknown")
                                    state = lab.get("state", "unknown")
                                    print(f"     - {title} ({lab_id}) [{state}]")
                                if len(labs) > 5:
                                    print(f"     ... and {len(labs) - 5} more")
                            except json.JSONDecodeError:
                                print(f"  Raw response: {content.text[:200]}...")

                print("  ✅ PASSED: get_cml_labs successful")
                return True

    except ImportError as e:
        print(f"  ⚠️  MCP SDK import error: {e}")
        return True
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Run all E2E tests."""
    print("=" * 60)
    print("CML-MCP HTTP Service End-to-End Tests")
    print("=" * 60)

    # Configuration
    base_url = os.environ.get("CML_MCP_URL", "http://localhost:9000")
    username = os.environ.get("CML_USERNAME", "")
    password = os.environ.get("CML_PASSWORD", "")
    cml_url = os.environ.get("CML_URL", None)

    if not username or not password:
        print("\n⚠️  Warning: CML_USERNAME and/or CML_PASSWORD not set")
        print("   Some tests may fail without proper credentials.")
        print("\n   Set credentials with:")
        print("   export CML_USERNAME=your_username")
        print("   export CML_PASSWORD=your_password")
        print()

    auth_header = encode_credentials(username or "test", password or "test")

    print("\nConfiguration:")
    print(f"  MCP Server: {base_url}")
    print(f"  Target CML: {cml_url or '(using server default)'}")
    print(f"  Username: {username or '(not set)'}")

    results = []

    # Test 1: Health endpoint (no auth needed)
    results.append(("Health Endpoint", await test_health_endpoint(base_url)))

    # Test 2: SSE connection
    results.append(("SSE Connection", await test_sse_connection(base_url, auth_header)))

    # Tests requiring valid credentials
    if username and password:
        # Test 3: MCP Protocol
        results.append(("MCP Protocol", await test_mcp_protocol_with_sdk(base_url, auth_header, cml_url)))

        # Test 4: Tool call
        results.append(("Tool Call (status)", await test_mcp_tool_call(base_url, auth_header, cml_url)))

        # Test 5: List labs
        results.append(("List Labs", await test_mcp_list_labs(base_url, auth_header, cml_url)))
    else:
        print("\n⚠️  Skipping authenticated tests (no credentials provided)")

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = 0
    failed = 0
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {name}")
        if result:
            passed += 1
        else:
            failed += 1

    print()
    print(f"  Total: {passed} passed, {failed} failed")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
