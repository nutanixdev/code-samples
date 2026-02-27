"""
Use the Nutanix v4 API SDKs to demonstrate VMM template usage
Requires Prism Central 7.5 or later and AOS 7.5 or later
Author: Chris Rasmussen, Senior Technical Marketing Engineer, Nutanix
Date: February 2026
"""

import datetime
import uuid
import sys
from pprint import pprint
import urllib3
from base64 import b64encode
from rich import print

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import ntnx_clustermgmt_py_client
from ntnx_clustermgmt_py_client import Configuration as ClusterConfiguration
from ntnx_clustermgmt_py_client import ApiClient as ClusterClient
from ntnx_clustermgmt_py_client.rest import ApiException as ClusterException

import ntnx_networking_py_client
from ntnx_networking_py_client import Configuration as NetworkingConfiguration
from ntnx_networking_py_client import ApiClient as NetworkingClient
from ntnx_networking_py_client.rest import ApiException as NetworkingException

import ntnx_vmm_py_client
from ntnx_vmm_py_client import Configuration as VMMConfiguration
from ntnx_vmm_py_client import ApiClient as VMMClient
from ntnx_vmm_py_client.rest import ApiException as VMMException

from ntnx_vmm_py_client import TemplatesApi, TemplateDeployment, VmConfigOverride, GuestCustomizationParams, CloudInit, Userdata, CloudInitDataSourceType
from ntnx_vmm_py_client.models.vmm.v4.ahv.config.Nic import Nic
from ntnx_vmm_py_client.models.vmm.v4.ahv.config.NicNetworkInfo import NicNetworkInfo
from ntnx_vmm_py_client.models.vmm.v4.ahv.config.NicType import NicType
from ntnx_vmm_py_client.models.vmm.v4.ahv.config.SubnetReference import SubnetReference

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

        print("Collecting environment details ...")

        vmm_config = VMMConfiguration()
        cluster_config = ClusterConfiguration()
        networking_config = NetworkingConfiguration()

        for config in [
            vmm_config,
            cluster_config,
            networking_config,
        ]:
            config.host = script_config.pc_ip
            config.username = script_config.pc_username
            config.password = script_config.pc_password
            config.verify_ssl = False

        vmm_client = VMMClient(configuration=vmm_config)
        cluster_client = ClusterClient(configuration=cluster_config)
        networking_client = NetworkingClient(configuration=networking_config)

        for client in [
            vmm_client,
            cluster_client,
            networking_client,
        ]:
            client.add_default_header(
                header_name="Accept-Encoding", header_value="gzip, deflate, br"
            )

        networking_instance = ntnx_networking_py_client.api.SubnetsApi(api_client=networking_client)
        cluster_instance = ntnx_clustermgmt_py_client.api.ClustersApi(api_client=cluster_client)
        vmm_instance = ntnx_vmm_py_client.api.TemplatesApi(api_client=vmm_client)

        # get a list of registered Prism Element (AOS) clusters
        clusters_list = cluster_instance.list_clusters(
            async_req=False,
            _filter="config/clusterFunction/any(a:a eq Clustermgmt.Config.ClusterFunctionRef'AOS')"
        )

        # get a filtered list of existing subnets
        subnets_list = networking_instance.list_subnets(async_req=False, _limit=1, _filter="name eq 'UVM'")

        print("This script is for demo purposes only and has found the following environment details.")
        print(f"    First cluster name: {clusters_list.data[0].name}")
        print(f"    First subnet name: {subnets_list.data[0].name}")
        confirm_continue = utils.confirm(f"    Continue demo using these details?")

        if confirm_continue:
            print("Continuing ...")
        else:
            print("Exiting ...")
            sys.exit()

        # change the template name as necessary for your environment
        templates_list = vmm_instance.list_templates(
            async_req=False, _limit=1, _filter="templateName eq 'cr-template'"
        )

        # make sure a matching template was found
        if not templates_list.data:
            print("No matching templates found.  Exiting ...")
            sys.exit()
        else:
            print("Matching template found.  Continuing ...")

        # get template ext_id
        template_extid = templates_list.data[0].ext_id

        print(f"Template extID: {template_extid}")

        # get template versions and template version ext_id
        template_versions = vmm_instance.list_template_versions(template_extid)
        template_version_extid = template_versions.data[0].ext_id
        print(f"Template version extID: {template_version_extid}")

        # read the CloudInit userdata from the on-disk file
        print(f"Preparing CloudInit userdata ...")
        with open("userdata_simple.yaml", "r", encoding="ascii") as userdata_file:
            userdata_encoded = b64encode(
                bytes(userdata_file.read(), encoding="ascii")
            ).decode("ascii")

        random_uuid = uuid.uuid1()

        # setup the instace of the template deployment details
        # this will be passed to the template deployment request shortly
        print(f"Building deployment configuration ...")
        template_deployment = TemplateDeployment(
            version_id=template_version_extid,
            number_of_vms=1,
            cluster_reference=clusters_list.data[0].ext_id,
            override_vm_config_map={0: VmConfigOverride(
                    name=f"vm_from_template_{random_uuid}",
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
        print("VM deployment from template starting ...")
        deployment = vmm_instance.deploy_template(
            async_req=False,
            body=template_deployment,
            extId=template_extid
        )

        task_extid = deployment.data.ext_id
        utils.monitor_task(
            task_ext_id=task_extid,
            task_name="VM deployment from template",
            pc_ip=script_config.pc_ip,
            username=script_config.pc_username,
            password=script_config.pc_password,
            prefix="",
        )

        print("VM deployment from template completed.  Check Prism Central for detailed task info.")

    except (VMMException, NetworkingException, ClusterException) as ex:
        print(
            f"Unable to authenticate using the supplied credentials.  \
Check your username and/or password, then try again.  \
Exception details: {ex}"
        )

if __name__ == "__main__":
    main()
