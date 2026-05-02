# Quick Reference: Mock Testing Framework

## Quick Start

```bash
# Run tests with mocks (default - fast, no CML server needed)
just test

# Run tests against live CML server (reads CML_URL/USERNAME/PASSWORD from .env)
just test-live

# Pass extra pytest args
just test "-k packet -x"
just test-live "-k packet"
```

Direct `pytest` invocation also works (skip the `just` wrapper):

```bash
pytest tests/                                        # mock mode (default)
USE_MOCKS=false pytest tests/                        # live mode
pytest -m "not live_only" tests/                     # only mock-compatible
USE_MOCKS=false pytest -m live_only tests/           # only live-only
```

## Test Results Summary

- **Mock mode**: 14 passed, 11 skipped (live_only tests)
- **Live mode**: 25 tests run against a real CML 2.9+ server

## Environment Variables

| Variable | Default | Description |
| --- | --- | --- |
| `USE_MOCKS` | `true` | Enable/disable mock mode |
| `CML_URL` | Required for live | URL of CML server |
| `CML_USERNAME` | Required for live | CML username |
| `CML_PASSWORD` | Required for live | CML password |
| `CML_VERIFY_SSL` | `true` | Set `false` for self-signed certs |

## Test Markers

- `@pytest.mark.live_only` - Test requires live CML server (creates/modifies resources)
- `@pytest.mark.mock_only` - Test only works with mocks (not valid against a live server)
- No marker - Test works in both modes

## Files

- `tests/conftest.py` - Mock framework + fixtures
- `tests/test_cml_mcp.py` - Main test suite
- `tests/test_schema_drift.py` - Catches CML schema drift in flattened tools
- `tests/mocks/*.json` - Mock API responses
- `tests/README.md` - Detailed documentation
- `tests/MOCK_FRAMEWORK.md` - Implementation details
