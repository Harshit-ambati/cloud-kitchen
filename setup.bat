@echo off
REM Cloud Kitchen Setup Script for Windows

echo 🚀 Cloud Kitchen Setup Script
echo ==============================

REM Check Python
echo.
echo Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found. Please install Python 3.9+
    pause
    exit /b 1
)
echo ✓ Python found
for /f "tokens=*" %%i in ('python --version') do echo %%i

REM Check Node
echo.
echo Checking Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Node.js not found. Please install Node.js 16+
    pause
    exit /b 1
)
echo ✓ Node.js found
for /f "tokens=*" %%i in ('node --version') do echo %%i

REM Backend Setup
echo.
echo Setting up Backend...
cd backend
python -m venv venv
call venv\Scripts\activate.bat
pip install -r requirements.txt
echo ✓ Backend dependencies installed

REM Frontend Setup
echo.
echo Setting up Frontend...
cd ..\frontend
call npm install
echo ✓ Frontend dependencies installed

REM Create .env if not exists
echo.
echo Checking configuration...
if not exist "..\backend\.env" (
    (
        echo MONGO_URI=mongodb://localhost:27017/
    ) > ..\backend\.env
    echo ✓ Created .env file
) else (
    echo ✓ .env already exists
)

echo.
echo ==============================
echo ✨ Setup Complete!
echo ==============================
echo.
echo 📝 Next steps:
echo 1. Start MongoDB: mongod
echo 2. Train ML model: python setup_ml.py
echo 3. Start backend: cd backend ^&^& python -m uvicorn app.main:app --reload
echo 4. Start frontend: cd frontend ^&^& npm run dev
echo.
pause
