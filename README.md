# Fiocruz Genomics Portal

A comprehensive platform for exploring and analyzing genomic variants, designed for the Fiocruz research community. This portal integrates a high-performance Elasticsearch backend with a modern React frontend to provide fast and intuitive access to genomic data.

## Quick Start (Production/Docker)

The easiest way to run the entire application (Database, Backend, and Frontend) is using Docker. This is recommended for **deployment** or **quick testing** without setting up a local development environment.

### Prerequisites
- [Docker](https://www.docker.com/get-started) installed and running.
- [Git](https://git-scm.com/) to clone the repository.

### Steps
1. **Clone the repository:**
   ```bash
   git clone https://github.com/omatheuspimenta/fiocruz-genomics-portal
   cd fiocruz-genomics-portal
   ```

2. **Start the services:**
   ```bash
   docker-compose up --build -d
   ```
   *The `-d` flag runs the containers in the background.*

3. **Access the application:**
   - Open your browser and go to: `http://localhost:8000`
   - The API documentation is available at: `http://localhost:8000/docs`
   
3. **Access the application:**
   - Open your browser and go to: `http://localhost:8000`
   - The API documentation is available at: `http://localhost:8000/docs`

4. **Stop the services:**
   ```bash
   docker-compose down
   ```

---

## High-Performance Production Deployment

This guide is optimized for high-specification servers (e.g., 64 CPUs, 300GB RAM). The architecture uses **Nginx** as a reverse proxy and static file server, and **Gunicorn** with **Uvicorn workers** for the Python backend.

### Architecture Overview
- **Nginx**: Serves the React frontend (static files) and proxies API requests. Handles Gzip compression and security headers.
- **Backend (API)**: Runs FastAPI using Gunicorn with 64 workers (configurable) to maximize CPU usage.
- **Database**: Elasticsearch 8.11 optimized with 30GB Heap.

### Prerequisites
- **Docker** and **Docker Compose** installed.
- **Git** installed.
- Ports **80** (HTTP) and **9200** (Elasticsearch) available.

### Step-by-Step Deployment

#### 1. System Tuning
Elasticsearch requires increased memory map limits. Run this on the host machine:

```bash
# Apply temporarily
sudo sysctl -w vm.max_map_count=262144

# Apply permanently (persist after reboot)
echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

#### 2. Clone and Configure
Clone the repository and navigate to the project folder.

```bash
git clone https://github.com/omatheuspimenta/fiocruz-genomics-portal
cd fiocruz-genomics-portal
```

Create a `.env` file with your production secrets:

```bash
cp .env.example .env
# Edit .env and set a strong SECRET_KEY and other variables
nano .env
```

#### 3. Deploy with Docker Compose
Use the production compose file to build and start the optimized stack.

```bash
docker-compose -f docker-compose.prod.yml up --build -d
```

#### 4. Verify Deployment
Check the status of your containers:

```bash
docker-compose -f docker-compose.prod.yml ps
```

- **Frontend**: Accessible at `http://<your-server-ip>` (Port 80).
- **API Docs**: Accessible at `http://<your-server-ip>/docs`.
- **Elasticsearch**: Internal only (or mapped to 9200 if needed for debugging).

#### 5. Monitoring & Logs
To view logs for a specific service (e.g., the app):

```bash
docker-compose -f docker-compose.prod.yml logs -f app
```

To monitor resource usage:

```bash
docker stats
```
You should see the `app` container utilizing multiple cores under load, and Elasticsearch using ~30GB RAM.

---

## Local Development Guide

If you want to modify the code or run components individually on your local env, follow this guide.

### Prerequisites
- **Python 3.11+** (We recommend using [uv](https://github.com/astral-sh/uv) for fast package management).
- **Node.js 18+** (for the frontend).
- **Docker** (required for the Elasticsearch database).

### 1. Database Setup (Elasticsearch)
We use Docker to run the database, as it's complex to install manually.

```bash
# Start only the database
docker-compose up -d elasticsearch
```
*Wait a few seconds for it to initialize.*

### 2. Backend Setup (Python/FastAPI)

1. **Navigate to the project root.**

2. **Install dependencies:**
   If you have `uv` installed:
   ```bash
   uv sync
   ```
   Or using standard pip:
   ```bash
   pip install "fastapi[standard]" "elasticsearch[async]" "pydantic-settings" "python-dotenv" "slowapi"
   ```

3. **Run the API:**
   ```bash
   # Using uv
   uv run uvicorn api:app --reload

   # OR using python directly
   python api.py
   ```
   The backend will start at `http://localhost:8000`.

> [!NOTE]
> You may need to activate your virtual environment before installing packages and running the server.


```bash
# Example using venv
source venv/bin/activate
```

### 3. Export HAIL Data to Elasticsearch

Before running the export scripts, ensure that Elasticsearch is running locally (as described in step 1).  
Follow the instructions in the "Data Management" section below to parse and export data.


### 4. Frontend Setup (React/Vite)

1. **Navigate to the frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Run the development server:**
   ```bash
   npm run dev
   ```
   The frontend will start at `http://localhost:5173` (usually).
   *Note: In development mode, the frontend connects to the backend at localhost:8000.*

---

## Data Management

The repository includes scripts to parse and load genomic data.

### Scripts Location
All scripts are located in the `scripts/` directory.

### 1. Parse Nirvana Output
Converts Nirvana JSON output into a flat structure suitable for Elasticsearch, this script uses Hail for efficient processing and export to Elasticsearch.

```bash
python scripts/parse_nirvana.py --input <path_to_nirvana.json> --output <path_to_output.ht>
```

### 2. Export to Elasticsearch
Loads the processed data into the running Elasticsearch instance.

```bash
python scripts/export_to_es.py --input <path_to_output.json> --index variants
```

---

## Testing

To run the basic backend tests:

```bash
# From the project root
uv run pytest
# OR
pytest
```

---

## Troubleshooting

- **Elasticsearch Connection Error:** Ensure the Docker container is running (`docker ps`) and accessible at `localhost:9200`.
- **Port Conflicts:** If port 8000 or 5173 is in use, stop the other process or change the port in the run commands.
