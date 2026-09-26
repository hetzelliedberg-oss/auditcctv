FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies for OpenCV, PyAV, and Thai fonts
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    fonts-thai-tlwg \
    git \
    curl \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create supervisord configuration to run both daemon and dashboard
RUN mkdir -p /etc/supervisor/conf.d
RUN echo "[supervisord]\nnodaemon=true\n\n[program:daemon]\ncommand=python live_stream_daemon.py\nautostart=true\nautorestart=true\nstderr_logfile=/var/log/daemon.err.log\nstdout_logfile=/var/log/daemon.out.log\n\n[program:dashboard]\ncommand=streamlit run app_dashboard.py --server.port 8501 --server.address 0.0.0.0 --server.headless true\nautostart=true\nautorestart=true\nstderr_logfile=/var/log/dashboard.err.log\nstdout_logfile=/var/log/dashboard.out.log\n" > /etc/supervisor/conf.d/supervisord.conf

EXPOSE 8501

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
