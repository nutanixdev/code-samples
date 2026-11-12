#Requires -Version 7.0

using namespace Nutanix.OpsmgmtSDK.Model.Opsmgmt.V4.Config

# Create a Prism Central report configuration using the Nutanix v4 PowerShell cmdlets.
# The report charts average VM CPU usage and is emailed to one recipient as a PDF.
# PowerShell equivalent of generate_report_config.py (v4 Python SDK).
# Requires PowerShell 7 or later.
#
# Usage: ./generate_report_config.ps1 -pc_ip <prism_central_ip> -username <prism_central_username>
# The script prompts for the password.

param(
    [Parameter(Mandatory)] [string] $pc_ip,      # Prism Central IP address or FQDN
    [Parameter(Mandatory)] [string] $username    # Prism Central username
)

$ErrorActionPreference = "Stop"

# install the Nutanix Opsmgmt module the first time the script runs
# Nutanix.Opsmgmt manages report configurations; it is currently a pre-release module
if (-not (Get-Module -ListAvailable -Name Nutanix.Opsmgmt)) {
    Install-Module -Name Nutanix.Opsmgmt -Scope CurrentUser -AllowPrerelease -Force
}

# the module must be imported before its cmdlets can be used
Import-Module Nutanix.Opsmgmt

# prompt for the password; it is never stored in the script
$Credential = Get-Credential -UserName $username -Message "Prism Central credentials"

# connect to Prism Central; one call covers every Nutanix module in this session
# Set-PrismCentralConfig has no -Credential parameter, so pass the
# credential's username and password separately
# -SkipCertificateCheck allows self-signed certificates; remove it if
# your Prism Central uses a trusted certificate
Set-PrismCentralConfig -Host $pc_ip -Port 443 -Username $Credential.UserName -Password $Credential.Password -SkipCertificateCheck

# ask for the schedule start and end times, with sensible defaults
$DefaultStart = "2025-01-01T00:00:00Z"
$DefaultEnd   = "2025-01-02T00:00:00Z"
Write-Output "Press Enter at each prompt to accept the default value."

$StartTime = Read-Host "Report start time in ISO-8601 format [$DefaultStart]"
if ($StartTime -eq "") { $StartTime = $DefaultStart }

$EndTime = Read-Host "Report end time in ISO-8601 format [$DefaultEnd]"
if ($EndTime -eq "") { $EndTime = $DefaultEnd }

# show how many user-created report configurations already exist
# the API returns at most 100 per page, so keep asking until a page comes back short
# system configurations are removed here, after the page size check has its full count
$PageSize = 100
$Page = 0
$UserConfigs = @()

do {
    $Batch = @(Get-ConfigReportConfigsList -Limit_ $PageSize -Page_ $Page)
    $UserConfigs += @($Batch | Where-Object { -not $_.IsSystemDefined })
    $Page++
} while ($Batch.Count -eq $PageSize)

Write-Output "$($UserConfigs.Count) user-created report configurations found."

$RecipientName  = Read-Host "Report recipient name"
$RecipientEmail = Read-Host "Report recipient email address"

$ConfigName = "ps_report_config_$([guid]::NewGuid())"

Write-Output "Report configuration will be as follows:"
Write-Output "   Configuration name: $ConfigName"
Write-Output "   Start time: $StartTime"
Write-Output "   End time: $EndTime"
Write-Output "   Report interval: Yearly"

# build the report configuration, from the inside out
# note: types such as [WidgetConfig] only become available after the first
# Nutanix.Opsmgmt cmdlet has run (Get-ConfigReportConfigsList, above)

# one widget: a full-width line chart of average VM CPU usage
$WidgetConfig = [WidgetConfig]@{
    Heading      = "VM CPU Usage (%)"
    EntityType   = "VM"
    Type         = "LINECHART"
    Size         = "FULLSPAN"
    Fields       = @(
        [WidgetField]@{
            Label             = "CPU usage"
            Name              = "hypervisor_cpu_usage_ppm"
            AggregateFunction = "AVG"
        }
    )
    DataCriteria = [DataCriteria]@{
        SortColumn = "hypervisor_cpu_usage_ppm"
        SortOrder  = "ASCENDING"
    }
}

# one section, holding one row, holding the widget; the section repeats for each VM
$Section = [Section]@{
    Name           = "First Section"
    Description    = "This is the first section in the report"
    Rows           = @( [Row]@{ Widgets = @( [Widget]::new($WidgetConfig) ) } )
    RepeatCriteria = [RepeatCriteria]@{ EntityType = "VM" }
}

$ReportConfig = [ReportConfig]@{
    Name                     = $ConfigName
    Description              = "report configuration created from v4 PowerShell cmdlets"
    Schedule                 = [ReportSchedule]@{
        ScheduleInterval = "YEARLY"   # DAILY, WEEKLY, MONTHLY or YEARLY
        Frequency        = 1          # run every 1 interval
        StartTime        = $StartTime # required: when the schedule starts
        EndTime          = $EndTime   # optional: when the schedule ends
    }
    Sections                 = @($Section)
    SupportedFormats         = @("PDF")   # PDF or CSV
    Timezone                 = "UTC"
    NotificationPolicy       = [NotificationPolicy]@{
        RecipientFormats = @("PDF")
        EmailSubject     = "Nutanix Prism Central Report"
        EmailBody        = "Nutanix Prism Central Report; this report was generated from a report configuration created using the Nutanix v4 PowerShell cmdlets."
        Recipients       = @(
            [Recipient]@{
                RecipientName = $RecipientName
                EmailAddress  = $RecipientEmail
            }
        )
    }
    DefaultSectionEntityType = "VM"
}

# submit the request; Prism Central returns a task that creates the configuration
Write-Output "Submitting report config creation request ..."
New-ConfigReportConfig -Body $ReportConfig

# remove the stored connection details from this PowerShell session
Clear-NutanixConfig

