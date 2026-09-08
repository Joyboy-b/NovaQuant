@echo off
setlocal
for /f "usebackq delims=" %%i in (`"%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do set "NOVA_VS_PATH=%%i"
if not defined NOVA_VS_PATH exit /b 1
call "%NOVA_VS_PATH%\VC\Auxiliary\Build\vcvars64.bat"
if errorlevel 1 exit /b 1
cd /d "%~dp0.."
if not exist build-benchmark mkdir build-benchmark
cl /nologo /O2 /EHsc /std:c++17 /fp:precise /LD engine-cpp\backtest.cpp /Fobuild-benchmark\backtest.obj /Febuild-benchmark\novaquant_backtest.dll /link /IMPLIB:build-benchmark\novaquant_backtest.lib
exit /b %errorlevel%
