# Code Samples for Nutanix v4 PowerShell Cmdlets

Two sample scripts that use the Nutanix v4 PowerShell Cmdlets (version 1.0.0 and later) to work with Prism Central.

> **Requires PowerShell 7 or later.** Both scripts declare `#Requires -Version 7.0` and will not run in Windows PowerShell 5.1 (`powershell.exe`). Run them from `pwsh`.
>
> **Requires the 1.0.0 Nutanix PowerShell modules** (`Nutanix.Vmm`, `Nutanix.Opsmgmt`). The scripts do not work with the older 2.x Nutanix PowerShell Cmdlets.

| Script | Purpose |
| --- | --- |
| `list_vms_powered_off.ps1` | Lists every AHV VM that is powered off, with its vCPU count, memory and ext ID. |
| `generate_report_config.ps1` | Creates a Prism Central report configuration that charts average VM CPU usage and emails it to one recipient as a PDF. |

## Requirements

- PowerShell 7 or later
- Network access to Prism Central
- A Prism Central account with permission to list VMs and, for the report script, create report configurations

## Installing the Cmdlets

Install the Nutanix modules from the PowerShell Gallery:

```powershell
Install-Module -Name Nutanix.Vmm -Scope CurrentUser
Install-Module -Name Nutanix.Opsmgmt -Scope CurrentUser -AllowPrerelease
```

`Nutanix.Opsmgmt` is currently a pre-release module, so it needs `-AllowPrerelease`.

Each script also checks for the modules it needs and installs any that are missing the first time it runs.

## Running the Scripts

Both scripts have two mandatory parameters:

| Parameter | Description |
| --- | --- |
| `-pc_ip` | Prism Central IP address or FQDN |
| `-username` | Prism Central username |

Run the scripts from a PowerShell 7 session (`pwsh`), not Windows PowerShell (`powershell.exe`). To check your version:

```powershell
$PSVersionTable.PSVersion
```

Neither script stores credentials. Each one prompts for the Prism Central password when it starts. If you leave out a mandatory parameter, PowerShell prompts for it.

### List powered-off VMs

```powershell
./list_vms_powered_off.ps1 -pc_ip 10.0.0.10 -username admin
```

The script prints a table of powered-off VMs sorted by name, followed by the total count.

### Create a report configuration

```powershell
./generate_report_config.ps1 -pc_ip 10.0.0.10 -username admin
```

After you enter the password, the script asks for:

1. **Report start time** in ISO-8601 format (press Enter to accept `2025-01-01T00:00:00Z`)
2. **Report end time** in ISO-8601 format (press Enter to accept `2025-01-02T00:00:00Z`)
3. **Recipient name**
4. **Recipient email address**

It then shows how many user-created report configurations already exist, prints a summary of the new configuration and submits it to Prism Central. The configuration is named `ps_report_config_<guid>` and runs on a yearly schedule.

## Notes

- Both scripts pass `-SkipCertificateCheck` so they work with the self-signed certificate Prism Central uses by default. Remove it from the `Set-PrismCentralConfig` line if your Prism Central has a trusted certificate.
- **Security:** `-SkipCertificateCheck` disables TLS certificate validation, which may increase the risk of the connection being intercepted. Check your organisation's security policies before using it, and consider using a trusted certificate on Prism Central where possible.
- Both scripts run `Clear-NutanixConfig` before exiting, which removes the stored connection details from the PowerShell session.
