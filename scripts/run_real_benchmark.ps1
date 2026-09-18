param(
    [int]$Attempts = 2,
    [string]$Data = "data/test_cases_v2.json",
    [string]$DatasetVersion = "v2.0.0",
    [string]$RubricVersion = "v1.0.0",
    [string]$Config = "configs/models.json",
    [string]$Judges = "configs/judges.json",
    [int]$CaseOffset = 0,
    [int]$CaseLimit = 0
)

$ErrorActionPreference = "Stop"

if (!(Test-Path -LiteralPath ".env")) {
    throw "Create .env from .env.example and add provider keys before a real run."
}

if (!(Test-Path -LiteralPath $Data)) {
    throw "Dataset not found: $Data"
}

Write-Host "Starting a real benchmark run with $Attempts attempt(s) per case."
Write-Host "Results will be written to a new results/runs directory."

$arguments = @(
    "-m", "src.runner",
    "--config", $Config,
    "--judges", $Judges,
    "--data", $Data,
    "--label", "real",
    "--dataset-version", $DatasetVersion,
    "--rubric-version", $RubricVersion,
    "--attempts", $Attempts,
    "--case-offset", $CaseOffset
)

if ($CaseLimit -gt 0) {
    $arguments += @("--case-limit", $CaseLimit)
}

python @arguments
