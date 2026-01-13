#!/bin/bash
set -e

# Universal Simulation Engine - Docker Entrypoint Script
# This script handles config fallback and starts the application

CONFIG_FILE="/config/factory.yml"
DEFAULT_CONFIG="/app/config/default_config.yml"

# Check if user provided a custom config
if [ -f "$CONFIG_FILE" ]; then
    echo "🏭 Using custom configuration: $CONFIG_FILE"
    CONFIG_TO_USE="$CONFIG_FILE"
else
    echo "📋 No custom config found at $CONFIG_FILE"
    echo "📋 Using default configuration: $DEFAULT_CONFIG"
    CONFIG_TO_USE="$DEFAULT_CONFIG"
fi

# Log startup information
echo "════════════════════════════════════════════════════════════"
echo "🏭 Universal Simulation Engine"
echo "════════════════════════════════════════════════════════════"
echo "📁 Configuration: $CONFIG_TO_USE"
echo "🌐 API Server: http://0.0.0.0:8080"
echo "📊 API Documentation: http://0.0.0.0:8080/docs"
echo "════════════════════════════════════════════════════════════"

# Start the application
exec python -m src.main \
    --config "$CONFIG_TO_USE" \
    --host "0.0.0.0" \
    --port "8080" \
    "$@"