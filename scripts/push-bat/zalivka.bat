@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
title ЗАЛИВКА - локальная работа -> GitHub (через патчи)

rem ============================================================
rem  ЗАЛИВКА.bat - механизм заливки локальной работы в репо.
rem  Режимы:  (без аргументов = меню)
rem    sync   - сверка с origin + pull --rebase, отчёт
rem    patch  - незапушенное -> патчи в _patches\ (коммиты + рабочее дерево)
rem    fixcrlf- снять фантомные CRLF-диффы (renormalize), без коммита
rem    push   - коммит реальных изменений + pull --rebase + push
rem    force  - push --force-with-lease (только осознанно!)
rem  Список репо: repos.txt рядом с батником (по одному пути в строке).
rem  Токен НЕ хранится: авторизация через Git Credential Manager.
rem ============================================================

set "MODE=%~1"
set "ROOT=%~dp0"
set "LOG=%ROOT%_zalivka_log.txt"
set "STAMP=%date% %time%"

if "%MODE%"=="" goto MENU
goto RUN

:MENU
echo.
echo  ============ ЗАЛИВКА ============
echo   1. sync   - сверка и подтяжка с GitHub
echo   2. patch  - незапушенное в патчи (_patches\)
echo   3. fixcrlf- снять фантомные CRLF-диффы
echo   4. push   - коммит + pull --rebase + push
echo   5. force  - force-with-lease (опасно)
echo   0. выход
echo =================================
set /p CHOICE="Выбор: "
if "%CHOICE%"=="1" set MODE=sync
if "%CHOICE%"=="2" set MODE=patch
if "%CHOICE%"=="3" set MODE=fixcrlf
if "%CHOICE%"=="4" set MODE=push
if "%CHOICE%"=="5" set MODE=force
if "%MODE%"=="" goto :eof

:RUN
if not exist "%ROOT%repos.txt" (
  echo [X] Нет repos.txt рядом с батником. Создай из repos.txt.example.
  exit /b 1
)
where git >nul 2>nul || (echo [X] git не найден в PATH & exit /b 1)

echo ===== ЗАЛИВКА %MODE% :: %STAMP% ===== >> "%LOG%"

for /f "usebackq eol=# delims=" %%R in ("%ROOT%repos.txt") do call :ONE "%%R"
echo.
echo ===== ГОТОВО. Полный журнал: %LOG% =====
if "%MODE%"=="patch" echo Патчи лежат в ^<репо^>\_patches\ - их можно переносить и применять отдельно.
exit /b 0

:ONE
set "REPO=%~1"
if not exist "%REPO%\.git" (
  echo [skip] %REPO% - не git-репо >> "%LOG%"
  echo [skip] %REPO%
  exit /b 0
)
echo.
echo ---- %REPO% ----
for /f %%B in ('git -C "%REPO%" rev-parse --abbrev-ref HEAD 2^>nul') do set "BR=%%B"
echo   ветка: !BR!
echo ---- %REPO% [!BR!] %MODE% %STAMP% ---- >> "%LOG%"

if "%MODE%"=="fixcrlf" goto MODE_FIXCRLF
if "%MODE%"=="sync"  goto MODE_SYNC
if "%MODE%"=="patch" goto MODE_PATCH
if "%MODE%"=="push"  goto MODE_PUSH
if "%MODE%"=="force" goto MODE_FORCE
exit /b 0

:MODE_FIXCRLF
git -C "%REPO%" add --renormalize . >> "%LOG%" 2>&1
git -C "%REPO%" diff --cached --quiet
if errorlevel 1 (
  echo   [!] После renormalize есть реальные изменения - смотри git -C "%REPO%" diff --cached
  echo   [!] renormalize обнаружил РЕАЛЬНЫЕ изменения >> "%LOG%"
) else (
  echo   [ok] Фантомных CRLF-диффов больше нет; реальных изменений нет
  echo   [ok] fixcrlf: только фантомы, откат >> "%LOG%"
)
git -C "%REPO%" reset -q >> "%LOG%" 2>&1
exit /b 0

:MODE_SYNC
git -C "%REPO%" pull --rebase >> "%LOG%" 2>&1
if errorlevel 1 (echo   [X] pull --rebase упал - см. журнал & exit /b 0) else (echo   [ok] подтянуто)
for /f %%N in ('git -C "%REPO%" rev-list --count HEAD..@{u} 2^>nul') do echo   впереди(локал) коммитов: %%N
exit /b 0

:MODE_PATCH
if not exist "%REPO%\_patches" mkdir "%REPO%\_patches"
git -C "%REPO%" format-patch "@{u}..HEAD" -o "%REPO%\_patches" >> "%LOG%" 2>&1
git -C "%REPO%" diff HEAD > "%REPO%\_patches\00-worktree.patch" 2>> "%LOG%"
for %%F in ("%REPO%\_patches\*.patch") do echo   патч: %%~nxF
git -C "%REPO%" log --oneline "@{u}..HEAD" >> "%LOG%" 2>&1
echo   [ok] патчи готовы в %REPO%\_patches
exit /b 0

:MODE_PUSH
git -C "%REPO%" add --renormalize . >> "%LOG%" 2>&1
git -C "%REPO%" diff --cached --quiet
if not errorlevel 1 (
  echo   [i] реальных изменений нет - только push коммитов, если есть
) else (
  for /f "delims=" %%M in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd HH:mm"') do set "NOW=%%M"
  git -C "%REPO%" commit -m "local work: !NOW! (заливка.bat)" >> "%LOG%" 2>&1
  echo   [ok] закоммичено
)
git -C "%REPO%" pull --rebase >> "%LOG%" 2>&1 || (echo   [X] конфликт rebase - разбирай руками; журнал: %LOG% & exit /b 0)
git -C "%REPO%" push >> "%LOG%" 2>&1
if errorlevel 1 (echo   [X] push не прошёл - нужны креды (Git Credential Manager) или нет прав & exit /b 0)
echo   [ok] запушено
exit /b 0

:MODE_FORCE
echo   [!] force-with-lease: перезапишет удалённую ветку, если кто-то успел раньше
git -C "%REPO%" push --force-with-lease >> "%LOG%" 2>&1
if errorlevel 1 (echo   [X] force не прошёл & exit /b 0)
echo   [ok] force-with-lease прошёл
exit /b 0
