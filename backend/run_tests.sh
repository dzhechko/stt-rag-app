#!/bin/bash

# Test runner script for STT App Backend

set -e

echo "========================================="
echo "STT App Backend Test Runner"
echo "========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if running from backend directory
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}Error: Please run this script from the backend directory${NC}"
    exit 1
fi

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${YELLOW}pytest not found. Installing test dependencies...${NC}"
    pip install -r requirements-test.txt
fi

# Parse command line arguments
TEST_TYPE=""
COVERAGE=false
VERBOSE=false
WATCH=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --unit)
            TEST_TYPE="unit"
            shift
            ;;
        --integration)
            TEST_TYPE="integration"
            shift
            ;;
        --coverage|-c)
            COVERAGE=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --watch|-w)
            WATCH=true
            shift
            ;;
        --help|-h)
            echo "Usage: ./run_tests.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --unit          Run unit tests only"
            echo "  --integration   Run integration tests only"
            echo "  --coverage, -c  Run with coverage report"
            echo "  --verbose, -v   Verbose output"
            echo "  --watch, -w     Watch mode (rerun on file changes)"
            echo "  --help, -h      Show this help message"
            echo ""
            echo "Examples:"
            echo "  ./run_tests.sh                 # Run all tests"
            echo "  ./run_tests.sh --integration   # Run integration tests only"
            echo "  ./run_tests.sh --coverage      # Run with coverage"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help to see available options"
            exit 1
            ;;
    esac
done

# Build pytest command
PYTEST_CMD="pytest"

# Add test type filter
if [ -n "$TEST_TYPE" ]; then
    PYTEST_CMD="$PYTEST_CMD tests/$TEST_TYPE"
else
    PYTEST_CMD="$PYTEST_CMD tests"
fi

# Add coverage if requested
if [ "$COVERAGE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD --cov=app --cov-report=html --cov-report=term"
fi

# Add verbosity if requested
if [ "$VERBOSE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -vv"
else
    PYTEST_CMD="$PYTEST_CMD -v"
fi

# Add watch mode if requested
if [ "$WATCH" = true ]; then
    if ! command -v pytest-watch &> /dev/null; then
        echo -e "${YELLOW}pytest-watch not found. Installing...${NC}"
        pip install pytest-watch
    fi
    echo -e "${GREEN}Running in watch mode...${NC}"
    ptw tests -- -v
    exit 0
fi

# Print command
echo -e "${GREEN}Running: $PYTEST_CMD${NC}"
echo ""

# Run tests
eval $PYTEST_CMD
TEST_EXIT_CODE=$?

echo ""
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}=========================================${NC}"
    echo -e "${GREEN}All tests passed!${NC}"
    echo -e "${GREEN}=========================================${NC}"
    if [ "$COVERAGE" = true ]; then
        echo ""
        echo -e "${YELLOW}Coverage report generated: htmlcov/index.html${NC}"
    fi
else
    echo -e "${RED}=========================================${NC}"
    echo -e "${RED}Some tests failed!${NC}"
    echo -e "${RED}=========================================${NC}"
fi

exit $TEST_EXIT_CODE
