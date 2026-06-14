# Démarre le backend FastAPI et le frontend SvelteKit dans deux fenêtres séparées

Write-Host "Démarrage de YGO Intel..." -ForegroundColor Cyan

# Backend
Start-Process powershell -ArgumentList "-NoExit", "-Command", @"
  Set-Location 'C:\Projects\ygo-deckbuild\backend'
  Write-Host 'Backend FastAPI sur http://localhost:8000' -ForegroundColor Green
  .\.venv\Scripts\uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
"@

# Frontend
Start-Process powershell -ArgumentList "-NoExit", "-Command", @"
  Set-Location 'C:\Projects\ygo-deckbuild\frontend'
  Write-Host 'Frontend SvelteKit sur http://localhost:5173' -ForegroundColor Green
  npm run dev
"@

Write-Host ""
Write-Host "  Frontend : http://localhost:5173" -ForegroundColor Yellow
Write-Host "  Backend  : http://localhost:8000" -ForegroundColor Yellow
Write-Host "  API docs : http://localhost:8000/docs" -ForegroundColor Yellow
Write-Host ""
Write-Host "Ferme les deux fenêtres PowerShell pour arrêter." -ForegroundColor Gray
