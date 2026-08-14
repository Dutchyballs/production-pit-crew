[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("Project", "User")]
    [string]$Scope,
    [string]$ProjectDir,
    [switch]$DryRun,
    [switch]$Force,
    [switch]$Uninstall
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$installerArgs = @("$PSScriptRoot/install_core.py", "--scope", $Scope.ToLowerInvariant())
if ($ProjectDir) { $installerArgs += @("--project-dir", $ProjectDir) }
if ($DryRun) { $installerArgs += "--dry-run" }
if ($Force) { $installerArgs += "--force" }
if ($Uninstall) { $installerArgs += "--uninstall" }

$python = Get-Command py -ErrorAction SilentlyContinue
if ($python) {
    & $python.Source -3 @installerArgs
    exit $LASTEXITCODE
}

$python = Get-Command python -ErrorAction SilentlyContinue
if ($python) {
    & $python.Source @installerArgs
    exit $LASTEXITCODE
}

Write-Error "Production Pit Crew for Codex requires Python 3.11 or newer."
exit 2
