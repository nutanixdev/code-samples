# Nutanix Code Samples
#
# Powershell script to demonstrate basic usage of the Prism REST API v3
# This specific script creates a basic VM similar to the other VM scripts in this repository

# class to hold our request parameters
# this isn't strictly necessary, but makes the management of related-parameters nice and clean
class RequestParameters {
    [string]$cluster_ip
    [string]$uri
    [string]$username
    [string]$password
    [string]$payload
    [string]$method
    [Hashtable]$headers
    [int]$timeout
    [string]$vm_name
}

$parameters = [RequestParameters]::new()

# set the name of the VM that will be created
$parameters.vm_name = "BasicVMViaAPIv3"

# set the basic properties for the request
$parameters.cluster_ip = "10.0.0.1"
$parameters.uri = "https://" + $parameters.cluster_ip + ":9440/api/nutanix/v3/vms"

# the payload for this sample script creates a basic VM named as per the $parameters.vm_name variable
# this shows the bare minimum of parameters required to create a VM
# note the vm doesn't get powered on
$parameters.payload = "{ `
                        ""spec"": { `
                            ""name"":""" + $parameters.vm_name + """, `
                            ""resources"":{ `
                            } `
                            }, `
                            ""metadata"":{ `
                                ""kind"":""vm"" `
                            } `
                       }"

$parameters.method = "POST"

# set a sensible timeout - you may want to increase this
$parameters.timeout = 5

# get the user's credentials
# username will be prompted on the command line/within PowerShell
$parameters.username = Read-Host "Enter cluster username"

# password will prompted using a dialog/popup (because of -AsSecureString)
$secure_password = Read-Host "Enter cluster password" -AsSecureString

# convert the secure string into a format that is usable by ToBase64String below
# be aware that the result of this is a plain text string - handle it appropriately in production
$binary_string = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure_password)
$plain_text_password = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($binary_string)
$parameters.password = $plain_text_password

# create the HTTP Basic Authorization header
$pair = $parameters.username + ":" + $parameters.password
$bytes = [System.Text.Encoding]::ASCII.GetBytes($pair)
$base64 = [System.Convert]::ToBase64String($bytes)
$basicAuthValue = "Basic $base64"

# setup the request headers
$parameters.headers = @{
    'Accept' = 'application/json'
    'Authorization' = $basicAuthValue
    'Content-Type' = 'application/json'
}

# disable SSL certification verification
# you probably shouldn't do this in production ...
if (-not ([System.Management.Automation.PSTypeName]'ServerCertificateValidationCallback').Type)
{
$certCallback = @"
    using System;
    using System.Net;
    using System.Net.Security;
    using System.Security.Cryptography.X509Certificates;
    public class ServerCertificateValidationCallback
    {
        public static void Ignore()
        {
            if(ServicePointManager.ServerCertificateValidationCallback ==null)
            {
                ServicePointManager.ServerCertificateValidationCallback +=
                    delegate
                    (
                        Object obj,
                        X509Certificate certificate,
                        X509Chain chain,
                        SslPolicyErrors errors
                    )
                    {
                        return true;
                    };
            }
        }
    }
"@
    Add-Type $certCallback
 }
[ServerCertificateValidationCallback]::Ignore()
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# handle the exceptions
try {
    # submit the request that has been constructed above
    # note that | Select * is not necessary and can be removed,
    # but does show how you can specify which JSON properties can
    # be extracted later
    Invoke-WebRequest `
        -Uri $parameters.uri `
        -Headers $parameters.headers `
        -Method $parameters.method `
        -Body $parameters.payload `
        -TimeoutSec $parameters.timeout `
        -UseBasicParsing `
        -DisableKeepAlive `
        | ConvertFrom-Json | Select *
}
# e.g. connections timeouts, missing required payload parameters, extra/unexpected payload parameters
catch [System.Net.WebException] {
    Write-Host "An error occurred while processing the API request."
    Write-Host $_
}
# e.g. attempting to use the GET verb on a request that should be POST
catch [System.Net.ProtocolViolationException] {
    Write-Host "A payload/request body error occurred while making the request."
    Write-Host $_
}