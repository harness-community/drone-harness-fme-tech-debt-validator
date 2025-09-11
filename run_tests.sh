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

# Run different test categories
echo ""
echo "🔍 Running Unit Tests..."
pytest tests/ -m "unit" -v

echo ""
echo "🔗 Running Integration Tests..."
pytest tests/ -m "integration" -v

echo ""
echo "🌳 Running AST Parsing Tests..."
pytest tests/ -m "ast" -v

echo ""
echo "📊 Running All Tests with Coverage..."
pytest tests/ --cov=app --cov-report=html --cov-report=term

echo ""
echo "🐌 Running Slow Tests..."
pytest tests/ -m "slow" -v

echo ""
echo "🏃‍♂️ Running Fast Tests in Parallel..."
pytest tests/ -m "not slow" -n auto

echo ""
echo "✅ All tests completed!"
echo ""
echo "📈 Coverage report generated in htmlcov/index.html"
echo "🔍 View detailed results in the terminal output above"