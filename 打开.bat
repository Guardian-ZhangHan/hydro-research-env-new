锘緻echo off
chcp 936 >nul
setlocal
set "PROJ=%~dp0"
if "%PROJ:~-1%"=="\" set "PROJ=%PROJ:~0,-1%"

echo ============================================================
echo   姘存枃鍦拌川瀛︾鐮旂幆澧? -  涓€閿墦寮€
echo   椤圭洰浣嶇疆: %PROJ%
echo ============================================================
echo.

echo [1/2] 姝ｅ湪鎵撳紑椤圭洰鏂囦欢澶?...
where code >nul 2>nul
if errorlevel 1 goto use_explorer
start "" code "%PROJ%"
echo   -^> 宸茬敤 VS Code 鎵撳紑
goto after_open
:use_explorer
start "" explorer "%PROJ%"
echo   -^> 宸茬敤鏂囦欢璧勬簮绠＄悊鍣ㄦ墦寮€
:after_open

echo [2/2] 鍙€夛細璺戜竴娆＄幆澧冭嚜妫€锛堝け璐ヤ笉褰卞搷鎵撳紑锛?..
where python >nul 2>nul
if errorlevel 1 goto no_python
if not exist "%PROJ%\scripts\test_check.py" goto no_script
echo   妫€娴嬪埌 python 涓庤嚜妫€鑴氭湰锛屽紑濮嬭嚜妫€锛堣緭鍑轰粎渚涘弬鑰冿級...
echo   ------------------------------------------------
python "%PROJ%\scripts\test_check.py"
echo   ------------------------------------------------
echo   鑷缁撴潫銆傛棤璁虹粨鏋滃浣曪紝鏂囦欢澶瑰凡鎵撳紑锛屽彲鏀惧績浣跨敤銆?
goto done
:no_script
echo   鑷鑴氭湰涓嶅瓨鍦紙浣犲彲鑳借皟鏁磋繃缁撴瀯锛夛紝璺宠繃鑷銆?
goto done
:no_python
echo   鏈娴嬪埌 python锛岃烦杩囪嚜妫€銆傝濂?Python/Miniconda 鍚庡啀鎵嬪姩璺戙€?
:done
echo.
echo 瀹屾垚銆傚畬鏁存楠よ README.md锛屽叧鎺夋湰绐楀彛鍗冲彲銆?
pause
