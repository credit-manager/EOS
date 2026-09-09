@echo off
cd /d D:\EOS\Eos final
python -m uvicorn main:app --host 127.0.0.1 --port 8000
