param(
  [Parameter(Mandatory = $true)]
  [ValidateSet("dev", "stage", "prod")]
  [string]$Environment
)

$required = @(
  "FOUNDRY_PROJECT_ENDPOINT_$($Environment.ToUpper())",
  "FOUNDRY_API_KEY_$($Environment.ToUpper())",
  "FOUNDRY_PROJECT_REGION_$($Environment.ToUpper())"
)

$missing = @()
foreach ($key in $required) {
  $value = [Environment]::GetEnvironmentVariable($key)
  if ([string]::IsNullOrWhiteSpace($value)) {
    $missing += $key
  }
}

if ($missing.Count -gt 0) {
  Write-Error ("Missing required environment variables: {0}" -f ($missing -join ", "))
  exit 1
}

Write-Host ("All required variables are present for environment '{0}'." -f $Environment)
