@echo off
chcp 936 >nul
setlocal
set "PROJ=%~dp0"
if "%PROJ:~-1%"=="\" set "PROJ=%PROJ:~0,-1%"

echo ============================================================
echo   水文地质学科研环境  -  一键打开
echo   项目位置: %PROJ%
echo ============================================================
echo.

echo [1/2] 正在打开项目文件夹 ...
where code >nul 2>nul
if errorlevel 1 goto use_explorer
start "" code "%PROJ%"
echo   -^> 已用 VS Code 打开
goto after_open
:use_explorer
start "" explorer "%PROJ%"
echo   -^> 已用文件资源管理器打开
:after_open

echo [2/2] 可选：跑一次环境自检（失败不影响打开）...
where python >nul 2>nul
if errorlevel 1 goto no_python
if not exist "%PROJ%\scripts\test_check.py" goto no_script
echo   检测到 python 与自检脚本，开始自检（输出仅供参考）...
echo   ------------------------------------------------
python "%PROJ%\scripts\test_check.py"
echo   ------------------------------------------------
echo   自检结束。无论结果如何，文件夹已打开，可放心使用。
goto done
:no_script
echo   自检脚本不存在（你可能调整过结构），跳过自检。
goto done
:no_python
echo   未检测到 python，跳过自检。装好 Python/Miniconda 后再手动跑。
:done
echo.
echo 完成。完整步骤见 README.md，关掉本窗口即可。
pause
