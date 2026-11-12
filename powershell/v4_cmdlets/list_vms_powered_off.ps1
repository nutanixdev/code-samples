#Requires -Version 7.0

# List all AHV VMs that are powered off, using the Nutanix v4 PowerShell cmdlets.
# Requires PowerShell 7 or later.
#
# Usage: ./list_vms_powered_off.ps1 -pc_ip <prism_central_ip> -username <prism_central_username>
# The script prompts for the password.

param(
    [Parameter(Mandatory)] [string] $pc_ip,      # Prism Central IP address or FQDN
    [Parameter(Mandatory)] [string] $username    # Prism Central username
)

$ErrorActionPreference = "Stop"

# install the Nutanix VMM module the first time the script runs
if (-not (Get-Module -ListAvailable -Name Nutanix.Vmm)) {
    Install-Module -Name Nutanix.Vmm -Scope CurrentUser -Force
}

# the module must be imported before its cmdlets can be used
Import-Module Nutanix.Vmm

# prompt for the password; it is never stored in the script
$Credential = Get-Credential -UserName $username -Message "Prism Central credentials"

# connect to Prism Central
# Set-PrismCentralConfig has no -Credential parameter, so pass the
# credential's username and password separately
# -SkipCertificateCheck allows self-signed certificates; remove it if
# your Prism Central uses a trusted certificate
Set-PrismCentralConfig -Host $pc_ip -Username $Credential.UserName -Password $Credential.Password -SkipCertificateCheck

# ask Prism Central for powered-off VMs only
# the API returns at most 100 VMs per page, so keep asking until a page comes back short
$Filter = "powerState eq Vmm.Ahv.Config.PowerState'OFF'"
$PageSize = 100
$Page = 0
$PoweredOffVms = @()

do {
    $Batch = @(Get-AhvConfigVmsList -Filter_ $Filter -Limit_ $PageSize -Page_ $Page)
    $PoweredOffVms += $Batch
    $Page++
} while ($Batch.Count -eq $PageSize)

# show the results
$PoweredOffVms |
    Sort-Object Name |
    Format-Table Name, PowerState,
        @{ Label = "vCPUs";      Expression = { $_.NumSockets * $_.NumCoresPerSocket } },
        @{ Label = "Memory GiB"; Expression = { $_.MemorySizeBytes / 1GB } },
        ExtId -AutoSize

Write-Output "Powered-off VMs found: $($PoweredOffVms.Count)"

# remove the stored connection details from this PowerShell session
Clear-NutanixConfig
