# Docker guide

Build image:

1. From the repository root, build the Docker image (PowerShell/CMD):

   docker build -t keylogger-dashboard:latest .

Run container:

2. Run the container mapping port 5000:

   docker run -it --rm -p 5000:5000 --name keylogger-server keylogger-dashboard:latest

Notes:
- The server uses Flask-SocketIO and the image installs `eventlet`. Logs will be printed to stdout.
- If you need to persist the SQLite DB between runs, mount a volume:

   docker run -it --rm -p 5000:5000 -v %CD%/clients.db:/app/clients.db --name keylogger-server keylogger-dashboard:latest


Using Docker Compose (recommended for development):

1. Create a host data directory and an empty `clients.db` file so the container can use it. This avoids overwriting the application source inside the container:

   mkdir data
   type NUL > data\clients.db   # PowerShell/CMD on Windows; on Unix use: touch data/clients.db

2. Start the service with Docker Compose:

   docker compose up --build

This maps the host `./data/clients.db` file into the container at `/app/clients.db`, so the SQLite DB is persisted on the host without replacing the application files in `/app`.

To stop and remove containers created by compose:

   docker compose down

