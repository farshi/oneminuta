#!/bin/bash
# Install Git hooks for OneMinuta project

echo "🔧 Installing Git hooks for OneMinuta"
echo "====================================="

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    echo "❌ Error: Not in a Git repository"
    echo "Please run this script from the project root"
    exit 1
fi

# Create hooks directory if it doesn't exist
mkdir -p .git/hooks

# Copy hooks and make them executable
echo "Installing pre-commit hook..."
cp .githooks/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit

echo "Installing pre-push hook..."
cp .githooks/pre-push .git/hooks/pre-push
chmod +x .git/hooks/pre-push

# Test that Python and required modules are available
echo ""
echo "Testing hook requirements..."

# Check Python
if ! command -v python &> /dev/null; then
    echo "⚠️  Warning: Python not found in PATH"
    echo "Make sure Python is installed and accessible"
fi

# Check if project dependencies are installed
python -c "import sys, pathlib; sys.path.insert(0, '.'); from tests.chatbot.test_chatbot_structure import test_chatbot_structure" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ Project dependencies available"
else
    echo "⚠️  Warning: Some project dependencies may be missing"
    echo "Run: pip install openai telethon pytest python-dotenv"
fi

# Check .env file
if [ -f ".env" ]; then
    echo "✅ .env file found"
else
    echo "⚠️  Warning: .env file not found"
    echo "Create .env file for optimal testing"
fi

echo ""
echo "✅ Git hooks installed successfully!"
echo ""
echo "What the hooks do:"
echo "=================="
echo ""
echo "📝 pre-commit hook:"
echo "  - Runs quick tests (no API required)"
echo "  - Checks Python syntax"
echo "  - Warns about debug print statements"
echo "  - Blocks hardcoded secrets"
echo ""
echo "🚀 pre-push hook:"
echo "  - Runs comprehensive tests for main branch"
echo "  - Runs quick tests for feature branches"
echo "  - Checks test coverage (if pytest available)"
echo "  - Shows uncommitted changes warning"
echo ""
echo "To bypass hooks (not recommended):"
echo "  git commit --no-verify"
echo "  git push --no-verify"
echo ""
echo "To test hooks:"
echo "  git commit -m 'test commit'"
echo "  git push"

# Test the pre-commit hook
echo ""
echo "Testing pre-commit hook..."
.git/hooks/pre-commit

if [ $? -eq 0 ]; then
    echo "✅ Pre-commit hook test passed!"
else
    echo "❌ Pre-commit hook test failed"
    echo "Please check the errors above"
    exit 1
fi

echo ""
echo "🎉 Setup complete! Your commits and pushes are now protected by tests."