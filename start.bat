@echo off
echo Starting CompanyOS Backend...
echo Serving on http://localhost:8001
call .\venv\Scripts\activate
python -m uvicorn backend.main:app --reload --port 8001
pause
