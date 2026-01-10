# Quick Reference: Mock Testing Framework

## Quick Start

```bash
# Run tests with mocks (default - fast, no CML server needed)
pytest tests/

# Run tests against live CML server  
USE_MOCKS=false CML_URL=https://cml.example.com CML_USERNAME=admin CML_PASSWORD=pass pytest tests/

# Run only tests that work with mocks
pytest -m "not live_only" tests/

# Run only tests that require live server
USE_MOCKS=false pytest -m live_only tests/
```

## Test Results Summary

- **Mock Mode**: 9 passed, 9 skipped (live_only tests)
- **Live Mode**: All 18 tests run against real server

## Environment Variables

| Variable | Default | Description |
| --- | --- | --- |
| `USE_MOCKS` | `true` | Enable/disable mock mode |
| `CML_URL` | Required for live | URL of CML server |
| `CML_USERNAME` | Required for live | CML username |
| `CML_PASSWORD` | Required for live | CML password |

## Test Markers

- `@pytest.mark.live_only` - Test requires live CML server (creates/modifies resources)
- No marker - Test works with mocks (read-only operations)

## Files

- `tests/conftest.py` - Mock framework implementation
- `tests/mocks/*.json` - Mock API responses  
- `tests/README.md` - Detailed documentation
- `tests/MOCK_FRAMEWORK.md` - Implementation details
