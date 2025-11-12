@echo off
echo ============================================================
echo Restarting Dev Server and Running Evaluation
echo ============================================================
echo.

echo Step 1: Finding and stopping the current dev server (PID 19932)...
taskkill /PID 19932 /F
timeout /t 2 /nobreak >nul

echo.
echo Step 2: Starting dev server in background...
cd ..\ai-sdk-rag-starter
start "Dev Server" cmd /c "pnpm run dev"

echo.
echo Waiting 10 seconds for server to start...
timeout /t 10 /nobreak

echo.
echo Step 3: Running API evaluation...
cd ..\evaluation
python api_evaluation.py

echo.
echo ============================================================
echo Done!
echo ============================================================
pause
