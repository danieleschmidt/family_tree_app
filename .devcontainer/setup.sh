#!/bin/bash

# Family Tree App Development Container Setup Script
set -e

echo "🚀 Setting up Family Tree App development environment..."

# Update system packages
apt-get update && apt-get upgrade -y

# Install system dependencies
apt-get install -y \
    build-essential \
    libpq-dev \
    postgresql-client \
    git \
    curl \
    wget \
    vim \
    nano \
    htop \
    tree \
    jq

# Install Python development tools
pip install --upgrade pip poetry

# Install project dependencies
echo "📦 Installing Python dependencies..."
cd /workspaces/family_tree_app
poetry config virtualenvs.create false
poetry install

# Install additional requirements
if [ -f "extra_requirements.txt" ]; then
    pip install -r extra_requirements.txt
fi

# Install development and testing dependencies
pip install \
    pytest \
    pytest-django \
    pytest-cov \
    black \
    flake8 \
    isort \
    mypy \
    django-debug-toolbar \
    factory-boy \
    coverage

# Create .env file from template if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
fi

# Set up pre-commit hooks
echo "🔧 Setting up pre-commit hooks..."
pip install pre-commit
pre-commit install

# Make manage.py executable
chmod +x source/manage.py

# Create necessary directories
mkdir -p source/content/media/uploads
mkdir -p source/content/static/collected
mkdir -p logs
mkdir -p backups

# Set up database (if PostgreSQL is available)
echo "🗄️  Database setup will be handled by docker-compose..."

# Install Node.js dependencies for frontend tools
echo "📦 Installing Node.js dependencies..."
npm install -g \
    prettier \
    eslint \
    @tailwindcss/cli

echo "✅ Development environment setup complete!"
echo ""
echo "🎯 Next steps:"
echo "  1. Update .env file with your configuration"
echo "  2. Run: docker-compose up -d (for database services)"
echo "  3. Run: python source/manage.py migrate"
echo "  4. Run: python source/manage.py createsuperuser"
echo "  5. Run: python source/manage.py runserver"
echo ""
echo "🌐 Access the application at: http://localhost:8000"