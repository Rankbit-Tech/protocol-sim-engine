#!/bin/bash
# Universal Simulation Engine - Complete Test Suite Runner

set -e  # Exit on any error

echo "🧪 Universal Simulation Engine - Test Suite"
echo "=========================================="
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track results
UNIT_TESTS_PASSED=false
TOTAL_FAILURES=0

echo "📦 Step 1: Unit Tests"
echo "----------------------------------------"
if python -m pytest tests/unit/ -v --tb=short; then
    echo -e "${GREEN}✅ Unit tests passed${NC}"
    UNIT_TESTS_PASSED=true
else
    echo -e "${RED}❌ Unit tests failed${NC}"
    TOTAL_FAILURES=$((TOTAL_FAILURES + 1))
fi
echo ""

echo "=========================================="
echo "📊 Test Summary"
echo "=========================================="

if [ "$UNIT_TESTS_PASSED" = true ]; then
    echo -e "${GREEN}✅ Unit Tests: PASSED${NC}"
else
    echo -e "${RED}❌ Unit Tests: FAILED${NC}"
fi

echo ""
echo "----------------------------------------"

if [ $TOTAL_FAILURES -eq 0 ]; then
    echo -e "${GREEN}🎉 All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ $TOTAL_FAILURES test suite(s) failed${NC}"
    exit 1
fi