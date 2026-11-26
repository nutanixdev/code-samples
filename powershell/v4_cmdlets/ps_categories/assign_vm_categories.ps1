# Nutanix Code Samples
#
# PowerShell script to demonstrate basic usage of the Nutanix PowerShell cmdlets for the v4 APIs
#
# This specific script looks up a category by key and value, then assigns it to a VM with a specified name
#
# Requirements:
#   - PowerShell 7 or later
#   - The Nutanix.Prism and Nutanix.Vmm modules, for example:
#     Install-Module -Name Nutanix.Prism,Nutanix.Vmm -Scope CurrentUser
#
# Before running:
#   - Change $VmName below to the name of a VM that exists in your Prism Central;
#     the value in this script is an example only and will not exist in your environment
#   - The VM name must be unique in your Prism Central
#   - The category passed with -cat_key and -cat_value must already exist in your Prism Central
#
# Usage:
#   ./assign_vm_categories.ps1 -pc_ip <pc_ip_or_fqdn> -username <username> -cat_key <category_key> -cat_value <category_value>
#
# Example:
#   ./assign_vm_categories.ps1 -pc_ip 10.0.0.1 -username admin -cat_key Environment -cat_value Production

param(
    [Parameter(Mandatory)] [string] $pc_ip,
    [Parameter(Mandatory)] [string] $username,
    [Parameter(Mandatory)] [string] $cat_key,
    [Parameter(Mandatory)] [string] $cat_value
)

# the VM that will have the category assigned
# CHANGE THIS: example value only; replace it with the name of an existing VM
$VmName = "cr-ubuntu-lcm-download-server"

Import-Module Nutanix.Prism
Import-Module Nutanix.Vmm

# prompt for the password; it is never stored in the script
$Credential = Get-Credential -UserName $username -Message "Prism Central credentials"

# -SkipCertificateCheck allows self-signed certificates; remove it if
# your Prism Central uses a trusted certificate
Set-PrismCentralConfig -Host $pc_ip -Username $Credential.UserName -Password $Credential.Password -SkipCertificateCheck

# look up the category by key and value to get its ExtId
Write-Host "Looking up category $($cat_key):$($cat_value)"
$Category = Get-ConfigCategoriesList -Filter_ "key eq '$cat_key' and value eq '$cat_value'"
if (-not $Category) {
    throw "No category found with key '$cat_key' and value '$cat_value'"
}
Write-Host "Found category $($cat_key):$($cat_value) with ExtId $($Category.ExtId)"

# look up the VM by name to get its ExtId; VM names are not guaranteed to be
# unique, so stop unless exactly one VM matches
Write-Host "Looking up VM $VmName"
$Vms = @(Get-AhvConfigVmsList -Filter_ "name eq '$VmName'")
if ($Vms.Count -ne 1) {
    throw "Expected exactly 1 VM named '$VmName', found $($Vms.Count)"
}
$VmExtId = $Vms[0].ExtId
Write-Host "Found VM $VmName with ExtId $VmExtId"

# build the list of categories to associate
$Categories = [System.Collections.Generic.List[Nutanix.VmmSDK.Model.Vmm.V4.Ahv.Config.CategoryReference]]::new()
$Categories.Add([Nutanix.VmmSDK.Model.Vmm.V4.Ahv.Config.CategoryReference]::new($Category.ExtId))
$Body = [Nutanix.VmmSDK.Model.Vmm.V4.Ahv.Config.AssociateVmCategoriesParams]::new($Categories)

# the VM's current ETag guards against overwriting a concurrent change
$ETag = Get-AhvConfigVmById -ExtId $VmExtId -EtagOnly

Write-Host "Assigning category $($cat_key):$($cat_value) to VM $VmName ($VmExtId)"
Invoke-AhvConfigAssociateCategories -ExtId $VmExtId -Body $Body -ETag $ETag
Write-Host "Category assignment submitted for VM $VmName"
