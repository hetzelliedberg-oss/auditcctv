@echo off
echo Starting Xiaomi CCTV Analytics Services in background...
start /B python live_stream_daemon.py
start /B streamlit run app_dashboard.py --server.port 8501 --server.headless true
echo Services started! Dashboard is at http://localhost:8501
