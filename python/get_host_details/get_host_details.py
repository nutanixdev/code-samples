#!/usr/bin/env python

"""
Script to fetch details regarding CPUs, Memory configuration,
Bios and BMC versions on a host.
This script generates an excel sheet in the current directory of name
host_script_timestamp
"""
from requests.auth import HTTPBasicAuth
from datetime import datetime
from pprint import pprint
import requests
import sys
import json
import time
import xlsxwriter
import urllib3

'''
disable insecure connection warnings
please be advised and aware of the implications of doing this
in a production environment!
'''
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

peVIP = "<cluster_ip>" # Prism Element VIP
baseUrl = "https://" + peVIP + ":9440/PrismGateway/services/rest/v2.0/" # Base Url v2 API
headers = {'ContentType':'application/json'}
user = "admin"
passw = "<password>"
hostObj = "hosts" # endpoint for hosts

# standard get Request
def getRequest(baseUrl, user, passw, obj):
    comUrl = baseUrl + obj + "/"
    r = requests.get(comUrl, auth=(user, passw), verify=False)
    return r.json()

# standard post Request
def postRequest(baseUrl, user, passw, obj, data):
    comUrl = baseUrl + obj + "/"
    print("URL: ", comUrl)
    dumpData = json.dumps(cloneData, separators=(',', ':'))
    print("type", type(dumpData))
    print(dumpData)
    r = requests.post(comUrl, auth=(user, passw), data=dumpData, verify=False)
    return r.status_code


# standard delete request
def deleteRequest(baseUrl, user, passw, obj, uuid):
    comUrl = baseUrl + obj + "/" + uuid
    print("URL: ", comUrl)
    r = requests.delete(comUrl, auth=(user, passw), verify=False)
    return r.status_code


# get a list of host Names and UUIDs
# Return dictionary with name to host Mapping
def getHostNames(hostObj):
    hostData = getRequest(baseUrl, user, passw, hostObj)
    nameUuidDict = {}
    for field in hostData["entities"]:
        nameUuidDict[field["name"]] = field["uuid"]
    return nameUuidDict

# get individual statistics from each host
# hostJson return json data structure for individual host
# required parameters can be extracted from the host Json structure
# returns a dictionary with hostname as the key and metrics as a list of values
def getHostStats(nameUuidDict, hostObj):
    hostStatsDict = {}
    for name, uuid in nameUuidDict.items():
        hostKeyObj = hostObj + "/" + uuid
        hostJson = getRequest(baseUrl, user, passw, hostKeyObj)
        hostStatsDict[name]= [ hostJson["serial"], hostJson["num_cpu_threads"],
        hostJson["num_vms"], hostJson["bios_version"],
        hostJson["bmc_version"], hostJson["memory_capacity_in_bytes"],
        hostJson["hypervisor_full_name"],hostJson["metadata_store_status"]]
    return hostStatsDict


# create an excel sheet of host details in current directory
def printHostStats(hostStatsDict):
    # Create a filename based on current timestamp and initialise worksheet
    now = datetime.now()
    dt_string = now.strftime("%d-%m-%y_%H-%M-%S")
    fileName = "host_report_" + dt_string + ".xlsx"
    print(fileName)
    workbook = xlsxwriter.Workbook(fileName)
    worksheet = workbook.add_worksheet()
    bold = workbook.add_format({'bold': True})

    # Add data headers or titles for the metrics
    worksheet.write('A1', 'Hostname', bold)
    worksheet.write('B1', 'Node Serial', bold)
    worksheet.write('C1', 'CPUs per core', bold)
    worksheet.write('D1', 'No of VMs', bold)
    worksheet.write('E1', 'BIOS Version', bold)
    worksheet.write('F1', 'BMC Version', bold)
    worksheet.write('G1', 'Memory Capacity (bytes)', bold)
    worksheet.write('H1', 'Hypervisor OS', bold)
    worksheet.write('I1', 'Metadata Store', bold)

    # Set starting row and column on worksheet
    row = 1
    col = 0

    # Write data from Host dictionary to the excel sheet
    for name, values in hostStatsDict.items():
        worksheet.write(row, col, name)
        for i, val in enumerate(values):
            worksheet.write(row, col + 1 + i, val)
        row += 1

    workbook.close()

if __name__ == '__main__':
    nameUuidDict = getHostNames(hostObj)
    hostStatsDict = getHostStats(nameUuidDict, hostObj)
    printHostStats(hostStatsDict)