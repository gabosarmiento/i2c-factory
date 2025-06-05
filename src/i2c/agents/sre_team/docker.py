from pathlib import Path
from typing import Dict, Any, List
import json
import time

class DockerConfigAgent:
    """Generates Docker configurations based on architectural intelligence"""
    
    def __init__(self, project_path=None, **kwargs):  # Add project_path parameter
        self.project_path = Path(project_path) if project_path else Path(".")
        self.name = "DockerConfig"
    
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
        
        # Generate frontend Dockerfile and nginx config
        if "frontend" in modules or system_type == "fullstack_web_app":
            frontend_dockerfile = self._generate_frontend_dockerfile(project_path, modules.get("frontend", {}))
            frontend_docker_path = project_path / "frontend" / "Dockerfile"
            frontend_docker_path.write_text(frontend_dockerfile)
            configs_created.append("frontend/Dockerfile")
            
            # Generate nginx.conf for frontend
            nginx_config = self._generate_nginx_config()
            nginx_config_path = project_path / "frontend" / "nginx.conf"
            nginx_config_path.write_text(nginx_config)
            configs_created.append("frontend/nginx.conf")
        
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
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install security scanning tools
RUN pip install --no-cache-dir pip-audit

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

# Install all dependencies (including dev deps for build)
RUN npm install

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
        
        compose_content = """services:"""
        
        if has_backend:
            # Use timestamp to avoid container name conflicts
            timestamp = int(time.time())
            compose_content += f"""
  backend:
    build: 
      context: ./backend
      dockerfile: Dockerfile
    container_name: snippet-backend-{timestamp}
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
            # Use timestamp to avoid container name conflicts  
            timestamp = int(time.time())
            compose_content += f"""
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: snippet-frontend-{timestamp}
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
            # Use timestamp to avoid container name conflicts
            timestamp = int(time.time())
            compose_content += f"""
  db:
    image: postgres:15-alpine
    container_name: snippet-db-{timestamp}
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=snippetdb
    ports:
      - "0:5432"  # Use dynamic port allocation to avoid conflicts
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
    
    async def run(self) -> Dict[str, Any]:
        """
        AGNO-compatible async run method for SRE team integration.
        Generates Docker configurations and returns results.
        """
        try:
            # Analyze project architecture
            architectural_context = self._analyze_project_architecture()
            
            # Generate Docker configurations
            result = self.generate_docker_configs(self.project_path, architectural_context)
            
            return {
                "passed": True,
                "files_created": result.get("configs_created", []),
                "issues": [],
                "system_type": result.get("system_type", "unknown")
            }
        except Exception as e:
            return {
                "passed": False,
                "files_created": [],
                "issues": [f"Docker config generation failed: {str(e)}"],
                "system_type": "unknown"
            }
    
    def _analyze_project_architecture(self) -> Dict[str, Any]:
        """Analyze project structure to determine architecture"""
        
        # Check for frontend files
        frontend_files = list(self.project_path.rglob("*.jsx")) + list(self.project_path.rglob("*.js")) + list(self.project_path.rglob("*.ts")) + list(self.project_path.rglob("*.tsx"))
        has_frontend = bool(frontend_files) or (self.project_path / "frontend").exists()
        
        # Check for backend files  
        backend_files = list(self.project_path.rglob("*.py"))
        has_backend = bool(backend_files) or (self.project_path / "backend").exists()
        
        # Determine system type
        if has_frontend and has_backend:
            system_type = "fullstack_web_app"
        elif has_frontend:
            system_type = "frontend_app"
        elif has_backend:
            system_type = "backend_app"
        else:
            system_type = "unknown"
        
        # Build modules
        modules = {}
        if has_backend:
            modules["backend"] = {
                "languages": ["python"],
                "responsibilities": ["API endpoints", "business logic"]
            }
        
        if has_frontend:
            modules["frontend"] = {
                "languages": ["javascript", "typescript"],
                "responsibilities": ["user interface", "client-side logic"]
            }
        
        return {
            "system_type": system_type,
            "modules": modules,
            "project_structure": {
                "has_frontend": has_frontend,
                "has_backend": has_backend
            }
        }
    
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
    
    def _generate_nginx_config(self) -> str:
        """Generate nginx.conf for frontend serving"""
        return """server {
    listen 80;
    server_name localhost;
    
    # Serve static files
    location / {
        root /usr/share/nginx/html;
        index index.html index.htm;
        try_files $uri $uri/ /index.html;
    }
    
    # API proxy to backend
    location /api/ {
        proxy_pass http://backend:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }
    
    # Health check endpoint
    location /health {
        access_log off;
        return 200 "OK";
        add_header Content-Type text/plain;
    }
    
    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied expired no-cache no-store private auth;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/x-javascript
        application/xml+rss
        application/javascript
        application/json;
        
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
}"""

# For convenience imports
docker_config = DockerConfigAgent(project_path=Path("."))

# For flexible creation elsewhere
def build_docker_config_agent(project_path=None) -> DockerConfigAgent:
    return DockerConfigAgent(project_path=Path(project_path or "."))