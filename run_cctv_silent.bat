@echo off
:: Silent Background Launcher for Xiaomi CCTV AI Engine
:: Runs completely independently of Antigravity or command prompts
cd /d "%~dp0"

echo [1/3] Starting Live Stream AI Supervisor...
start "" /B pythonw live_stream_daemon.py

echo [2/3] Starting Web Dashboard on Port 8501...
start "" /B pythonw -m streamlit run app_dashboard.py --server.port 8501 --server.headless true

echo [3/3] System running in background! Access dashboard at: http://localhost:8501
