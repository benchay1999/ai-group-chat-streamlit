# Security Test Suite

Comprehensive security testing for AI Group Chat application before deployment to 100-120 users.

## Test Categories

### 1. Authentication Security (`test_security_auth.py`)
- JWT token security (expiration, tampering, replay)
- MTurk worker registration
- Role-based access control
- Rate limiting
- SQL injection prevention

### 2. Payment Fraud Prevention (`test_security_payments.py`)
- Double payment prevention
- Payment amount manipulation
- Redemption code security
- Gem balance integrity
- Concurrent transaction handling

### 3. Concurrent Sessions (`test_security_concurrency.py`)
- Multiple sessions per user
- Race condition handling
- Session hijacking prevention
- Room capacity enforcement

### 4. Data Privacy (`test_security_data_privacy.py`)
- User data exposure prevention
- Cross-user data access
- API response filtering
- PII protection

### 5. Load Testing (`test_security_load.py`)
- 100-120 concurrent user simulation
- Database connection pool testing
- API performance under load

## Quick Start

```bash
# Install dependencies
pip install -r requirements_test.txt

# Run all tests
./run_security_tests.sh

# Or run individually
pytest test_security_auth.py -v
pytest test_security_payments.py -v
pytest test_security_concurrency.py -v
pytest test_security_data_privacy.py -v
pytest test_security_load.py -v -m slow
```

## Configuration Validation

```bash
# Validate production configuration
python validate_production_config.py --env-file ../.env

# Strict mode (warnings as errors)
python validate_production_config.py --env-file ../.env --strict
```

## Manual Testing

See `MANUAL_PENETRATION_TESTING.md` for detailed manual test procedures.

## Test Results

Results are tracked in `../SECURITY_TEST_RESULTS.md`.

## Files

- `test_security_auth.py` - Authentication tests (10 tests)
- `test_security_payments.py` - Payment tests (10 tests)
- `test_security_concurrency.py` - Concurrency tests (6 tests)
- `test_security_data_privacy.py` - Privacy tests (7 tests)
- `test_security_load.py` - Load tests (4 tests)
- `validate_production_config.py` - Config validator
- `MANUAL_PENETRATION_TESTING.md` - Manual test procedures (36 tests)
- `conftest.py` - Shared pytest fixtures
- `pytest.ini` - Pytest configuration
- `run_security_tests.sh` - Test runner script
- `requirements_test.txt` - Test dependencies

**Total**: 73 test cases (37 automated + 36 manual)

## Coverage

Generate coverage report:
```bash
pytest test_security_*.py --cov=backend --cov-report=html
open htmlcov/index.html
```

## CI/CD Integration

Add to GitHub Actions (example):
```yaml
name: Security Tests
on: [push, pull_request]
jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run security tests
        run: |
          cd backend/tests
          pip install -r requirements_test.txt
          pytest test_security_*.py -v
```

## Support

For issues or questions about security tests, contact the development team.

