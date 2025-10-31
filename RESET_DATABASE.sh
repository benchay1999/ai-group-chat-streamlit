#!/bin/bash
# Quick Database Reset Script
# Clears all transactional data while preserving user accounts

echo "🔧 Database Reset - Quick Start"
echo "================================"
echo ""
echo "This will:"
echo "  ❌ Delete all game sessions"
echo "  ❌ Delete all transactions"
echo "  🔄 Reset user gem balances to 0"
echo "  ✅ Keep user accounts intact"
echo ""
echo "For full details, see: DATABASE_RESET_GUIDE.md"
echo ""

cd "$(dirname "$0")/backend"

# Check if conda is available
if ! command -v conda &> /dev/null; then
    echo "❌ Error: conda not found. Please install Anaconda or Miniconda."
    exit 1
fi

# Activate conda environment
echo "🔄 Activating conda environment..."
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate group-chat

if [ $? -ne 0 ]; then
    echo "❌ Error: Could not activate group-chat environment."
    echo "   Run: conda create -n group-chat python=3.10"
    exit 1
fi

# Run the reset script
echo ""
python reset_transactional_data.py

# Deactivate conda
conda deactivate

echo ""
echo "✅ Done! You can now restart the backend server."

