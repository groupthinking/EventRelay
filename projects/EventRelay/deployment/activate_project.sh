#!/bin/bash
# UVAI YouTube Extension - Custom Activation Script

echo "🔄 Activating UVAI YouTube Extension virtual environment..."

# Activate the virtual environment
source .venv/bin/activate

# Run post-activation script
if [ -f ".venv/bin/postactivate" ]; then
    bash .venv/bin/postactivate
fi

echo ""
echo "🎯 Ready to develop! Type 'deactivate' when done."
