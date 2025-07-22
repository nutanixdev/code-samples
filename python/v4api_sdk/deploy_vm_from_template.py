"""
Use the Nutanix v4 API SDKs to demonstrate VMM template usage
Requires Prism Central 2024.3.1 or later and AOS 7.0 or later
"""

import datetime
import uuid
import sys
from pprint import pprint
import urllib3
from base64 import b64encode

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# utilities functions and classes e.g. environment management
from tme.utils import Utils

# functions and classes for Prism Central connection management
from tme.apiclient import ApiClient

from ntnx_vmm_py_client.rest import ApiException as VMMException
from ntnx_clustermgmt_py_client.rest import ApiException as ClusterMgmtException
from ntnx_networking_py_client.rest import ApiException as NetworkingException

from ntnx_vmm_py_client import TemplatesApi, TemplateDeployment, VmConfigOverride, GuestCustomizationParams, CloudInit, Userdata, CloudInitDataSourceType
from ntnx_vmm_py_client.models.vmm.v4.ahv.config.Nic import Nic
from ntnx_vmm_py_client.models.vmm.v4.ahv.config.NicNetworkInfo import NicNetworkInfo
from ntnx_vmm_py_client.models.vmm.v4.ahv.config.NicType import NicType
from ntnx_vmm_py_client.models.vmm.v4.ahv.config.SubnetReference import SubnetReference

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

        print(utils.printc("SDK", "Collecting environment details ...", "magenta"))

        # setup the instance of our ApiClient classes
        # these handle all Prism Central connections and provides
        # access to the chosen namespace's APIs, when required
        # this demo requires the following namespaces:
        # ntnx_vmm_py_client, ntnx_clustermgmt_py_client, ntnx_networking_py_client
        cluster_client  = ApiClient(config=config, sdk_module="ntnx_clustermgmt_py_client")
        # with the cluster client setup, specify the Nutanix v4 API we want to use
        # this section requires use of the ClustersApi
        cluster_instance = cluster_client.imported_module.api.ClustersApi(api_client=cluster_client.api_client)

        # get a list of registered Prism Element clusters
        clusters_list = cluster_instance.list_clusters(async_req=False, _limit=1)

        networking_client = ApiClient(config=config, sdk_module="ntnx_networking_py_client")

        # this section requires use of the SubnetsApi
        networking_instance = networking_client.imported_module.api.SubnetsApi(api_client=networking_client.api_client)

        # get a filtered list of existing subnets
        subnets_list = networking_instance.list_subnets(async_req=False, _limit=1, _filter="name eq 'UVM'")

        print(utils.printc("RESP", "This script is for demo purposes only and has found the following environment details.", "yellow"))
        print(f"    First cluster name: {clusters_list.data[0].name}")
        print(f"    First subnet name: {subnets_list.data[0].name}")
        confirm_continue = utils.confirm(f"    Continue demo using these details?")

        if confirm_continue:
            print(utils.printc("INFO", "Continuing ...", "blue"))
        else:
            print(utils.printc("INFO", "Exiting ...", "magenta"))
            sys.exit()

        vmm_client = ApiClient(config=config, sdk_module="ntnx_vmm_py_client")

        # this section requires use of the TemplatesApi
        templates_instance = vmm_client.imported_module.api.TemplatesApi(
            api_client=vmm_client.api_client
        )

        # change the template name as necessary for your environment
        templates_list = templates_instance.list_templates(
            async_req=False, _limit=1, _filter="templateName eq 'cr-template'"
        )

        # make sure a matching template was found
        if not templates_list.data:
            print(utils.printc("ERR", "No matching templates found.  Exiting ...", "red"))
            sys.exit()
        else:
            print(utils.printc("INFO", "Matching template found.  Continuing ...", "blue"))

        # get template ext_id
        template_extid = templates_list.data[0].ext_id

        print(utils.printc("INFO", f"Template extID: {template_extid}", "blue"))

        # get template versions and template version ext_id
        template_versions = templates_instance.list_template_versions(template_extid)
        template_version_extid = template_versions.data[0].ext_id
        print(utils.printc("INFO", f"Template version extID: {template_version_extid}", "blue"))

        # read the CloudInit userdata from the on-disk file
        print(utils.printc("INFO", f"Preparing CloudInit userdata ...", "blue"))
        with open("userdata_simple.yaml", "r", encoding="ascii") as userdata_file:
            userdata_encoded = b64encode(
                bytes(userdata_file.read(), encoding="ascii")
            ).decode("ascii")

        # setup the instace of the template deployment details
        # this will be passed to the template deployment request shortly
        print(utils.printc("INFO", f"Building deployment configuration ...", "blue"))
        template_deployment = TemplateDeployment(
            version_id=template_version_extid,
            number_of_vms=3,
            cluster_reference=clusters_list.data[0].ext_id,
            override_vm_config_map={0: VmConfigOverride(
                    nics=[
                        Nic(
                            network_info=NicNetworkInfo(
                                nic_type=NicType.NORMAL_NIC,
                                subnet=SubnetReference(
                                    ext_id=subnets_list.data[0].ext_id
                                )
                            )
                        )
                    ],
                    guest_customization=GuestCustomizationParams(
                        config=CloudInit(
                            cloud_init_script=Userdata(value=userdata_encoded)
                        )
                    )
                )
            }
        )

        # send the template deployment request
        print(utils.printc("INFO", "VM deployment from template starting ...", "blue"))
        deployment = templates_instance.deploy_template(async_req=False, body=template_deployment, extId=template_extid)

        task_extid = deployment.data.ext_id
        utils.monitor_task(
            task_ext_id=task_extid,
            task_name=utils.printc("INFO", "VM deployment from template", "blue"),
            pc_ip=config.pc_ip,
            username=config.pc_username,
            password=config.pc_password,
            poll_timeout=1,
            prefix="",
        )

        print(utils.printc("INFO", "VM deployment from template completed.  Check Prism Central for detailed task info.", "blue"))

    except (VMMException, NetworkingException, ClusterMgmtException) as ex:
        print(
            f"Unable to authenticate using the supplied credentials.  \
Check your username and/or password, then try again.  \
Exception details: {ex}"
        )

if __name__ == "__main__":
    main()
