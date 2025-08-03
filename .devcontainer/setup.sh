#!/bin/bash

# Family Tree App Development Container Setup Script
# This script sets up the development environment inside the container

set -e

echo "🚀 Setting up Family Tree App development environment..."

# Update package lists
echo "📦 Updating package lists..."
apt-get update

# Install additional system dependencies
echo "🔧 Installing system dependencies..."
apt-get install -y \
    curl \
    wget \
    git \
    build-essential \
    libpq-dev \
    libssl-dev \
    libffi-dev \
    zlib1g-dev \
    libjpeg-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libwebp-dev \
    tcl8.6-dev \
    tk8.6-dev \
    python3-tk \
    gettext \
    redis-tools \
    postgresql-client

# Install Poetry if not already installed
if ! command -v poetry &> /dev/null; then
    echo "📚 Installing Poetry..."
    curl -sSL https://install.python-poetry.org | python3 -
    export PATH="/root/.local/bin:$PATH"
fi

# Configure Poetry
echo "⚙️ Configuring Poetry..."
poetry config virtualenvs.create true
poetry config virtualenvs.in-project false
poetry config virtualenvs.path /opt/poetry/venv

# Install Python dependencies
echo "🐍 Installing Python dependencies..."
cd /workspace
poetry install --no-root

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
fi

# Set up pre-commit hooks
echo "🪝 Setting up pre-commit hooks..."
poetry run pre-commit install

# Install Node.js dependencies if package.json exists
if [ -f package.json ]; then
    echo "📦 Installing Node.js dependencies..."
    npm install
fi

# Run initial database setup
echo "🗄️ Setting up database..."
poetry run python source/manage.py makemigrations --check --dry-run || {
    echo "⚠️ Migrations need to be created. Run 'poetry run python source/manage.py makemigrations' manually."
}

# Create initial superuser if needed (non-interactive)
echo "👤 Setting up initial superuser..."
poetry run python source/manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('✅ Created superuser: admin/admin123')
else:
    print('ℹ️ Superuser already exists')
" || echo "⚠️ Could not create superuser automatically"

# Collect static files
echo "📁 Collecting static files..."
poetry run python source/manage.py collectstatic --noinput --clear || echo "⚠️ Could not collect static files"

# Set up git configuration
echo "🔧 Setting up git configuration..."
git config --global init.defaultBranch main
git config --global pull.rebase false
git config --global user.name "DevContainer User" || true
git config --global user.email "devcontainer@example.com" || true

# Create helpful aliases
echo "⚡ Setting up helpful aliases..."
echo 'alias runserver="poetry run python source/manage.py runserver 0.0.0.0:8000"' >> ~/.bashrc
echo 'alias shell="poetry run python source/manage.py shell"' >> ~/.bashrc
echo 'alias migrate="poetry run python source/manage.py migrate"' >> ~/.bashrc
echo 'alias makemigrations="poetry run python source/manage.py makemigrations"' >> ~/.bashrc
echo 'alias test="poetry run pytest"' >> ~/.bashrc
echo 'alias lint="poetry run flake8 source"' >> ~/.bashrc
echo 'alias format="poetry run black source && poetry run isort source"' >> ~/.bashrc
echo 'alias typecheck="poetry run mypy source"' >> ~/.bashrc

# Create workspace directories
echo "📁 Creating workspace directories..."
mkdir -p /workspace/logs
mkdir -p /workspace/media
mkdir -p /workspace/static
mkdir -p /workspace/tmp

# Set permissions
echo "🔐 Setting permissions..."
chmod -R 755 /workspace
chown -R vscode:vscode /workspace || true

# Display helpful information
echo ""
echo "✅ Development environment setup complete!"
echo ""
echo "🎯 Quick start commands:"
echo "  runserver       - Start Django development server"
echo "  shell          - Open Django shell"
echo "  migrate        - Run database migrations"
echo "  makemigrations - Create new migrations"
echo "  test           - Run test suite"
echo "  lint           - Check code style"
echo "  format         - Format code with Black and isort"
echo "  typecheck      - Run type checking with mypy"
echo ""
echo "🌐 Access points:"
echo "  Django app: http://localhost:8000"
echo "  Admin panel: http://localhost:8000/admin (admin/admin123)"
echo ""
echo "📚 Documentation:"
echo "  Project docs: /workspace/docs/"
echo "  API docs: /workspace/docs/guides/api.md"
echo ""
echo "Happy coding! 🚀"