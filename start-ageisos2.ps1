# Start AgeisOS2 development environment
# Launches backend bridge, frontend UI, and Python core in separate PowerShell windows

Write-Host "Starting AgeisOS2..." -ForegroundColor Green

# Backend bridge (Express/Socket.IO on port 5000)
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd `"'$PSScriptRoot\backend-bridge'`"; npm start" -WorkingDirectory "$PSScriptRoot"

# Frontend UI (Vite dev server on port 5173)
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd `"'$PSScriptRoot\frontend-ui'`"; npm run dev" -WorkingDirectory "$PSScriptRoot"

# Python core assistant
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd `"'$PSScriptRoot\python-core'`"; & `"'C:\Users\ayush\AppData\Local\Python\bin\python.exe'"` core.py" -WorkingDirectory "$PSScriptRoot"

Write-Host "All services started. Check each window for output." -ForegroundColor Yellow
