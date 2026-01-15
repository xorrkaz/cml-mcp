# Mock Testing Framework - Implementation Summary

## Overview

An optional mock framework has been created for the CML MCP server tests. Tests can run in two modes:

1. **Mock Mode (default)**: Uses pre-recorded API responses from `tests/mocks/` directory
2. **Live Mode**: Runs against a real CML server

## Implementation Details

### Architecture

The mock framework is implemented in `tests/conftest.py` and consists of:

1. **MockCMLClient Class**: A complete mock implementation of the CML API client that:
   - Loads mock data from JSON files in `tests/mocks/`
   - Simulates API responses for GET, POST, PUT, DELETE, and PATCH requests
   - Tracks created resources (labs, nodes, users, groups, etc.)
   - Generates unique IDs for created resources

2. **Module-Level Patching**: The framework patches `CMLClient` at module load time before the server module initializes, ensuring all tests use the mock client when `USE_MOCKS=true`

3. **Pytest Markers**: Tests are marked with:
   - `@pytest.mark.live_only`: Tests that create/modify resources (require live server)
   - Tests without markers: Read-only tests (work with mocks)

### Files Created/Modified

1. **`tests/conftest.py`** (new):
   - `MockCMLClient` class with full API mocking
   - Environment-based configuration (`USE_MOCKS`)
   - Automatic patching logic
   - Pytest fixtures and configuration

2. **`tests/README.md`** (new):
   - Comprehensive documentation for using the test framework
   - Usage examples for both modes
   - Mock data management instructions
   - Troubleshooting guide

3. **`tests/test_cml_mcp.py`** (modified):
   - Added module docstring explaining test modes
   - Marked 9 tests as `@pytest.mark.live_only`
   - Tests that modify state now skip in mock mode

## Test Results

### Mock Mode (USE_MOCKS=true)

- **10/10 read-only tests PASSING**
- Tests run in ~3 seconds
- No network calls, no external dependencies
- Safe for CI/CD pipelines

### Test Categories

**Read-Only Tests (Work with Mocks)**:

- ✅ test_list_tools
- ✅ test_get_cml_labs  
- ✅ test_get_cml_users
- ✅ test_get_cml_groups
- ✅ test_get_cml_information
- ✅ test_get_cml_status
- ✅ test_get_cml_statistics
- ✅ test_get_cml_licensing_details
- ✅ test_node_defs
- ✅ test_packet_capture_operations

**State-Modifying Tests (Require Live Server)**:

- 🔴 test_user_mgmt (marked `live_only`)
- 🔴 test_group_mgmt (marked `live_only`)
- 🔴 test_empty_lab_mgmt (marked `live_only`)
- 🔴 test_modify_cml_lab (marked `live_only`)
- 🔴 test_full_cml_topology (marked `live_only`)
- 🔴 test_intf_management (marked `live_only`)
- 🔴 test_add_annotation_to_cml_lab (marked `live_only`)
- 🔴 test_connect_two_nodes (marked `live_only`)
- 🔴 test_get_nodes_for_cml_lab (marked `live_only`)

## Usage

### Running Tests with Mocks (Default)

```bash
# Run all tests that work with mocks
pytest tests/

# Explicitly set mock mode
USE_MOCKS=true pytest tests/

# Run only tests compatible with mocks
pytest -m "not live_only" tests/
```

### Running Tests Against Live Server

```bash
# Set environment variables
export USE_MOCKS=false
export CML_URL=https://your-cml-server.com
export CML_USERNAME=admin
export CML_PASSWORD=yourpassword

# Run all tests
pytest tests/

# Run only live_only tests
pytest -m live_only tests/
```

## Mock Data Files

The following mock data files are used:

| File                                | Endpoint                                     | Description             |
| ----------------------------------- | -------------------------------------------- | ----------------------- |
| `get_labs.json`                     | `/labs`                                      | List of labs            |
| `get_users.json`                    | `/users`                                     | List of users           |
| `get_groups.json`                   | `/groups`                                    | List of groups          |
| `get_cml_info.json`                 | `/system_information`                        | System information      |
| `get_cml_status.json`               | `/system_health`                             | System health status    |
| `get_cml_statistics.json`           | `/system_stats`                              | System statistics       |
| `get_node_defs.json`                | `/simplified_node_definitions`               | Node definitions        |
| `get_node_def_detail.json`          | `/node_definitions/{id}`                     | Node definition         |
| `get_nodes_for_cml_lab.json`        | `/labs/{id}/nodes`                           | Nodes in a lab          |
| `get_interfaces_for_node.json`      | `/labs/{id}/nodes/{nid}/interfaces`          | Node interfaces         |
| `get_all_links_for_lab.json`        | `/labs/{id}/links`                           | Links in a lab          |
| `get_cml_lab_by_title.json`         | `/labs/{id}`                                 | Lab details             |
| `get_cml_licensing_details.json`    | `/licensing`                                 | Licensing info          |
| `get_annotations_for_cml_lab.json`  | `/labs/{id}/annotations`                     | Lab annotations         |
| `check_packet_capture_status.json`  | `/labs/{id}/links/{lid}/capture/status`      | Packet capture status   |
| `get_captured_packet_overview.json` | `/pcap/{key}/packets`                        | Packet capture overview |

## Key Features

1. **Zero Configuration for Mock Mode**: Just run `pytest` - mocks are enabled by default
2. **Intelligent Patching**: Patches the CMLClient before server initialization
3. **Realistic Responses**: Uses actual API responses captured from CML server
4. **Resource Tracking**: Mock tracks created resources and generates unique IDs
5. **Selective Test Execution**: Use pytest markers to run subsets of tests
6. **CI/CD Ready**: Fast, reliable, no external dependencies in mock mode

## Benefits

### For Development

- Fast test feedback loop
- No need for running CML server
- Safe experimentation without affecting real resources
- Consistent test results

### For CI/CD

- No infrastructure dependencies
- Faster pipeline execution
- Lower resource costs
- Reliable, reproducible results

### For Integration Testing

- Option to run against live server
- Full end-to-end validation
- Real API integration testing

## Future Enhancements

Potential improvements for the mock framework:

1. **Enhanced Mock Creation**: Support for creating mock labs/nodes/users in tests
2. **State Persistence**: Keep mock state between test runs
3. **Mock Validation**: Verify mock data matches current API schemas
4. **Auto-Update Mocks**: Script to refresh mock data from live server
5. **Partial Mocking**: Mock only specific endpoints while using live server for others
