# AI简历-岗位智能匹配 启动脚本
Write-Host "Starting..." -ForegroundColor Green

# Kill old processes
Get-Process -Name streamlit -ErrorAction SilentlyContinue | Stop-Process -Force

# Start
Set-Location $PSScriptRoot
Start-Process "http://localhost:8501"
streamlit run app.py --server.headless true
