@echo off
REM Quick test runner for EDMCVKBConnector
REM Run this from the project root directory

setlocal enabledelayedexpansion

echo.
echo ====================================================================
echo           EDMCVKBConnector Test Runner
echo ====================================================================
echo.

REM Check if we're in the right directory
if not exist "test" (
    echo ERROR: test directory not found!
    echo Please run this from the project root directory.
    exit /b 1
)

REM Parse command line argument
set TEST_TYPE=%1
if "%TEST_TYPE%"=="" set TEST_TYPE=all

cd test

if "%TEST_TYPE%"=="unit" (
    echo Running UNIT TESTS only
    echo.
    python test_config.py
    goto :end
)

if "%TEST_TYPE%"=="integration" (
    echo Running INTEGRATION TESTS only
    echo.
    python test_integration.py
    goto :end
)

if "%TEST_TYPE%"=="server" (
    echo Running VKB SERVER INTEGRATION TESTS
    echo.
    python test_vkb_server_integration.py
    goto :end
)

if "%TEST_TYPE%"=="real" (
    echo Running REAL VKB SERVER INTEGRATION TESTS
    echo.
    echo NOTE: These tests require VKB hardware with VKB-Link running
    echo.
    python test_real_vkb_server.py
    goto :end
)

if "%TEST_TYPE%"=="rules" (
    echo Running COMPREHENSIVE RULES ENGINE TESTS
    echo.
    python test_rules_comprehensive.py
    goto :end
)

if "%TEST_TYPE%"=="dev" (
    echo Running FULL DEVELOPMENT TEST with EDMC environment
    echo.
    python dev_test.py
    goto :end
)

if "%TEST_TYPE%"=="mock" (
    echo Starting MOCK VKB SERVER
    echo Listen on 127.0.0.1:50995
    echo Press Ctrl+C to stop
    echo.
    python mock_vkb_server.py
    goto :end
)

if "%TEST_TYPE%"=="all" (
    echo Running ALL tests (unit + integration + server + dev)
    echo.
    python dev_test.py
    goto :end
)

REM Invalid option
echo Usage: test.bat [unit^|integration^|server^|real^|rules^|dev^|mock^|all]
echo.
echo   unit         - Run unit tests only
echo   integration  - Run integration tests only
echo   server       - Run VKB mock server tests
echo   real         - Run tests against REAL VKB hardware (requires VKB-Link)
echo   rules        - Run comprehensive rules engine tests
echo   dev          - Run full dev test with EDMC environment
echo   mock         - Start mock VKB server
echo   all          - Run all tests (default, skips real tests)
echo.
echo Examples:
echo   test.bat              # Run all tests (mock server only)
echo   test.bat unit         # Quick syntax check
echo   test.bat server       # Test VKB socket operations
echo   test.bat rules        # Test rules engine with 23 test cases
echo   test.bat real         # Test against real VKB hardware
echo   test.bat dev          # Full test with EDMC

:end
cd ..
endlocal
