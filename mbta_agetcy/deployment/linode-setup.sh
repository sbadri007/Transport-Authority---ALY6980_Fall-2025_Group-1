#!/bin/bash

# Linode Multi-Server Deployment Script
set -e

echo "🌐 MBTA-Corto Linode Deployment"

# Configuration
LINODE_SERVERS=(
    "main-server.linode.com"  # Main orchestration server
    # Add your other MBTA agent servers here
)

DEPLOY_USER="deploy"
DEPLOY_PATH="/opt/mbta-corto"

# Function to deploy to a server
deploy_to_server() {
    local server=$1
    
    echo "📦 Deploying to $server..."
    
    # Create deployment directory
    ssh ${DEPLOY_USER}@${server} "mkdir -p ${DEPLOY_PATH}"
    
    # Copy files
    rsync -avz --exclude='.git' --exclude='__pycache__' \
        ./ ${DEPLOY_USER}@${server}:${DEPLOY_PATH}/
    
    # Install dependencies and start services
    ssh ${DEPLOY_USER}@${server} << 'ENDSSH'
cd ${DEPLOY_PATH}

# Install Docker if not present
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker ${USER}
fi

# Install Docker Compose
if ! command -v docker-compose &> /dev/null; then
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
fi

# Deploy
./deployment/deploy.sh
ENDSSH
    
    echo "✅ Deployment to $server complete"
}

# Deploy to all servers
for server in "${LINODE_SERVERS[@]}"; do
    deploy_to_server "$server"
done

echo ""
echo "🎉 All deployments complete!"