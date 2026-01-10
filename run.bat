@echo off
echo ========================================
echo   SVG to PDF Merger - Launcher
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python from: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Check if pypdf is installed
echo Checking dependencies...
python -c "import pypdf" >nul 2>&1
if errorlevel 1 (
    echo pypdf is not installed. Installing now...
    pip install pypdf
    if errorlevel 1 (
        echo [ERROR] Failed to install pypdf
        echo Try running: pip install pypdf
        pause
        exit /b 1
    )
    echo pypdf installed successfully.
) else (
    echo pypdf is already installed.
)

REM Check if all required files exist
echo.
echo Checking application files...
if not exist "main.py" (
    echo [ERROR] main.py not found!
    echo Please make sure all files are in the same directory:
    echo   main.py, gui.py, pdf_merger.py, svg_processor.py, utils.py
    pause
    exit /b 1
)

if not exist "gui.py" (
    echo [ERROR] gui.py not found!
    pause
    exit /b 1
)

if not exist "pdf_merger.py" (
    echo [ERROR] pdf_merger.py not found!
    pause
    exit /b 1
)

if not exist "svg_processor.py" (
    echo [ERROR] svg_processor.py not found!
    pause
    exit /b 1
)

if not exist "utils.py" (
    echo [ERROR] utils.py not found!
    pause
    exit /b 1
)

echo All files found.
echo.

REM Run the application
echo Starting SVG to PDF Merger...
echo.
echo --------------------------------------------------------
echo   Application is starting...
echo   Please wait for the GUI window to appear.
echo --------------------------------------------------------
echo.

python main.py

if errorlevel 1 (
    echo.
    echo [ERROR] Application crashed!
    echo Possible issues:
    echo 1. Missing dependencies - try: pip install pypdf
    echo 2. Corrupted files - redownload the application
    echo 3. Inkscape not installed at default location
    pause
    exit /b 1
)

echo.
echo Application closed.
pause