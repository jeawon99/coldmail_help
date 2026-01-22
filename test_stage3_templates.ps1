# Stage 3: Templates API 테스트
$baseUrl = "http://127.0.0.1:8000/api/v1"

Write-Host "`n=== Stage 3: Templates API 테스트 시작 ===" -ForegroundColor Cyan

# 1. Template 생성
Write-Host "`n[1] POST /templates/ - Template 생성" -ForegroundColor Yellow
$template1 = @{
    name = "Welcome Email"
    description = "Welcome email template for new leads"
} | ConvertTo-Json
$resp1 = Invoke-RestMethod -Uri "$baseUrl/templates/" -Method POST -Body $template1 -ContentType "application/json"
Write-Host "응답: $($resp1 | ConvertTo-Json -Depth 5)" -ForegroundColor Green
$templateId = $resp1.data.id

# 2. Template Version 생성 (v1)
Write-Host "`n[2] POST /templates/{id}/versions/ - Version 1 생성" -ForegroundColor Yellow
$version1 = @{
    subject_tpl = "Hello {{first_name}}!"
    body_tpl = "Welcome, {{first_name}} {{last_name}}!`n`nWe're glad to contact you at {{email}}."
    format = "text"
    cta_type = "none"
    personalization_level = "medium"
} | ConvertTo-Json
$resp2 = Invoke-RestMethod -Uri "$baseUrl/templates/$templateId/versions/" -Method POST -Body $version1 -ContentType "application/json"
Write-Host "응답: $($resp2 | ConvertTo-Json -Depth 5)" -ForegroundColor Green
$versionId1 = $resp2.data.id

# 3. Template Version 생성 (v2) - 자동 버전 증가 테스트
Write-Host "`n[3] POST /templates/{id}/versions/ - Version 2 생성 (자동 증가)" -ForegroundColor Yellow
$version2 = @{
    subject_tpl = "{{first_name}}, Special Offer!"
    body_tpl = "<h1>Hello {{first_name}}!</h1><p>{{company}} has a special offer for you.</p>"
    format = "html"
    cta_type = "button"
    personalization_level = "high"
} | ConvertTo-Json
$resp3 = Invoke-RestMethod -Uri "$baseUrl/templates/$templateId/versions/" -Method POST -Body $version2 -ContentType "application/json"
Write-Host "응답: $($resp3 | ConvertTo-Json -Depth 5)" -ForegroundColor Green
Write-Host "버전 번호 자동 증가 확인: $($resp3.data.version_number)" -ForegroundColor Magenta
$versionId2 = $resp3.data.id

# 4. Template 목록 조회 (버전 포함)
Write-Host "`n[4] GET /templates/ - Template 목록 조회" -ForegroundColor Yellow
$resp4 = Invoke-RestMethod -Uri "$baseUrl/templates/" -Method GET
Write-Host "응답: $($resp4 | ConvertTo-Json -Depth 5)" -ForegroundColor Green
Write-Host "latest_version: $($resp4.results[0].latest_version)" -ForegroundColor Magenta
Write-Host "version_count: $($resp4.results[0].version_count)" -ForegroundColor Magenta

# 5. Render Preview (Lead ID 사용)
Write-Host "`n[5] POST /template-versions/{id}/render-preview/ - Lead ID로 렌더링" -ForegroundColor Yellow
$renderLeadId = @{
    lead_id = 1
} | ConvertTo-Json
$resp5 = Invoke-RestMethod -Uri "$baseUrl/template-versions/$versionId2/render-preview/" -Method POST -Body $renderLeadId -ContentType "application/json"
Write-Host "응답: $($resp5 | ConvertTo-Json -Depth 5)" -ForegroundColor Green

# 6. Render Preview (Sample Data 사용)
Write-Host "`n[6] POST /template-versions/{id}/render-preview/ - Sample Data로 렌더링" -ForegroundColor Yellow
$renderSampleData = @{
    sample_data = @{
        first_name = "Test"
        last_name = "User"
        email = "test@example.com"
        company = "Test Company Inc"
    }
} | ConvertTo-Json -Depth 3
$resp6 = Invoke-RestMethod -Uri "$baseUrl/template-versions/$versionId2/render-preview/" -Method POST -Body $renderSampleData -ContentType "application/json"
Write-Host "응답: $($resp6 | ConvertTo-Json -Depth 5)" -ForegroundColor Green

# 7. Template Syntax 에러 테스트
Write-Host "`n[7] Template Syntax 에러 테스트" -ForegroundColor Yellow
$versionError = @{
    subject_tpl = "Invalid template {{first_name"
    body_tpl = "Test"
    format = "text"
} | ConvertTo-Json
try {
    $respError = Invoke-RestMethod -Uri "$baseUrl/templates/$templateId/versions/" -Method POST -Body $versionError -ContentType "application/json"
} catch {
    Write-Host "에러 응답 (예상됨): $($_.Exception.Message)" -ForegroundColor Red
}

# 8. Undefined Variable 에러 테스트
Write-Host "`n[8] Undefined Variable 에러 테스트" -ForegroundColor Yellow
$versionUndef = @{
    subject_tpl = "Hello {{nonexistent_variable}}"
    body_tpl = "Test"
    format = "text"
} | ConvertTo-Json
$resp8 = Invoke-RestMethod -Uri "$baseUrl/templates/$templateId/versions/" -Method POST -Body $versionUndef -ContentType "application/json"
$versionIdUndef = $resp8.data.id

$renderUndef = @{
    sample_data = @{
        first_name = "Test"
    }
} | ConvertTo-Json -Depth 3
try {
    $respUndef = Invoke-RestMethod -Uri "$baseUrl/template-versions/$versionIdUndef/render-preview/" -Method POST -Body $renderUndef -ContentType "application/json"
} catch {
    Write-Host "에러 응답 (예상됨): $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n=== Stage 3 테스트 완료 ===" -ForegroundColor Cyan
