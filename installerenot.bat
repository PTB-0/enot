@echo off
setlocal enabledelayedexpansion

set "hedef=%USERPROFILE%\AppData\Local\enot"

if exist "%hedef%" (
    set /p ask=ENOT ZATEN VAR. SILMEK ISTER MISIN (E/H): 

    if /i "!ask!"=="E" (
        rmdir /s /q "%hedef%"
        mkdir "%hedef%"
    ) else (
        echo Islem iptal edildi.
        pause
        exit
    )
) else (
    mkdir "%hedef%"
)

cd /d "%hedef%"

curl -O https://raw.githubusercontent.com/PTB-0/enot/main/notPedFM.py

echo Kurulum tamamlandi.
pause