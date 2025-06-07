#!/bin/bash

# Setup script for Network Tester
echo "🔧 Setting up Network Tester environment..."

# Check if conda is available
if ! command -v conda &> /dev/null; then
    echo "❌ Conda is not installed or not in PATH"
    echo "Please install Miniconda or Anaconda first:"
    echo "https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi

# Remove existing environment if it exists
echo "🗑️ Removing existing environment (if any)..."
conda env remove --name network-tester -y 2>/dev/null || true

# Create new environment
echo "🏗️ Creating new Conda environment..."
conda env create -f environment.yml

echo "✅ Environment created successfully!"
echo ""
echo "To use the Network Tester:"
echo "1. Activate the environment: conda activate network-tester"
echo "2. Run the tool: python request_flooder.py"
echo ""
echo "To deactivate when done: conda deactivate"