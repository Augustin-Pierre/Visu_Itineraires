@echo off
cd /d %~dp0

set OSGEO4W_ROOT=C:\Program Files\QGIS 3.40.12

call "%OSGEO4W_ROOT%\bin\o4w_env.bat"

echo Compilation des ressources en cours...
call pyrcc5 -o resources.py resources.qrc

echo Termine !
pause