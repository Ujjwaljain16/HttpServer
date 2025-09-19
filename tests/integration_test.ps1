# HTTP Server Integration Test Script (PowerShell)
# Tests all major functionality of the HTTP server

param(
    [string]$ServerHost = "127.0.0.1",
    [int]$Port = 8080
)

$BaseUrl = "http://${ServerHost}:${Port}"

# Test counters
$TestsPassed = 0
$TestsFailed = 0

# Function to print test results
function Write-TestResult {
    param(
        [string]$TestName,
        [string]$Status,
        [string]$Message = ""
    )
    
    if ($Status -eq "PASS") {
        Write-Host "✅ PASS $TestName" -ForegroundColor Green
        $script:TestsPassed++
    } else {
        Write-Host "❌ FAIL $TestName" -ForegroundColor Red
        if ($Message) {
            Write-Host "    $Message" -ForegroundColor Yellow
        }
        $script:TestsFailed++
    }
}

# Function to check if server is running
function Test-ServerConnectivity {
    Write-Host "Checking server connectivity..."
    try {
        $response = Invoke-WebRequest -Uri "$BaseUrl/" -TimeoutSec 5 -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            Write-Host "✅ Server is running on $BaseUrl" -ForegroundColor Green
            return $true
        } else {
            Write-Host "❌ Server returned status $($response.StatusCode)" -ForegroundColor Red
            return $false
        }
    } catch {
        Write-Host "❌ Server is not responding on $BaseUrl" -ForegroundColor Red
        Write-Host "Please start the server first:" -ForegroundColor Yellow
        Write-Host "  python server.py $Port $ServerHost 2" -ForegroundColor Yellow
        return $false
    }
}

# Test 1: GET / returns 200 and contains <html>
function Test-GetHomepage {
    Write-Host "Testing GET / homepage..."
    
    try {
        $response = Invoke-WebRequest -Uri "$BaseUrl/" -UseBasicParsing
        
        if ($response.StatusCode -eq 200) {
            if ($response.Content -match "<html") {
                Write-TestResult "GET Homepage" "PASS" "Status: $($response.StatusCode), contains <html>"
            } else {
                Write-TestResult "GET Homepage" "FAIL" "Status: $($response.StatusCode), but missing <html>"
            }
        } else {
            Write-TestResult "GET Homepage" "FAIL" "Expected 200, got $($response.StatusCode)"
        }
    } catch {
        Write-TestResult "GET Homepage" "FAIL" "Exception: $($_.Exception.Message)"
    }
}

# Test 2: Download logo.png and verify file size
function Test-FileDownload {
    Write-Host "Testing file download..."
    
    try {
        $response = Invoke-WebRequest -Uri "$BaseUrl/logo.png" -UseBasicParsing
        
        if ($response.StatusCode -eq 200) {
            # Check Content-Type
            $contentType = $response.Headers["Content-Type"]
            if ($contentType -like "*application/octet-stream*") {
                # Check if file exists in resources and compare size
                $resourcesFile = "resources/logo.png"
                if (Test-Path $resourcesFile) {
                    $expectedSize = (Get-Item $resourcesFile).Length
                    $actualSize = $response.Content.Length
                    
                    if ($actualSize -eq $expectedSize) {
                        Write-TestResult "File Download" "PASS" "Size: $actualSize bytes, Content-Type: $contentType"
                    } else {
                        Write-TestResult "File Download" "FAIL" "Size mismatch: downloaded $actualSize, original $expectedSize"
                    }
                } else {
                    Write-TestResult "File Download" "FAIL" "Source file resources/logo.png does not exist"
                }
            } else {
                Write-TestResult "File Download" "FAIL" "Expected application/octet-stream, got $contentType"
            }
        } else {
            Write-TestResult "File Download" "FAIL" "Expected 200, got $($response.StatusCode)"
        }
    } catch {
        Write-TestResult "File Download" "FAIL" "Exception: $($_.Exception.Message)"
    }
}

# Test 3: POST JSON to /upload and verify 201 and file creation
function Test-JsonUpload {
    Write-Host "Testing JSON upload..."
    
    try {
        # Create test JSON data
        $testData = @{
            test = "integration_test"
            timestamp = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")
            message = "This is a test upload from integration test"
        } | ConvertTo-Json
        
        $headers = @{
            "Content-Type" = "application/json"
        }
        
        $response = Invoke-WebRequest -Uri "$BaseUrl/upload" -Method POST -Body $testData -Headers $headers -UseBasicParsing
        
        if ($response.StatusCode -eq 201) {
            # Parse JSON response to get filepath
            $responseData = $response.Content | ConvertFrom-Json
            
            if ($responseData.filepath) {
                # Check if file exists
                $fullPath = "resources" + $responseData.filepath
                if (Test-Path $fullPath) {
                    Write-TestResult "JSON Upload" "PASS" "File created: $($responseData.filepath)"
                } else {
                    Write-TestResult "JSON Upload" "FAIL" "File not found: $fullPath"
                }
            } else {
                Write-TestResult "JSON Upload" "FAIL" "No filepath in response"
            }
        } else {
            Write-TestResult "JSON Upload" "FAIL" "Expected 201, got $($response.StatusCode)"
        }
    } catch {
        Write-TestResult "JSON Upload" "FAIL" "Exception: $($_.Exception.Message)"
    }
}

# Test 4: Path traversal protection
function Test-PathTraversal {
    Write-Host "Testing path traversal protection..."
    
    try {
        $response = Invoke-WebRequest -Uri "$BaseUrl/../etc/passwd" -UseBasicParsing
        
        if ($response.StatusCode -eq 403) {
            if ($response.Content -match "forbidden") {
                Write-TestResult "Path Traversal Protection" "PASS" "Status: $($response.StatusCode), correctly blocked"
            } else {
                Write-TestResult "Path Traversal Protection" "FAIL" "Status: $($response.StatusCode), but missing 'Forbidden' in body"
            }
        } else {
            Write-TestResult "Path Traversal Protection" "FAIL" "Expected 403, got $($response.StatusCode)"
        }
    } catch {
        # Check if it's a 403 error
        if ($_.Exception.Response.StatusCode -eq 403) {
            Write-TestResult "Path Traversal Protection" "PASS" "Status: 403, correctly blocked"
        } else {
            Write-TestResult "Path Traversal Protection" "FAIL" "Exception: $($_.Exception.Message)"
        }
    }
}

# Test 5: Host header validation
function Test-HostValidation {
    Write-Host "Testing Host header validation..."
    
    try {
        $headers = @{
            "Host" = "evil.com:8080"
        }
        
        $response = Invoke-WebRequest -Uri "$BaseUrl/" -Headers $headers -UseBasicParsing
        
        if ($response.StatusCode -eq 403) {
            if ($response.Content -match "forbidden|host mismatch") {
                Write-TestResult "Host Validation" "PASS" "Status: $($response.StatusCode), correctly blocked evil.com"
            } else {
                Write-TestResult "Host Validation" "FAIL" "Status: $($response.StatusCode), but missing 'Forbidden' or 'Host mismatch' in body"
            }
        } else {
            Write-TestResult "Host Validation" "FAIL" "Expected 403, got $($response.StatusCode)"
        }
    } catch {
        # Check if it's a 403 error
        if ($_.Exception.Response.StatusCode -eq 403) {
            Write-TestResult "Host Validation" "PASS" "Status: 403, correctly blocked evil.com"
        } else {
            Write-TestResult "Host Validation" "FAIL" "Exception: $($_.Exception.Message)"
        }
    }
}

# Test 6: Missing Host header
function Test-MissingHost {
    Write-Host "Testing missing Host header..."
    
    try {
        # Use a custom request without Host header
        $request = [System.Net.WebRequest]::Create("$BaseUrl/")
        $request.Method = "GET"
        $response = $request.GetResponse()
        
        Write-TestResult "Missing Host Header" "FAIL" "Expected 400, got $($response.StatusCode)"
        $response.Close()
    } catch {
        if ($_.Exception.Response.StatusCode -eq 400) {
            Write-TestResult "Missing Host Header" "PASS" "Status: 400, correctly rejected"
        } else {
            Write-TestResult "Missing Host Header" "FAIL" "Exception: $($_.Exception.Message)"
        }
    }
}

# Test 7: Unsupported HTTP method
function Test-UnsupportedMethod {
    Write-Host "Testing unsupported HTTP method..."
    
    try {
        $response = Invoke-WebRequest -Uri "$BaseUrl/" -Method PUT -UseBasicParsing
        
        if ($response.StatusCode -eq 405) {
            $allowHeader = $response.Headers["Allow"]
            Write-TestResult "Unsupported Method" "PASS" "Status: $($response.StatusCode), Allow: $allowHeader"
        } else {
            Write-TestResult "Unsupported Method" "FAIL" "Expected 405, got $($response.StatusCode)"
        }
    } catch {
        if ($_.Exception.Response.StatusCode -eq 405) {
            Write-TestResult "Unsupported Method" "PASS" "Status: 405, correctly rejected PUT"
        } else {
            Write-TestResult "Unsupported Method" "FAIL" "Exception: $($_.Exception.Message)"
        }
    }
}

# Test 8: Unsupported content type
function Test-UnsupportedContentType {
    Write-Host "Testing unsupported content type..."
    
    try {
        $headers = @{
            "Content-Type" = "text/plain"
        }
        $body = "This is not JSON"
        
        $response = Invoke-WebRequest -Uri "$BaseUrl/upload" -Method POST -Body $body -Headers $headers -UseBasicParsing
        
        if ($response.StatusCode -eq 415) {
            Write-TestResult "Unsupported Content-Type" "PASS" "Status: $($response.StatusCode), correctly rejected"
        } else {
            Write-TestResult "Unsupported Content-Type" "FAIL" "Expected 415, got $($response.StatusCode)"
        }
    } catch {
        if ($_.Exception.Response.StatusCode -eq 415) {
            Write-TestResult "Unsupported Content-Type" "PASS" "Status: 415, correctly rejected"
        } else {
            Write-TestResult "Unsupported Content-Type" "FAIL" "Exception: $($_.Exception.Message)"
        }
    }
}

# Main test execution
function Main {
    Write-Host "================================================================"
    Write-Host "HTTP SERVER INTEGRATION TEST SUITE (PowerShell)"
    Write-Host "================================================================"
    Write-Host "Testing server at $BaseUrl"
    Write-Host ""
    
    # Check if server is running
    if (-not (Test-ServerConnectivity)) {
        exit 1
    }
    
    Write-Host ""
    
    # Run all tests
    Test-GetHomepage
    Test-FileDownload
    Test-JsonUpload
    Test-PathTraversal
    Test-HostValidation
    Test-MissingHost
    Test-UnsupportedMethod
    Test-UnsupportedContentType
    
    # Print summary
    Write-Host ""
    Write-Host "================================================================"
    Write-Host "TEST SUMMARY"
    Write-Host "================================================================"
    Write-Host "Total Tests: $($TestsPassed + $TestsFailed)"
    Write-Host "Passed: $TestsPassed" -ForegroundColor Green
    Write-Host "Failed: $TestsFailed" -ForegroundColor Red
    
    $successRate = [math]::Round(($TestsPassed / ($TestsPassed + $TestsFailed)) * 100, 1)
    Write-Host "Success Rate: $successRate%"
    
    if ($TestsFailed -eq 0) {
        Write-Host ""
        Write-Host "🎉 ALL TESTS PASSED! Server is working correctly." -ForegroundColor Green
        exit 0
    } else {
        Write-Host ""
        Write-Host "⚠️  $TestsFailed test(s) failed. Check the output above for details." -ForegroundColor Yellow
        exit 1
    }
}

# Run main function
Main
