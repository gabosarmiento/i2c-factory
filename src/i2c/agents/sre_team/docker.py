from pathlib import Path
from typing import Dict, Any, List
import json

from agno.agent import Agent

class DockerConfigAgent(Agent):
    """Generates Docker configurations based on architectural intelligence"""
    
    def __init__(self, project_path=None, **kwargs):  # Add project_path parameter
        self.project_path = Path(project_path) if project_path else Path(".")
        super().__init__(
            name="DockerConfig",
            model=None,  # No LLM calls needed
            description="Generates Docker configurations for deployment",
            **kwargs
        )
    
    def generate_docker_configs(self, project_path: Path, architectural_context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate Dockerfile and docker-compose.yml based on architectural context"""
        
        system_type = architectural_context.get("system_type", "unknown")
        modules = architectural_context.get("modules", {})
        
        configs_created = []
        
        # Generate backend Dockerfile
        if "backend" in modules or system_type == "fullstack_web_app":
            backend_dockerfile = self._generate_backend_dockerfile(project_path, modules.get("backend", {}))
            backend_docker_path = project_path / "backend" / "Dockerfile"
            backend_docker_path.write_text(backend_dockerfile)
            configs_created.append("backend/Dockerfile")
        
        # Generate frontend Dockerfile
        if "frontend" in modules or system_type == "fullstack_web_app":
            frontend_dockerfile = self._generate_frontend_dockerfile(project_path, modules.get("frontend", {}))
            frontend_docker_path = project_path / "frontend" / "Dockerfile"
            frontend_docker_path.write_text(frontend_dockerfile)
            configs_created.append("frontend/Dockerfile")
        
        # Generate docker-compose.yml
        if system_type == "fullstack_web_app":
            compose_content = self._generate_docker_compose(project_path, modules, system_type)
            compose_path = project_path / "docker-compose.yml"
            compose_path.write_text(compose_content)
            configs_created.append("docker-compose.yml")
        
        # Generate .dockerignore
        dockerignore_content = self._generate_dockerignore()
        dockerignore_path = project_path / ".dockerignore"
        dockerignore_path.write_text(dockerignore_content)
        configs_created.append(".dockerignore")
        
        return {
            "configs_created": configs_created,
            "system_type": system_type
        }
    
    def _generate_backend_dockerfile(self, project_path: Path, backend_module: Dict[str, Any]) -> str:
        """Generate FastAPI backend Dockerfile"""
        
        languages = backend_module.get("languages", ["python"])
        
        if "python" in languages:
            return """# FastAPI Backend Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \\
    && chown -R app:app /app
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
"""
        
        return "# Unsupported backend language\\n"
    
    def _generate_frontend_dockerfile(self, project_path: Path, frontend_module: Dict[str, Any]) -> str:
        """Generate React frontend Dockerfile with multi-stage build"""
        
        languages = frontend_module.get("languages", ["javascript"])
        
        if any(lang in languages for lang in ["javascript", "typescript"]):
            return """# React Frontend Dockerfile - Multi-stage build
FROM node:18-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built assets to nginx
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost/health || exit 1

CMD ["nginx", "-g", "daemon off;"]
"""
        
        return "# Unsupported frontend language\\n"
    
    def _generate_docker_compose(self, project_path: Path, modules: Dict[str, Any], system_type: str) -> str:
        """Generate docker-compose.yml for fullstack application"""
        
        has_backend = "backend" in modules
        has_frontend = "frontend" in modules
        
        compose_content = """version: '3.8'

services:"""
        
        if has_backend:
            compose_content += """
  backend:
    build: 
      context: ./backend
      dockerfile: Dockerfile
    container_name: snippet-backend
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=development
      - DATABASE_URL=postgresql://user:password@db:5432/snippetdb
      - CORS_ORIGINS=http://localhost:3000
    depends_on:
      - db
    volumes:
      - ./backend:/app
    networks:
      - snippet-network
    restart: unless-stopped"""
        
        if has_frontend:
            compose_content += """
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: snippet-frontend
    ports:
      - "3000:80"
    environment:
      - REACT_APP_API_URL=http://localhost:8000
    depends_on:
      - backend
    networks:
      - snippet-network
    restart: unless-stopped"""
        
        # Add database service for fullstack apps
        if system_type == "fullstack_web_app":
            compose_content += """
  db:
    image: postgres:15-alpine
    container_name: snippet-db
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=snippetdb
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - snippet-network
    restart: unless-stopped"""
        
        compose_content += """

networks:
  snippet-network:
    driver: bridge

volumes:
  postgres_data:
    driver: local
"""
        
        return compose_content
    
    def _generate_dockerignore(self) -> str:
        """Generate .dockerignore file"""
        
        return """# Dependencies
node_modules/
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
pip-log.txt

# IDEs
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Git
.git/
.gitignore

# Logs
*.log
logs/

# Runtime
*.pid
*.seed
*.pid.lock

# Coverage
coverage/
.nyc_output/
.coverage

# Build outputs
dist/
build/
*.egg-info/

# Environment
.env
.env.local
.env.*.local

# Docker
Dockerfile
docker-compose*.yml
.dockerignore
"""

# For convenience imports
docker_config = DockerConfigAgent(project_path=Path("."))

# For flexible creation elsewhere
def build_docker_config_agent(project_path=None) -> DockerConfigAgent:
    return DockerConfigAgent(project_path=Path(project_path or "."))