"""
Use the Nutanix v4 API SDKs to get VM stats
Requires Prism Central 2024.3.1 or later and AOS 7.0 or later
Author: Chris Rasmussen, Senior Technical Marketing Engineer, Nutanix
Date: May 2025
"""

# pylint: disable=line-too-long

from datetime import datetime
import sys
import urllib3

from ntnx_vmm_py_client.rest import ApiException as VMMException
from ntnx_vmm_py_client import DownSamplingOperator

# utilities functions and classes e.g. environment management
from tme.utils import Utils

# functions and classes for Prism Central connection management
from tme.apiclient import ApiClient


def main():
    """
    suppress warnings about insecure connections
    please consider the security implications before
    doing this in a production environment
    """
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    utils = Utils()
    config = utils.get_environment()

    try:
        print(utils.printc("SDK", "Collecting environment details ...", "magenta"))  # noqa

        # setup the instance of our ApiClient classes
        # these handle all Prism Central connections and provides
        # access to the chosen namespace's APIs, when required
        # this demo requires the following namespaces:
        # ntnx_vmm_py_client
        vmm_client = ApiClient(config=config, sdk_module="ntnx_vmm_py_client")
        # with the vmm client setup, specify the Nutanix v4 API we want to use
        # this section requires use of the VmApi
        vmm_instance = vmm_client.imported_module.api.VmApi(
            api_client=vmm_client.api_client
        )

        # get a list of VMs, filtered by name
        vm_name = "cr-tools-server-dsl"
        vm_list = vmm_instance.list_vms(async_req=False, _filter=f"name eq '{vm_name}'")  # noqa

        # make sure at least 1 VM was found
        if not vm_list.data:
            print(utils.printc("ERR", "No VMs found.  Exiting ...", "red"))
            sys.exit()
        else:
            print(utils.printc("INFO", "Matching VM found.  Continuing ...", "blue"))  # noqa

        print(
            utils.printc(
                "RESP",
                "This script is for demo purposes only and has found the following VM details.",
                "yellow",
            )
        )  # noqa
        print(f"    VM ext_id: {vm_list.data[0].ext_id}")
        print(f"    VM name: {vm_list.data[0].name}")
        confirm_continue = utils.confirm("    Continue demo using these details?")  # noqa

        if confirm_continue:
            print(utils.printc("INFO", "Continuing ...", "blue"))
        else:
            print(utils.printc("INFO", "Exiting ...", "magenta"))
            sys.exit()

        ext_id = vm_list.data[0].ext_id

        stats_instance = vmm_client.imported_module.api.StatsApi(
            api_client=vmm_client.api_client
        )

        # setup the stats request parameters
        # this example is AEST
        start_time = "2025-05-06T00:00:00.000+10:00"
        end_time = "2025-05-06T00:00:30.000+10:00"

        start_object = datetime.fromisoformat(start_time)
        end_object = datetime.fromisoformat(end_time)

        sampling_interval = 30
        select = "stats/hypervisorCpuUsagePpm,extId"
        stat_type = DownSamplingOperator.AVG

        print(
            utils.printc(
                "INFO",
                "This demo script will use the following start and end times:",
                "blue",
            )
        )
        print(f"    {start_time}")
        print(f"    {end_time}")

        print(utils.printc("INFO", "Retrieving VM stats ...", "blue"))
        stats = stats_instance.get_vm_stats_by_id(
            ext_id,
            _startTime=start_object,
            _endTime=end_object,
            _samplingInterval=sampling_interval,
            _statType=stat_type,
            _select=select,
        )

        print(utils.printc("INFO", "VM stats request completed.", "blue"))
        display_stats = utils.confirm(
            utils.printc(
                "INPUT",
                f"{len(stats.data.stats)} stats objects found.  Display response now?  Note: Stats responses can be very large.",
                "blue",
            )
        )  # noqa

        if display_stats:
            print(stats.data.stats[0].hypervisor_cpu_usage_ppm)

    except VMMException as vmm_exception:
        print(
            f"Unable to authenticate using the supplied credentials.  \
Check your username and/or password, then try again.  \
Exception details: {vmm_exception}"
        )


if __name__ == "__main__":
    main()
