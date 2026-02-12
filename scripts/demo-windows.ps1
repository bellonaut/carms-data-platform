# Shim entry point for users looking for a Windows-specific script.
# Delegates to demo.ps1 to keep logic in one place.
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

& "$PSScriptRoot/demo.ps1"
