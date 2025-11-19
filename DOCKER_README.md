# Dispatch Manager - Docker Deployment Guide

This guide explains how to deploy the Dispatch Manager application using Docker on Ubuntu 24.04 LTS.

## Architecture

The Docker setup consists of:

- **App Container**: Flask + SocketIO application with Gunicorn + eventlet
- **Nginx Container**: Reverse proxy with WebSocket support for SocketIO
- **Data Volumes**: Persistent storage for SQLite database and uploaded files

## Quick Deployment (Ubuntu 24.04 LTS)

### Prerequisites

- Ubuntu 24.04 LTS server
- Root or sudo access
- Internet connection

### Automated Deployment

1. **Clone or copy the application files to your server:**

   ```bash
   # If using git
   git clone <repository-url> /tmp/dispatch-manager
   cd /tmp/dispatch-manager/DispatchManagerV1.3
   
   # Or copy files manually to /tmp/dispatch-manager
   ```

2. **Make the deployment script executable:**

   ```bash
   chmod +x deploy.sh
   ```

3. **Run the automated deployment:**

   ```bash
   sudo ./deploy.sh
   ```

The script will:

- Install Docker and Docker Compose
- Configure firewall (UFW)
- Create necessary directories
- Generate SSL certificates (self-signed for initial setup)
- Deploy the application
- Set up automatic backups
- Create systemd service for management

### Manual Deployment

If you prefer manual deployment:

1. **Install Docker:**

   ```bash
   # Update package index
   sudo apt-get update
   
   # Install Docker
   sudo apt-get install -y docker.io docker-compose-plugin
   
   # Start and enable Docker
   sudo systemctl start docker
   sudo systemctl enable docker
   
   # Add your user to docker group
   sudo usermod -aG docker $USER
   ```

2. **Configure firewall:**

   ```bash
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw allow ssh
   sudo ufw --force enable
   ```

3. **Deploy the application:**

   ```bash
   # Copy application files
   sudo mkdir -p /opt/dispatch-manager
   sudo cp -r . /opt/dispatch-manager/
   
   # Create environment file
   sudo tee /opt/dispatch-manager/.env > /dev/null <<EOF
   SECRET_KEY=$(openssl rand -hex 32)
   FLASK_ENV=production
   EOF
   
   # Create SSL directory and generate self-signed certificate
   sudo mkdir -p /opt/dispatch-manager/ssl
   sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
       -keyout /opt/dispatch-manager/ssl/key.pem \
       -out /opt/dispatch-manager/ssl/cert.pem \
       -subj "/C=FR/ST=State/L=City/O=Organization/CN=localhost"
   
   # Build and start containers
   cd /opt/dispatch-manager
   sudo docker compose build
   sudo docker compose up -d
   ```

## Configuration

### Environment Variables

Create a `.env` file in the application directory:

```bash
SECRET_KEY=your-secure-secret-key-here
FLASK_ENV=production
```

### SSL Certificates

For production, replace the self-signed certificates with proper ones:

1. Obtain SSL certificates (Let's Encrypt recommended)
2. Place them in `/opt/dispatch-manager/ssl/`:
   - Certificate: `cert.pem`
   - Private key: `key.pem`
3. Uncomment and configure HTTPS section in `nginx.conf`
4. Restart containers: `docker compose restart`

### Domain Configuration

Edit `nginx.conf` to use your domain:

```nginx
server {
    listen 80;
    server_name your-domain.com;
    # ... rest of configuration
}
```

## Management

### Systemd Service

The deployment creates a systemd service `dispatch-manager`:

```bash
# Start service
sudo systemctl start dispatch-manager

# Stop service
sudo systemctl stop dispatch-manager

# Restart service
sudo systemctl restart dispatch-manager

# Check status
sudo systemctl status dispatch-manager

# View logs
sudo journalctl -u dispatch-manager -f
```

### Docker Commands

```bash
# View running containers
docker compose ps

# View logs
docker compose logs -f

# Stop all containers
docker compose down

# Start all containers
docker compose up -d

# Rebuild and restart
docker compose build && docker compose up -d

# Execute commands in app container
docker compose exec app bash
```

## Backup and Recovery

### Automatic Backups

The deployment sets up automatic daily backups at 2 AM:
- Database backups stored in `/opt/backups/dispatch-manager/`
- Upload directory backups
- 7-day retention policy

### Manual Backup

```bash
# Run manual backup
/opt/dispatch-manager/backup.sh

# Backup database only
docker exec dispatch_manager_app_app sqlite3 /app/dispatch.db ".backup /tmp/dispatch_backup.db"

# Backup uploads
tar -czf uploads_backup.tar.gz static/uploads/
```

### Recovery

```bash
# Stop application
sudo systemctl stop dispatch-manager

# Restore database
docker cp dispatch_backup.db dispatch_manager_app_app:/app/dispatch.db

# Restore uploads
tar -xzf uploads_backup.tar.gz -C /opt/dispatch-manager/

# Start application
sudo systemctl start dispatch-manager
```

## Monitoring

### Health Checks

The application includes health checks:
- Nginx: `http://localhost/health`
- App container: Docker health check

### Logs

Monitor logs for issues:
```bash
# Application logs
docker compose logs app

# Nginx logs
docker compose logs nginx

# System service logs
sudo journalctl -u dispatch-manager -f
```

## Security Considerations

1. **Change default passwords**: Update any default credentials
2. **Use proper SSL certificates**: Replace self-signed certificates in production
3. **Regular updates**: Keep Docker and containers updated
4. **Firewall configuration**: Ensure only necessary ports are open
5. **Backup security**: Store backups in secure, off-site location
6. **Monitor logs**: Regularly check for suspicious activity

## Troubleshooting

### Common Issues

1. **Containers won't start:**
   ```bash
   # Check logs
   docker compose logs
   
   # Check disk space
   df -h
   
   # Check Docker service
   sudo systemctl status docker
   ```

2. **Application not accessible:**
   ```bash
   # Check if containers are running
   docker compose ps
   
   # Check port conflicts
   sudo netstat -tlnp | grep :80
   
   # Check firewall
   sudo ufw status
   ```

3. **Database issues:**
   ```bash
   # Check database file permissions
   ls -la dispatch.db
   
   # Test database connection
   docker compose exec app sqlite3 /app/dispatch.db ".tables"
   ```

4. **WebSocket/SocketIO issues:**
   - Ensure nginx WebSocket proxy is configured correctly
   - Check if firewall allows WebSocket connections
   - Verify browser console for JavaScript errors

### Performance Optimization

1. **Database optimization:**
   - The SQLite database is already configured with WAL mode
   - Consider regular VACUUM operations for maintenance

2. **Nginx tuning:**
   - Adjust worker connections in nginx.conf
   - Enable additional caching for static files

3. **Container resources:**
   - Monitor container resource usage
   - Adjust memory limits if needed

## Updates

### Application Updates

```bash
cd /opt/dispatch-manager

# Pull latest code (if using git)
git pull

# Rebuild and restart
sudo docker compose build
sudo docker compose up -d
```

### System Updates

```bash
# Update Ubuntu packages
sudo apt update && sudo apt upgrade -y

# Update Docker
sudo apt update && sudo apt install docker.io -y

# Restart services
sudo systemctl restart dispatch-manager
```

## Support

For issues related to:
- **Docker deployment**: Check this guide and Docker documentation
- **Application functionality**: Refer to the main application documentation
- **Ubuntu server**: Consult Ubuntu 24.04 LTS documentation

## File Structure After Deployment

```
/opt/dispatch-manager/
├── app.py                 # Flask application
├── docker-compose.yml     # Docker composition
├── Dockerfile            # Application container definition
├── nginx.conf            # Nginx configuration
├── requirements.txt      # Python dependencies
├── .env                  # Environment variables
├── ssl/                  # SSL certificates
│   ├── cert.pem
│   └── key.pem
├── static/               # Static files
│   └── uploads/          # User uploads (persistent)
├── templates/            # Jinja2 templates
├── dispatch.db           # SQLite database (persistent)
└── backup.sh            # Backup script

/opt/backups/dispatch-manager/  # Backup directory
├── dispatch_YYYYMMDD_HHMMSS.db    # Database backups
└── uploads_YYYYMMDD_HHMMSS.tar.gz # Upload backups
```

This deployment setup provides a production-ready, scalable, and maintainable Docker installation of the Dispatch Manager application.
