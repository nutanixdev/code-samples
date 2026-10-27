#This is a basic test script to update the name and description of a target VM using 
#PowerShell and Nutanix v4 APIs. We are testing using Prism Central 2024.3 and the v4 4.0 VMM endpoints 

#Mandatory: change this variable to match your target Prism Central
$pc_ip = "10.38.94.100"

#Mandatory: change this variable to match existing VM in the Prism Central
$target_vm_name = "original_vm_name"

#Optional: change these variables if needed
$new_name = "renamed_vm_with_v4_APIs"
$new_description = "Updated Description with v4 APIs"

write-host "[ACTION] Starting script to rename VM [$($target_vm_name)] to new name [$($new_name)]" -ForegroundColor cyan
#Prism Central credential 
$pc_cred = Get-Credential -Message "Please enter an account with API access to Prism Central"

#setup default headers
$default_headers = New-Object "System.Collections.Generic.Dictionary[[String],[String]]"
$default_headers.Add("Accept", "application/json")

$default_headers.Add("Content-Type", "application/json")

#convert Prism Central credential to base64 authorization header and add to $default_headers
$var_bytes = [System.Text.Encoding]::UTF8.GetBytes($pc_cred.username + ":" + $pc_cred.GetNetworkCredential().password)
$var_base_64 =[Convert]::ToBase64String($var_bytes)
$default_headers['Authorization'] = "Basic " + $var_base_64

#looping example section using a PowerShell loop to recurse through all pages to pull every VM in 
#a PC and then use where-object to find target VM; this method is not as efficient as the subsequent
#example using filtering but is included for demonstration purposes
$all_vms = @()
$page = 0
#default limit is 25; maximum limit is 100
$limit = 10
$get_vms_url = "https://$($pc_ip):9440/api/vmm/v4.0/ahv/config/vms?`$page=$($page)&`$limit=$($limit)"
$get_vms_response = Invoke-RestMethod $get_vms_url -Method 'GET' -Headers $default_headers -SkipCertificateCheck
if ($get_vms_response.data) {
    $all_vms += $get_vms_response.data 
    $vm_count = $get_vms_response.metadata.totalAvailableResults
    $last_href = ($get_vms_response.metadata.links | where-object {$_.rel -eq 'last'}).href
    $last_page = $last_href.split('$page=')[-1].split('&$limit')[0]    
} else {
    write-host "[ERROR] Failure retrieving VMs from PC [$($pc_ip)]; exiting" -ForegroundColor Red
    exit
}
if ($last_page -gt 0) {    
    for ($cur_page = $page + 1; $cur_page -le $last_page; $cur_page++) {
        $get_vms_url = "https://$($pc_ip):9440/api/vmm/v4.0/ahv/config/vms?`$page=$($cur_page)&`$limit=$($limit)"
        $get_vms_response = Invoke-RestMethod $get_vms_url -Method 'GET' -Headers $default_headers -SkipCertificateCheck
        $all_vms += $get_vms_response.data
    }
} 
#find target VM via where-object
$found_vm_data = $all_vms | where-object {$_.name -eq $target_vm_name}
if ($found_vm_data)
{
    $target_ext_id = $found_vm_data[0].extId
    if ($found_vm_data.count -gt 1) {
        write-host "[WARNING] Found more than one VM with name [$($target_vm_name)] with Ext IDs [$(($found_vm_data.extId -join "," | out-string).trim())]" -ForegroundColor Yellow
    } 
    write-host "[INFO] Found VM [$($target_vm_name)] Ext ID [$($target_ext_id)]" -ForegroundColor green 
} else {   
    write-host "[ERROR] Failed to find VM [$($target_vm_name)]; exiting" -ForegroundColor red
    exit
}
#end looping example section

#filtering example to retrieve target VM using v4 filtering; this is the preferred 
#method as it only requires a single API call and less PowerShell code
write-host "[ACTION] Checking for the existence of VM [$($target_vm_name)] in Prism Central [$($pc_ip)]" -ForegroundColor cyan
$get_filter_url = "https://$($pc_ip):9440/api/vmm/v4.0/ahv/config/vms?`$filter=name eq '$($target_vm_name)'"
$get_filter_response = Invoke-RestMethod $get_filter_url -Method 'GET' -Headers $default_headers -SkipCertificateCheck

if ($get_filter_response.metadata) {
    $filter_vm_count = $get_filter_response.metadata.totalAvailableResults
} else {
    write-host "[ERROR] Failure retrieving VM from PC [$($pc_ip)]; exiting" -ForegroundColor Red
    exit
}

if ($filter_vm_count -gt 0)
{
    $target_ext_id =  $get_filter_response.data[0].extId
    if ($filter_vm_count -gt 1) {
        write-host "[WARNING] Found more than one VM [$($target_vm_name)] with Ext IDs [$(($get_filter_response.data.extId -join "," | out-string).trim())]" -ForegroundColor Yellow
    } 
    write-host "[INFO] Found VM [$($target_vm_name)] Ext ID [$($target_ext_id)]" -ForegroundColor green
} else {   
    write-host "[ERROR] Failed to find VM [$($target_vm_name)]; exiting" -ForegroundColor red
    exit
}
#end filtering example section

<#
#invoke-webrequest section
write-host "[ACTION] Retrieving data for VM with invoke-webrequest with ext ID [$($target_ext_id)]" -ForegroundColor cyan
$web_request_url="https://$($pc_ip):9440/api/vmm/v4.0/ahv/config/vms/$($target_ext_id)"
$web_request_response = Invoke-WebRequest $web_request_url -Method 'GET' -Headers $default_headers -SkipCertificateCheck
$web_request_data = $web_request_response.content | convertfrom-json -depth 99
#end invoke-webrequest section 
#>

#retrieve VM data by ext ID, including ETag
write-host "[ACTION] Retrieving data for VM with ext ID [$($target_ext_id)]" -ForegroundColor cyan
$check_vm_params=@{
    Uri="https://$($pc_ip):9440/api/vmm/v4.0/ahv/config/vms/$($target_ext_id)"
    Method="Get"
    Headers=$default_headers
    SkipCertificateCheck=$true
    ResponseHeadersVariable="resp_headers"
    StatusCodeVariable="status_code"
}
$check_vm_response = Invoke-RestMethod @check_vm_params
$etag = $resp_headers.ETag[0]
#end ETag section

#section to update the VM with a new name and description
#create new spec and save old description to revert
$original_description = $check_vm_response.data.description
$target_spec = $check_vm_response.data
$target_spec.name = $new_name
$target_spec.description = $new_description
$target_json = $target_spec | convertto-json -depth 99

#creates new headers for Put since we need more customization 
write-host "[ACTION] Updating VM [$($target_vm_name)] with a new name and description" -ForegroundColor cyan
$put_headers = $default_headers | ConvertTo-Json -Depth 99 | ConvertFrom-Json -AsHashtable
$put_headers.Add("If-Match", $eTag)
$ntnx_request_id = (New-Guid).guid
$put_headers.Add("NTNX-Request-Id", $ntnx_request_id)
$update_vm_params=@{
    Uri="https://$($pc_ip):9440/api/vmm/v4.0/ahv/config/vms/$($target_ext_id)"
    Method="Put"
    Body=$target_json
    Headers=$put_headers
    SkipCertificateCheck=$true
    SkipHeaderValidation=$true
    ResponseHeadersVariable="resp_headers"
    StatusCodeVariable="status_code"
}
$update_vm_response = Invoke-RestMethod @update_vm_params

if ($update_vm_response.data.extId) {
    $task_extId = $update_vm_response.data.extId
    write-host "[INFO] Name update task started with extId [$($task_extId)]" -ForegroundColor green
} else {
    write-host "[ERROR] Failed to create name update task" -ForegroundColor red
}
#end update section

#sleep to wait for the name update. Alternatively, you could create a loop to query 
#the tasks API to check the status using the $task_extId returned in the last step
start-sleep 10

#rechecking VM data by ext ID, including ETag
write-host "[ACTION] Rechecking data for VM with ext ID [$($target_ext_id)]" -ForegroundColor cyan
$recheck_vm_params=@{
    Uri="https://$($pc_ip):9440/api/vmm/v4.0/ahv/config/vms/$($target_ext_id)"
    Method="Get"
    Headers=$default_headers
    SkipCertificateCheck=$true
    ResponseHeadersVariable="resp_headers"
    StatusCodeVariable="status_code"
}
$recheck_vm_response = Invoke-RestMethod @recheck_vm_params
$new_etag = $resp_headers.ETag[0]

if ($recheck_vm_response.data) {
    $recheck_vm = $recheck_vm_response.data[0]
    If ($recheck_vm.name -eq $new_name -and $recheck_vm.description -eq $new_description) {
        write-host "[INFO] VM name and description updated: $($recheck_vm | select-object name, description | format-table | out-string)" -ForegroundColor Green
        Write-host "Type 'YES' to revert VM back to original name [$($target_vm_name)], or any other key to skip " -Nonewline -foregroundcolor yellow
        $prompt = read-host
        if ($prompt -ne "YES") { 
            write-host "[ACTION] Skipping reverting VM name" -ForegroundColor Cyan 
        }
    } else {
        write-host "[ERROR] Encountered issue updating VM name and description: $($recheck_vm | select-object name, description, extId, updateTime | format-table | out-string)" -ForegroundColor red
    } 
} 
#end rechecking VM section

#section to revert VM name and description back to the original 
if ($prompt -eq 'YES') {
    #revert to original name
    write-host "[ACTION] Reverting VM name [$($new_name)] back to original name [$($target_vm_name)]" -ForegroundColor cyan
    $revert_spec = $recheck_vm_response.data 
    $revert_spec.name = $target_vm_name
    $revert_spec.description = $original_description
    $revert_json = $revert_spec | convertto-json -depth 99

    #creates new headers for Put since we need more customization 
    $revert_headers = $default_headers | ConvertTo-Json -Depth 99 | ConvertFrom-Json -AsHashtable
    $revert_headers.Add("If-Match", $new_etag)
    $revert_request_id = (New-Guid).guid
    $revert_headers.Add("NTNX-Request-Id", $revert_request_id)
    $revert_vm_params=@{
        Uri="https://$($pc_ip):9440/api/vmm/v4.0/ahv/config/vms/$($target_ext_id)"
        Method="Put"
        Body=$revert_json
        Headers=$revert_headers
        SkipCertificateCheck=$true
        SkipHeaderValidation=$true
        ResponseHeadersVariable="resp_headers"
        StatusCodeVariable="status_code"
    }
    $revert_vm_response = Invoke-RestMethod @revert_vm_params
} 
#end section to revert name

write-host "[INFO] Script complete" -ForegroundColor green
