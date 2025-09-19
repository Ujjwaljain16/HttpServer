# HTTP Server Demo Script (PowerShell)
# Run this to demonstrate the server's capabilities

Write-Host "Multi-threaded HTTP Server Demo" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host

# Check if server is running
Write-Host "1. Checking server status..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:8080/" -TimeoutSec 2 -UseBasicParsing
    Write-Host "✅ Server is running on http://127.0.0.1:8080" -ForegroundColor Green
} catch {
    Write-Host "❌ Server is not running. Please start it first:" -ForegroundColor Red
    Write-Host "   python server.py 8080 127.0.0.1 4" -ForegroundColor Yellow
    exit 1
}

Write-Host
Write-Host "2. Testing basic functionality..." -ForegroundColor Yellow

# Test homepage
Write-Host "Homepage (GET /):" -ForegroundColor Cyan
$homepage = Invoke-WebRequest -Uri "http://127.0.0.1:8080/" -UseBasicParsing
$homepage.Content -split "`n" | Select-Object -First 5
Write-Host

# Test file download
Write-Host "File download (GET /logo.png):" -ForegroundColor Cyan
$fileResponse = Invoke-WebRequest -Uri "http://127.0.0.1:8080/logo.png" -UseBasicParsing
Write-Host "Status: $($fileResponse.StatusCode)"
Write-Host "Content-Type: $($fileResponse.Headers['Content-Type'])"
Write-Host "Content-Length: $($fileResponse.Headers['Content-Length'])"
Write-Host

# Test JSON upload
Write-Host "JSON upload (POST /upload):" -ForegroundColor Cyan
$jsonData = @{
    demo = "data"
    timestamp = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")
} | ConvertTo-Json

$headers = @{
    "Content-Type" = "application/json"
}

$uploadResponse = Invoke-WebRequest -Uri "http://127.0.0.1:8080/upload" -Method POST -Body $jsonData -Headers $headers -UseBasicParsing
Write-Host $uploadResponse.Content
Write-Host

Write-Host "3. Testing security features..." -ForegroundColor Yellow

# Test path traversal protection
Write-Host "Path traversal protection (GET /../etc/passwd):" -ForegroundColor Cyan
try {
    $traversalResponse = Invoke-WebRequest -Uri "http://127.0.0.1:8080/../etc/passwd" -UseBasicParsing
    Write-Host "Status: $($traversalResponse.StatusCode)"
} catch {
    if ($_.Exception.Response.StatusCode -eq 403) {
        Write-Host "Status: 403 (Forbidden) - Correctly blocked!" -ForegroundColor Green
    } else {
        Write-Host "Status: $($_.Exception.Response.StatusCode)"
    }
}
Write-Host

# Test Host header validation
Write-Host "Host header validation (Host: evil.com):" -ForegroundColor Cyan
try {
    $evilHeaders = @{
        "Host" = "evil.com:8080"
    }
    $evilResponse = Invoke-WebRequest -Uri "http://127.0.0.1:8080/" -Headers $evilHeaders -UseBasicParsing
    Write-Host "Status: $($evilResponse.StatusCode)"
} catch {
    if ($_.Exception.Response.StatusCode -eq 403) {
        Write-Host "Status: 403 (Forbidden) - Correctly blocked!" -ForegroundColor Green
    } else {
        Write-Host "Status: $($_.Exception.Response.StatusCode)"
    }
}
Write-Host

# Test missing Host header
Write-Host "Missing Host header:" -ForegroundColor Cyan
try {
    $emptyHeaders = @{
        "Host" = ""
    }
    $emptyResponse = Invoke-WebRequest -Uri "http://127.0.0.1:8080/" -Headers $emptyHeaders -UseBasicParsing
    Write-Host "Status: $($emptyResponse.StatusCode)"
} catch {
    if ($_.Exception.Response.StatusCode -eq 400) {
        Write-Host "Status: 400 (Bad Request) - Correctly rejected!" -ForegroundColor Green
    } else {
        Write-Host "Status: $($_.Exception.Response.StatusCode)"
    }
}
Write-Host

Write-Host "4. Running comprehensive integration tests..." -ForegroundColor Yellow
Write-Host "Integration Test Suite:" -ForegroundColor Cyan
python tests/integration_test.py

Write-Host
Write-Host "Demo complete! Check the server logs for detailed information." -ForegroundColor Green
Write-Host "   The server supports persistent connections, thread pooling," -ForegroundColor White
Write-Host "   security validation, and comprehensive error handling." -ForegroundColor White
