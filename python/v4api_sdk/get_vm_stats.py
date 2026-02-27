"""
Use the Nutanix v4 API SDKs to get VM stats
Requires Prism Central 7.5 or later and AOS 7.5 or later
Author: Chris Rasmussen, Senior Technical Marketing Engineer, Nutanix
Date: February 2026
"""

# pylint: disable=line-too-long

from datetime import datetime, timedelta
import sys
import urllib3
from rich import print

import ntnx_vmm_py_client
from ntnx_vmm_py_client import Configuration as VMMConfiguration
from ntnx_vmm_py_client import ApiClient as VMMClient
from ntnx_vmm_py_client.rest import ApiException as VMMException
from ntnx_vmm_py_client import DownSamplingOperator

# small library that manages commonly-used tasks across these code samples
from tme.utils import Utils
from tme.apiclient import ApiClient


def main():

    """
    suppress warnings about insecure connections
    please consider the security implications before
    doing this in a production environment
    """
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    utils = Utils()
    script_config = utils.get_environment()

    try:
        print("Collecting environment details ...")  # noqa

        vmm_config = VMMConfiguration()

        for config in [
            vmm_config,
        ]:
            config.host = script_config.pc_ip
            config.username = script_config.pc_username
            config.password = script_config.pc_password
            config.verify_ssl = False

        vmm_client = VMMClient(configuration=vmm_config)

        for client in [
            vmm_client,
        ]:
            client.add_default_header(
                header_name="Accept-Encoding", header_value="gzip, deflate, br"
            )

        # with the vmm client setup, specify the Nutanix v4 API we want to use
        # this section requires use of the VmApi
        vmm_instance = ntnx_vmm_py_client.api.VmApi(api_client=vmm_client)

        # get a list of VMs, filtered by name
        vm_name = "cr-AutoAD"
        vm_list = vmm_instance.list_vms(async_req=False, _filter=f"name eq '{vm_name}'")  # noqa

        # make sure at least 1 VM was found
        if not vm_list.data:
            print("No VMs found.  Exiting ...")
            sys.exit()
        else:
            print("Matching VM found.  Continuing ...")  # noqa

        print("This script is for demo purposes only and has found the following VM details.")  # noqa
        print(f"    VM ext_id: {vm_list.data[0].ext_id}")
        print(f"    VM name: {vm_list.data[0].name}")
        confirm_continue = utils.confirm("    Continue demo using these details?")  # noqa

        if confirm_continue:
            print("Continuing ...")
        else:
            print("Exiting ...")
            sys.exit()

        ext_id = vm_list.data[0].ext_id

        vmm_instance = ntnx_vmm_py_client.api.StatsApi(api_client=vmm_client)

        # setup the stats request parameters
        # this example is AEST

        # start time is "now" minus 5 minutes
        # default in this demo is UTC+10 i.e. AEST
        start_time = (datetime.now() - timedelta(minutes=120)).strftime("%Y-%m-%dT%H:%M:%S+10:00")
        # end time is "now"
        end_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+10:00")

        start_object = datetime.fromisoformat(start_time)
        end_object = datetime.fromisoformat(end_time)

        sampling_interval = 30
        select = "stats/hypervisorCpuUsagePpm,extId"
        stat_type = DownSamplingOperator.AVG

        print("This demo script will use the following spec:")
        print(f"    Start time: {start_time}")
        print(f"    End time: {end_time}")
        print("    VM extId will be included in the response")
        print("    120 minute reporting period")
        print("    30 second reporting interval")
        print("    AVG downsampling operator type")

        print("Retrieving VM stats ...")
        stats = vmm_instance.get_vm_stats_by_id(
            ext_id,
            _startTime=start_object,
            _endTime=end_object,
            _samplingInterval=sampling_interval,
            _statType=stat_type,
            _select=select,
        )

        print("VM stats request completed.")

        if stats.data.stats:
            display_stats = utils.confirm(f"{len(stats.data.stats)} stats object(s) found.  Display response now?  Note: Stats responses can be very large.")  # noqa

            if display_stats:
                print(stats.data)
                # example of showing the first hypervisor CPU usage statistic only
                # commented for demo purposes
                # print(stats.data.stats[0].hypervisor_cpu_usage_ppm)
        else:
            print("No VM stats available.  Exiting.")

    except VMMException as vmm_exception:
        print(
            f"Unable to authenticate using the supplied credentials.  \
Check your username and/or password, then try again.  \
Exception details: {vmm_exception}"
        )


if __name__ == "__main__":
    main()
