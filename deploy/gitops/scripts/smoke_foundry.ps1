param(
  [Parameter(Mandatory = $true)]
  [ValidateSet("dev", "stage", "prod")]
  [string]$Environment
)

$endpointVar = "FOUNDRY_PROJECT_ENDPOINT_$($Environment.ToUpper())"
$apiKeyVar = "FOUNDRY_API_KEY_$($Environment.ToUpper())"

$endpoint = [Environment]::GetEnvironmentVariable($endpointVar)
$apiKey = [Environment]::GetEnvironmentVariable($apiKeyVar)

if ([string]::IsNullOrWhiteSpace($endpoint)) {
  Write-Error ("Missing endpoint variable: {0}" -f $endpointVar)
  exit 1
}

if ([string]::IsNullOrWhiteSpace($apiKey)) {
  Write-Error ("Missing API key variable: {0}" -f $apiKeyVar)
  exit 1
}

try {
  $headers = @{
    "api-key" = $apiKey
  }

  $response = Invoke-WebRequest -Uri $endpoint -Headers $headers -Method GET -MaximumRedirection 0 -TimeoutSec 20 -SkipHttpErrorCheck
  $statusCode = [int]$response.StatusCode

  if ($statusCode -ge 200 -and $statusCode -lt 500) {
    Write-Host ("Foundry endpoint reachable. Status code: {0}" -f $statusCode)
    exit 0
  }

  Write-Error ("Unexpected status code from Foundry endpoint: {0}" -f $statusCode)
  exit 1
} catch {
  Write-Error ("Foundry smoke check failed: {0}" -f $_.Exception.Message)
  exit 1
}
