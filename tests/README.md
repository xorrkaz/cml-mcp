# CML MCP Tests

This directory contains tests for the CML MCP server. Tests can run in two modes: **mock mode** (using pre-recorded API responses) or **live mode** (against a real CML server).

## Test Modes

### Mock Mode (Default)

Mock mode uses pre-recorded API responses stored in the `mocks/` directory. This is the default mode and doesn't require a CML server.

**Advantages:**

- Fast execution
- No external dependencies
- Consistent, repeatable results
- Safe - doesn't modify any real resources

**Limitations:**

- Only tests data parsing and basic flow
- Doesn't test actual API integration
- Can't test resource creation/modification

**Usage:**

```bash
# Run all tests in mock mode (default)
pytest tests/

# Explicitly set mock mode
USE_MOCKS=true pytest tests/

# Run only tests that work with mocks
pytest -m "not live_only" tests/
```

### Live Mode

Live mode runs tests against a real CML server. This provides full integration testing but requires proper credentials and will create/delete resources on the server.

**Advantages:**

- Full end-to-end testing
- Tests actual API integration
- Validates real server responses

**Requirements:**

- Running CML server
- Valid credentials (CML_URL, CML_USERNAME, CML_PASSWORD environment variables)
- Sufficient permissions to create/delete labs, users, and groups

**Usage:**

```bash
# Run against live server
USE_MOCKS=false pytest tests/

# Run only tests marked as live_only
USE_MOCKS=false pytest -m live_only tests/
```

## Environment Variables

### Mock Mode

- `USE_MOCKS=true` (default) - Enable mock mode

### Live Mode Configuration

- `USE_MOCKS=false` - Disable mocks, use live server
- `CML_URL` - URL of your CML server (e.g., `https://cml-server.example.com`)
- `CML_USERNAME` - CML username
- `CML_PASSWORD` - CML password

Example:

```bash
export USE_MOCKS=false
export CML_URL=https://192.168.1.100
export CML_USERNAME=admin
export CML_PASSWORD=admin123
pytest tests/
```

## Test Markers

Tests are marked with the following pytest markers:

- `@pytest.mark.live_only` - Test requires a live CML server (creates/modifies resources)
- `@pytest.mark.mock_only` - Test only works with mocks

Use markers to selectively run tests:

```bash
# Run only read-only tests (safe for mock mode)
pytest -m "not live_only" tests/

# Run only tests that modify resources (requires live server)
USE_MOCKS=false pytest -m live_only tests/

# Run specific test
pytest tests/test_cml_mcp.py::test_get_cml_labs
```

## Mock Data

Mock data is stored in `tests/mocks/` as JSON files. Each file corresponds to a specific API endpoint:

- `get_labs.json` - List of labs
- `get_users.json` - List of users
- `get_groups.json` - List of groups
- `get_cml_info.json` - System information
- `get_cml_status.json` - System health status
- `get_cml_statistics.json` - System statistics
- `get_node_defs.json` - Available node definitions
- `get_node_def_detail.json` - Detailed node definition
- `get_nodes_for_cml_lab.json` - Nodes in a lab
- `get_interfaces_for_node.json` - Interfaces for a node
- `get_all_links_for_lab.json` - Links in a lab
- `get_cml_lab_by_title.json` - Lab details by title
- `get_cml_licensing_details.json` - Licensing information

### Updating Mock Data

To update mock data with fresh responses from a CML server:

1. Uncomment the `outsource()` calls in the test file
2. Run tests against a live server with `USE_MOCKS=false`
3. The `inline-snapshot` library will save API responses
4. Move the generated files from `.inline-snapshot/external/` to `tests/mocks/`
5. Rename files to match the naming convention

Example:

```bash
# Run test to capture API response
USE_MOCKS=false pytest tests/test_cml_mcp.py::test_get_cml_labs -v

# Move and rename the generated file
mv .inline-snapshot/external/<hash>.json tests/mocks/get_labs.json
```

## Test Coverage

### Read-Only Tests (Work with Mocks)

- `test_list_tools` - Verify available MCP tools
- `test_get_cml_labs` - List all labs
- `test_get_cml_users` - List all users
- `test_get_cml_groups` - List all groups
- `test_get_cml_information` - Get system info
- `test_get_cml_status` - Get system health
- `test_get_cml_statistics` - Get system stats
- `test_get_cml_licensing_details` - Get licensing info
- `test_node_defs` - List and get node definitions

### State-Modifying Tests (Require Live Server)

- `test_user_mgmt` - Create and delete users
- `test_group_mgmt` - Create and delete groups
- `test_empty_lab_mgmt` - Create and delete labs
- `test_modify_cml_lab` - Modify lab properties
- `test_full_cml_topology` - Create lab from topology file
- `test_intf_management` - Add interfaces to nodes
- `test_add_annotation_to_cml_lab` - Add annotations to labs
- `test_connect_two_nodes` - Create links between nodes
- `test_get_nodes_for_cml_lab` - Get nodes (creates test lab first)

## Continuous Integration

For CI/CD pipelines, use mock mode by default:

```yaml
# GitHub Actions example
- name: Run tests
  run: pytest tests/
  env:
    USE_MOCKS: "true"
```

Optionally, run live tests in a separate job if you have a test CML server available:

```yaml
- name: Run integration tests
  run: pytest tests/
  env:
    USE_MOCKS: "false"
    CML_URL: ${{ secrets.CML_URL }}
    CML_USERNAME: ${{ secrets.CML_USERNAME }}
    CML_PASSWORD: ${{ secrets.CML_PASSWORD }}
```

## Troubleshooting

### Mock Mode Issues

**Problem:** Tests fail with "File not found" errors

- **Solution:** Ensure all mock JSON files are present in `tests/mocks/`

**Problem:** Tests fail with schema validation errors

- **Solution:** Mock data may be outdated. Update mock files with fresh API responses

### Live Mode Issues

**Problem:** Authentication failures

- **Solution:** Verify CML_URL, CML_USERNAME, and CML_PASSWORD are set correctly

**Problem:** Permission denied errors

- **Solution:** Ensure the CML user has admin privileges or appropriate permissions

**Problem:** Tests create resources but don't clean up

- **Solution:** Tests include cleanup code. If a test fails, manually delete created resources or re-run the test

## Contributing

When adding new tests:

1. Mark tests appropriately with `@pytest.mark.live_only` if they modify resources
2. Provide corresponding mock data in `tests/mocks/` for read-only operations
3. Update this README if new mock files are added
4. Ensure tests clean up created resources (use try/finally or pytest fixtures)
5. Run tests in both mock and live modes before submitting
