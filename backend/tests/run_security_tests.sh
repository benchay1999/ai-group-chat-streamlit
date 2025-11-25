#!/bin/bash
# Security Test Suite Runner
# Runs all security tests and generates comprehensive report

set -e  # Exit on error

echo "🔒 AI Group Chat Security Test Suite"
echo "======================================"
echo ""

# Check if backend is running
echo "🔍 Checking if backend is running on port 8001..."
if curl -s http://localhost:8001/api/health > /dev/null 2>&1; then
    echo "✅ Backend is running"
else
    echo "⚠️  Backend not detected on port 8001"
    echo "   Please start backend first:"
    echo "   cd backend && uvicorn main:app --reload --port 8001"
    echo ""
    echo "Continue with unit tests only? (y/n)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""
echo "📋 Running Configuration Validation..."
echo "======================================"
python validate_production_config.py --env-file ../.env

echo ""
echo "🧪 Running Security Test Suite..."
echo "======================================"

# Run authentication tests
echo ""
echo "1️⃣  Authentication Security Tests..."
pytest test_security_auth.py -v --tb=short

# Run payment tests
echo ""
echo "2️⃣  Payment Fraud Prevention Tests..."
pytest test_security_payments.py -v --tb=short

# Run concurrency tests
echo ""
echo "3️⃣  Concurrent Session Security Tests..."
pytest test_security_concurrency.py -v --tb=short

# Run data privacy tests
echo ""
echo "4️⃣  Data Privacy & Leakage Tests..."
pytest test_security_data_privacy.py -v --tb=short

# Run load tests (optional - takes longer)
echo ""
echo "5️⃣  Load & Stress Tests (100-120 users)..."
echo "   Run load tests? (y/n)"
read -r run_load
if [[ "$run_load" =~ ^[Yy]$ ]]; then
    pytest test_security_load.py -v --tb=short -m slow
else
    echo "   Skipping load tests (run manually with: pytest test_security_load.py -v -m slow)"
fi

echo ""
echo "📊 Generating Coverage Report..."
echo "======================================"
pytest test_security_*.py --cov=backend --cov-report=html --cov-report=term

echo ""
echo "✅ Security Test Suite Complete!"
echo "======================================"
echo ""
echo "📁 Reports generated:"
echo "   - HTML Coverage: htmlcov/index.html"
echo "   - Manual tests: MANUAL_PENETRATION_TESTING.md"
echo ""
echo "Next steps:"
echo "1. Review test results above"
echo "2. Run manual penetration tests from MANUAL_PENETRATION_TESTING.md"
echo "3. Fix any failing tests"
echo "4. Document findings in SECURITY_TEST_RESULTS.md"

