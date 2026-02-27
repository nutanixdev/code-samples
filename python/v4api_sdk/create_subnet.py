"""
Use the Nutanix v4 Python SDK to create a Prism Central managed subnet
Requires Prism Central 7.5 or later and AOS 7.5 or later
Author: Chris Rasmussen, Senior Technical Marketing Engineer, Nutanix
Date: February 2026
"""

# disable pylint checks that don't matter for this demo
# pylint: disable=W0105, R0914, R0915;

import getpass
import argparse
import sys
import json
import os
from pprint import pprint
import urllib3
from rich import print

import ntnx_networking_py_client
from ntnx_networking_py_client import Configuration as NetworkingConfiguration
from ntnx_networking_py_client import ApiClient as NetworkingClient
from ntnx_networking_py_client.rest import ApiException as NetworkingException

# alias the v1 common and v4 networking classes
# this is for demo purposes only and should be considered
# before using in a production script
import ntnx_networking_py_client.models.common.v1.config as v1CommonConfig
import ntnx_networking_py_client.models.networking.v4.config as v4NetConfig

import ntnx_clustermgmt_py_client
from ntnx_clustermgmt_py_client import Configuration as ClusterConfiguration
from ntnx_clustermgmt_py_client import ApiClient as ClusterClient
from ntnx_clustermgmt_py_client.rest import ApiException as ClusterException

import ntnx_prism_py_client
from ntnx_prism_py_client import Configuration as PrismConfiguration
from ntnx_prism_py_client import ApiClient as PrismClient
from ntnx_prism_py_client.rest import ApiException as PrismException

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

    subnet_config = "subnet_config.json"

    # load the configuration
    print(f"Loading subnet configuration from {subnet_config} ...")
    try:
        if os.path.exists(subnet_config):
            with open(subnet_config, "r", encoding="utf-8") as config_file:
                config_json = json.loads(config_file.read())
                print("Subnet configuration loaded successfully.")
        else:
            print(f"Configuration file {subnet_config} not found.")
            sys.exit()
    except json.decoder.JSONDecodeError as config_error:
        print(f"Unable to load configuration: {config_error}")
        sys.exit()

    networking_config = NetworkingConfiguration()
    cluster_config = ClusterConfiguration()
    prism_config = PrismConfiguration()

    for config in [networking_config, cluster_config, prism_config]:
        config.host = script_config.pc_ip
        config.username = script_config.pc_username
        config.password = script_config.pc_password
        config.verify_ssl = False

    networking_client = NetworkingClient(configuration=networking_config)
    cluster_client = ClusterClient(configuration=cluster_config)
    prism_client = PrismClient(configuration=prism_config)

    for client in [networking_client, cluster_client, prism_client]:
        client.add_default_header(
            header_name="Accept-Encoding", header_value="gzip, deflate, br"
        )

    # create the API class instances
    networking_instance = ntnx_networking_py_client.api.SubnetsApi(api_client=networking_client)
    cluster_instance = ntnx_clustermgmt_py_client.api.ClustersApi(api_client=cluster_client)
    prism_instance = ntnx_prism_py_client.api.TasksApi(api_client=prism_client)

    # get list of existing clusters
    """
    cluster_list = cluster_instance.list_clusters(
        async_req=False
    )
    """
    cluster_list = cluster_instance.list_clusters(async_req=False)

    # list the clusters for the user to choose from
    cluster_ext_id_list = []
    for cluster in cluster_list.data:
        print(f"Cluster name: {cluster.name}, ext_id: {cluster.ext_id}")
        cluster_ext_id_list.append(cluster.ext_id)

    # get the cluster ID from the user
    cluster_ext_id = input(
        "\nEnter the ext_id for your cluster: "
    )

    # configure the new subnet's specifications
    # these specs are based on those loaded from the command-line JSON file
    try:
        try:
            new_subnet = v4NetConfig.Subnet.Subnet(
                name=config_json["name"],
                description=config_json["description"],
                cluster_reference=cluster_ext_id,
                subnet_type=v4NetConfig.SubnetType.SubnetType.VLAN,
                network_id=config_json["network_id"],
                virtual_switch_reference=config_json["virtual_switch_reference"],
                is_external=config_json["is_external"],
                is_advanced_networking=config_json["is_advanced_networking"],
                dhcp_options=v4NetConfig.DhcpOptions.DhcpOptions(
                    domain_name_servers=[
                        v1CommonConfig.IPAddress.IPAddress(
                            ipv4=v1CommonConfig.IPv4Address.IPv4Address(
                                prefix_length=config_json["dhcp"]["dns_servers"][0][
                                    "prefix_length"
                                ],
                                value=config_json["dhcp"]["dns_servers"][0][
                                    "ip_address"
                                ],
                            )
                        ),
                        v1CommonConfig.IPAddress.IPAddress(
                            ipv4=v1CommonConfig.IPv4Address.IPv4Address(
                                prefix_length=config_json["dhcp"]["dns_servers"][1][
                                    "prefix_length"
                                ],
                                value=config_json["dhcp"]["dns_servers"][1][
                                    "ip_address"
                                ],
                            )
                        ),
                    ]
                ),
                ip_config=[
                    v4NetConfig.IPConfig.IPConfig(
                        ipv4=v4NetConfig.IPv4Config.IPv4Config(
                            default_gateway_ip=v1CommonConfig.IPv4Address.IPv4Address(
                                prefix_length=config_json["gateway"]["prefix_length"],
                                value=config_json["gateway"]["ip_address"],
                            ),
                            dhcp_server_address=v1CommonConfig.IPv4Address.IPv4Address(
                                prefix_length=config_json["dhcp"]["dhcp_server"][
                                    "prefix_length"
                                ],
                                value=config_json["dhcp"]["dhcp_server"]["ip_address"],
                            ),
                            ip_subnet=v4NetConfig.IPv4Subnet.IPv4Subnet(
                                ip=v1CommonConfig.IPv4Address.IPv4Address(
                                    prefix_length=config_json["subnet_ip_prefix"],
                                    value=config_json["subnet_ip_address"],
                                ),
                                prefix_length=config_json["subnet_prefix"],
                            ),
                            pool_list=[
                                v4NetConfig.IPv4Pool.IPv4Pool(
                                    end_ip=v1CommonConfig.IPv4Address.IPv4Address(
                                        prefix_length=config_json["dhcp"]["dhcp_pool"][
                                            "end_ip"
                                        ]["prefix_length"],
                                        value=config_json["dhcp"]["dhcp_pool"][
                                            "end_ip"
                                        ]["ip_address"],
                                    ),
                                    start_ip=v1CommonConfig.IPv4Address.IPv4Address(
                                        prefix_length=config_json["dhcp"]["dhcp_pool"][
                                            "start_ip"
                                        ]["prefix_length"],
                                        value=config_json["dhcp"]["dhcp_pool"][
                                            "start_ip"
                                        ]["ip_address"],
                                    ),
                                )
                            ],
                        )
                    )
                ],
            )
        except AttributeError as ex:
            print("Attribute error while creating new subnet instance.  Details:")
            print(ex)
            sys.exit()
    except KeyError:
        print(
            f"KeyError: {subnet_config} does not contain the required keys.  \
Check the format then try again."
        )
        sys.exit()

    # ask if the user really wants to create the subnet
    confirm_create = utils.confirm(
        "Create subnet?  This will make networking changes in your environment."
    )

    # did the user say Yes to creating the subnet?
    if confirm_create:
        networking_instance = ntnx_networking_py_client.api.SubnetsApi(
            api_client=networking_client
        )

        print("\nCreating Subnet ...")
        create_subnet = networking_instance.create_subnet(
            async_req=False, body=new_subnet
        )

        task_extid = create_subnet.data.ext_id
        utils.monitor_task(
            task_ext_id=task_extid,
            task_name="Subnet create",
            pc_ip=script_config.pc_ip,
            username=script_config.pc_username,
            password=script_config.pc_password,
            poll_timeout=1,
            prefix="",
        )
        print(f"New Subnet named {config_json['name']} has been created.\n")
    else:
        print("Subnet creation cancelled.")


if __name__ == "__main__":
    main()
