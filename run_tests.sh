#!/bin/bash

# Test runner script for Feature Flag CI Plugin

set -e

echo "🧪 Running Feature Flag CI Plugin Test Suite"
echo "============================================"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python -m venv .venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source .venv/bin/activate

# Install test dependencies
echo "📋 Installing test dependencies..."
pip install -r requirements-test.txt

# Set Python path for app imports
export PYTHONPATH=app

# Run all tests with coverage
echo ""
echo "🧪 Running All Tests with Coverage..."
pytest tests/ -v --cov=app --cov-report=html --cov-report=term

echo ""
echo "🔍 Running linter..."
flake8 . --max-line-length=150 --extend-ignore=W293,W291,E203

echo ""
echo "✅ All tests completed!"
echo ""
echo "📈 Coverage report generated in htmlcov/index.html"
echo "🔍 View detailed results in the terminal output above"