#!/bin/bash
# AgentEval Setup Script
# This script sets up the development environment for AgentEval

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "$REPO_ROOT"

echo "🚀 Setting up AgentEval Development Environment..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "📦 Installing uv package manager..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
else
    echo "✅ uv is already installed"
fi

# Check Python version
echo "🐍 Checking Python version..."
if [ -f ".python-version" ]; then
    PYTHON_VERSION=$(cat .python-version)
    echo "Required Python version: $PYTHON_VERSION"
fi

# Create virtual environment
echo "📁 Creating virtual environment..."
if [ ! -d ".venv" ]; then
    uv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
uv pip install -e ".[dev]"

# Copy environment variables template
if [ ! -f ".env" ]; then
    echo "📄 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please update .env with your AWS credentials"
else
    echo "✅ .env file already exists"
fi

# Create necessary directories
echo "📁 Creating project directories..."
mkdir -p src/agenteval/{core,agents,memory,redteam,evaluation,observability,aws,api,cli,utils}
mkdir -p tests/{unit,integration,e2e}
mkdir -p infrastructure/{cloudformation,docker,terraform}
mkdir -p docs examples scripts

# Initialize __init__.py files
echo "📝 Creating __init__.py files..."
find src/agenteval -type d -exec touch {}/__init__.py \;
find tests -type d -exec touch {}/__init__.py \;

# Set up pre-commit hooks
if command -v pre-commit &> /dev/null; then
    echo "🔧 Setting up pre-commit hooks..."
    pre-commit install
fi

# Verify installation
echo "🔍 Verifying installation..."
python --version
python -c "import fastapi; print(f'✅ FastAPI: {fastapi.__version__}')"
python -c "import boto3; print(f'✅ Boto3: {boto3.__version__}')"
python -c "import opentelemetry; print('✅ OpenTelemetry: OK')"

echo ""
echo "✨ Setup complete! Next steps:"
echo ""
echo "1. Update .env with your AWS credentials"
echo "2. Configure AWS CLI: aws configure"
echo "3. Start development server: uvicorn agenteval.main:app --reload"
echo "4. Run tests: pytest tests/ -v"
echo ""
echo "📚 Documentation:"
echo "  - DEVELOPMENT_PLAN.md - Development roadmap"
echo "  - AGENTS.md - Master reference"
echo "  - req-docs/ - Requirements documentation"
echo ""
echo "Happy coding! 🎉"
