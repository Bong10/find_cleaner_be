# Deployment Guide for IONOS VPS

This guide will help you deploy the Tidy Linker backend to an IONOS VPS using Docker and Docker Compose.

## Prerequisites

1.  **IONOS VPS**: A Linux server (Ubuntu 20.04 or 22.04 recommended).
2.  **SSH Access**: You should be able to log in to your server via SSH.
    ```bash
    ssh root@YOUR_SERVER_IP
    ```
3.  **Domain Name** (Optional): A domain pointing to your server's IP address.

## Step 1: Prepare the Server

Log in to your server and update the system:

```bash
apt-get update && apt-get upgrade -y
```

### Install Docker and Docker Compose

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose (if not included in Docker installation)
apt-get install -y docker-compose-plugin
```

Verify installation:
```bash
docker --version
docker compose version
```

## Step 2: Transfer Project Files

You can transfer your files using `git` (recommended) or `scp`.

### Option A: Using Git (Recommended)
1.  Push your code to a repository (GitHub/GitLab).
2.  Clone it on the server:
    ```bash
    git clone https://github.com/yourusername/tidy-linker.git
    cd tidy-linker
    ```

### Option B: Using SCP (Copy from local machine)
Run this command from your local machine (not the server):
```bash
scp -r "path/to/your/project" root@YOUR_SERVER_IP:/root/tidy-linker
```

## Step 3: Configure Environment Variables

Create a `.env` file in the project root on the server:

```bash
cd /root/tidy-linker  # or wherever you put the project
nano .env
```

Paste your production configuration. Make sure to change `DEBUG` to `False` and set a strong `SECRET_KEY`.

```env
# Django Settings
DEBUG=False
SECRET_KEY=your-super-secret-key-change-this
ALLOWED_HOSTS=YOUR_SERVER_IP,yourdomain.com

# Database Settings
DB_ENGINE=django.db.backends.postgresql
DB_NAME=tidy_linker_db
DB_USER=tidy_linker_user
DB_PASSWORD=secure_db_password
DB_HOST=db
DB_PORT=5432

# Redis Settings
REDIS_HOST=redis
REDIS_PORT=6379
```

Save and exit (`Ctrl+O`, `Enter`, `Ctrl+X`).

## Step 4: Deploy

Build and start the containers:

```bash
docker compose up -d --build
```

This command will:
1.  Build the Django image.
2.  Start the Database, Redis, Worker, Web, and Nginx containers.
3.  Run migrations and collect static files (handled by `entrypoint.sh`).

## Step 5: Verify Deployment

Check if all containers are running:

```bash
docker compose ps
```

You should see `web`, `worker`, `redis`, `db`, and `nginx` with status `Up`.

Visit `http://YOUR_SERVER_IP` in your browser. You should see your application running.

## Step 6: Create Superuser

To access the Django admin, create a superuser inside the running container:

```bash
docker compose exec web python manage.py createsuperuser
```

## Troubleshooting

-   **View Logs**:
    ```bash
    docker compose logs -f web
    docker compose logs -f nginx
    ```
-   **Restart Services**:
    ```bash
    docker compose restart
    ```
-   **Rebuild after changes**:
    ```bash
    docker compose up -d --build
    ```
