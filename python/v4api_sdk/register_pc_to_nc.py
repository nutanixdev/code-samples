"""
Use the Nutanix v4 API SDKs to register a Prism Central
domain to Nutanix Central
Requires Prism Central 7.5.1 or later, AOS 7.5.1
or later and Nutanix Central 2.0 or later
Author: Chris Rasmussen, Senior Technical Marketing Engineer, Nutanix
Date: June 2026
"""

import getpass
import sys
import json
import time
from base64 import b64encode
import urllib3
import requests
from rich import print  # pylint: disable=redefined-builtin

from ntnx_iam_py_client import Configuration as IamConfiguration
from ntnx_iam_py_client import ApiClient as IamClient
from ntnx_iam_py_client.rest import ApiException as IAMException

from ntnx_iam_py_client import (
    DirectoryServicesApi
)

from ntnx_prism_py_client import Configuration as PrismConfiguration
from ntnx_prism_py_client import ApiClient as PrismClient
from ntnx_prism_py_client.rest import ApiException as PrismException

from ntnx_prism_py_client import (
    TasksApi
)

from ntnx_clustermgmt_py_client import Configuration as ClusterConfiguration
from ntnx_clustermgmt_py_client import ApiClient as ClusterClient
from ntnx_clustermgmt_py_client.rest import ApiException as ClusterException

from ntnx_clustermgmt_py_client import (
    ClustersApi
)

from ntnx_multidomain_py_client import Configuration as MDConfiguration
from ntnx_multidomain_py_client import ApiClient as MDClient
from ntnx_multidomain_py_client.rest import ApiException as MDException

from ntnx_multidomain_py_client import (
    LocationsApi,
    RegisteredDomain,
    RegisteredDomainsApi,
    LocalDomainApi,
    LocalDomainRegistrationSpec,
    RegistrationCredentials
)

# small library that manages commonly-used tasks across these code samples
from tme.utils import Utils


def main():  # pylint: disable=too-many-locals too-many-statements too-many-branches # noqa: E501

    """
    suppress warnings about insecure connections
    consider the security implications before
    doing this in a production environment
    """
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    utils = Utils()
    script_config = utils.get_environment()

    try:

        # prompt for environment-specific details
        print("Loading environment details from register_pc_to_nc.json ...")
        try:
            with open(
                     "./register_pc_to_nc.json",
                     "r",
                     encoding="utf-8"
                     ) as config_file:
                env_config = json.loads(config_file.read())
                print("Environment details [bold green]loaded \
successfully[/bold green].")
        except FileNotFoundError:
            print("register_pc_to_nc.json not found. Exiting ...")
            sys.exit()
        except PermissionError:
            print("register_pc_to_nc.json found but \
[bold red]cannot be opened[/bold red]; check \
permissions? Exiting ...")
            sys.exit()

        print("\nThe following configuration will be used for this demo.")
        print(f"    NC FQDN: {env_config['nc_fqdn']}")
        print(f"    NC username: {env_config['nc_username']}")
        print(f"    Identity Provider name: {env_config['idp_name']}")
        print("    Location: New York City, New York\n")

        # create the configuration instances
        iam_config = IamConfiguration()
        cluster_config = ClusterConfiguration()
        prism_config = PrismConfiguration()
        md_config = MDConfiguration()

        # create configuration instances for IAM and ClusterMgmt
        # note these use the PC endpoint and credentials
        for config in [iam_config, cluster_config, prism_config]:
            config.host = script_config.pc_ip
            config.port = "9440"
            config.username = script_config.pc_username
            config.password = script_config.pc_password
            config.verify_ssl = False

        # get the password for the supplied NC username
        nc_password = getpass.getpass(prompt=f"Enter the Nutanix \
Central password for {env_config['nc_username']}: ", stream=None)

        # create configuration instances for MultiDomain
        # note this uses the NC endpoint and credentials
        md_config.host = env_config["nc_fqdn"]
        md_config.port = "443"
        md_config.username = env_config["nc_username"]
        md_config.password = nc_password
        md_config.verify_ssl = False

        # create the instance of the ApiClient classes
        iam_client = IamClient(configuration=iam_config)
        cluster_client = ClusterClient(configuration=cluster_config)
        prism_client = PrismClient(configuration=prism_config)
        md_client = MDClient(configuration=md_config)

        # ask the user if they really want to continue
        confirm_continue = utils.confirm("Continue with PC to \
NC registration process?")
        if not confirm_continue:
            print("PC to NC domain registration cancelled.")
            sys.exit()

        # create the instance of the ClusterMgmt API class
        cluster_instance = ClustersApi(api_client=cluster_client)

        # list PC clusters
        print("Retrieving cluster list ...")
        cluster_list = cluster_instance.list_clusters(
            async_req=False,
            _filter="config/clusterFunction/any(a:a eq Clustermgmt.Config.ClusterFunctionRef'PRISM_CENTRAL')"  # pylint: disable=line-too-long # noqa: E501
        )
        if cluster_list.metadata.total_available_results:
            # get the PC domain's extId
            pc_domain_extid = cluster_list.data[0].ext_id
            print(f"Cluster of type PRISM_CENTRAL found ({pc_domain_extid}).")
        else:
            print(f"[bold red]No clusters of type PRISM_CENTRAL were found.[/bold red]  Exiting ...")
            sys.exit()

        # create the instance of the IAM API class
        iam_instance = DirectoryServicesApi(api_client=iam_client)
        print("Retrieving filtered Identity Provider (IdP) details ...")
        try:
            idp_name_filter = env_config["idp_name"]
        except KeyError:
            print("Required key [bold red]idp_name[/bold red] not found \
in register_pc_to_nc.json; check file contents? \
Exiting ...")
            sys.exit()

        # list matching Identity Providers
        idp_list = iam_instance.list_directory_services(
            async_req=False,
            _filter=f"name eq '{idp_name_filter}'"
        )
        if idp_list.metadata.total_available_results:
            idp_extid = idp_list.data[0].ext_id
            print(f"Identity Provider [bold green]{idp_name_filter}\
[/bold green] found ({idp_extid}).")
        else:
            print(f"Identity Provider [bold red]\
{idp_name_filter}[/bold red] \
not found. Exiting ...")
            sys.exit()

        # build the location list
        md_instance = LocationsApi(api_client=md_client)
        locations_list = md_instance.list_locations(
            _filter="contains(name, 'New York City')"
        )
        if locations_list.metadata.total_available_results:
            location_extid = locations_list.data[0].ext_id
            print(f"Location [bold green]New York City[/bold green] \
found ({location_extid}).")
        else:
            print("Location [bold red]\
New York City[/bold red] \
not found. Exiting ...")
            sys.exit()

        print("Creating registered domain ...")

        # pc_domain_extid = "27191464-8be0-404e-9387-123456789012"

        # build registered domain creation payload
        domain_payload = RegisteredDomain(
            name="demo_domain",
            location_ext_id=location_extid,
            domain_ext_id=pc_domain_extid
        )

        # attempt to create the registered domain
        md_instance = RegisteredDomainsApi(api_client=md_client)
        registered_domain = md_instance.create_registered_domain(
            async_req=False,
            body=domain_payload
        )
        if registered_domain.data.ext_id:
            task_extid = registered_domain.data.ext_id
            print(f"Create registered domain task created \
({task_extid}).")
            timeout = 10
            print(f"Waiting for {timeout} seconds before checking status ...")
            for time_remaining in range(timeout, 0, -1):
                print(time_remaining, end="...", flush=True)
                time.sleep(1)

            # setup REST API request credentials
            encoded_credentials = b64encode(
                bytes(
                    f"{env_config['nc_username']}:{nc_password}",
                    encoding="ascii"
                )
            ).decode("ascii")
            auth_header = f"Basic {encoded_credentials}"

            # setup the REST API request headers
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"{auth_header}",
                "cache-control": "no-cache",
            }

            # get the task details
            # note that this script uses the nutanix-central REST API
            # namespace for this request as this action is not yet
            # supported by the Nutanix v4 SDKs
            task_details_url = f"https://{env_config['nc_fqdn']}\
/api/nutanix-central/v4.0.a1/config/tasks/{task_extid}/status"
            task_details = requests.request(
                "GET",
                task_details_url,
                headers=headers,
                verify=False,  # SSL verification disabled — see security note at top of main()
                timeout=10
            )
            task_details.raise_for_status()
            result = task_details.json()["status"]
            if result == "FAILED":
                result_message = task_details.json()["data"]["subStateInfo"]["errorDetail"]  # pylint: disable=line-too-long # noqa: E501
                print("[bold red]FAILED[/bold red]:")
                print(f"    [bold yellow]{result_message}[/bold yellow]")
                print("    Exiting ...")
                sys.exit()
            else:
                print("[bold green]SUCCESSFUL[/bold green], continuing ...")

        else:
            print("Registered domain could \
be created. Exiting ...")
            sys.exit()

        # attempt to get the newly registered domain
        print("\nChecking creation of registered domain ...")
        new_domain = md_instance.get_registered_domain_by_id(
            pc_domain_extid,
            _select=f"extId = {pc_domain_extid}"
        )
        if new_domain.data:
            print(f"Registered domain named [bold green]\
{new_domain.data.name}[/bold green] found \
({pc_domain_extid}).")
        else:
            print(f"Registered domain {pc_domain_extid} [bold red]\
not found[/bold red]. Exiting ...")
            sys.exit()

        # the domain registration was successful
        target_url = new_domain.data.registration_config.target_url
        api_key = new_domain.data.registration_config.credentials.api_key
        key_id = new_domain.data.registration_config.credentials.key_id
        tenant_extid = new_domain.data.registration_config.tenant_ext_id

        print("Domain details:")
        print(f"    Target URL: {target_url}")
        print(f"    API key: {api_key} ([bold red]DO NOT[/bold red] display this \
on screen in production!)")
        print(f"    API key ID: {key_id}")

        # create configuration instances for MultiDomain
        # note this step uses the PC endpoint and credentials
        for config in [md_config]:
            config.host = script_config.pc_ip
            config.port = "9440"
            config.username = script_config.pc_username
            config.password = script_config.pc_password
            config.verify_ssl = False
        md_client = MDClient(configuration=md_config)
        md_instance = LocalDomainApi(api_client=md_client)

        print("Building PC to NC registration payload ...")
        domain_registration_spec = LocalDomainRegistrationSpec(
            domain_ext_id=pc_domain_extid,
            identity_provider_ext_id=idp_extid,
            target_url=target_url.replace("https://", ""),
            credentials=RegistrationCredentials(
                api_key=api_key,
                key_id=key_id
            ),
            tenant_ext_id=tenant_extid
        )

        # show a summary before the final step
        print("The following payload will be used for the final \
PC to NC registration step:\n")
        print(domain_registration_spec)
        # ask the user if they really want to continue
        confirm_continue = utils.confirm("\nContinue with final step \
of PC to NC registration process? This assumes SSL and DNS \
configuration has been completed as per the Nutanix Central \
deployment documentation.")
        if not confirm_continue:
            print("PC to NC domain registration cancelled.")
            sys.exit()
        else:
            print(f"Registering PC domain {pc_domain_extid} \
to NC at {target_url} ...")

        # do the actual PC to NC registration
        domain_registration = md_instance.register_local_domain(
            async_req=False,
            body=domain_registration_spec
        )

        if domain_registration.data.ext_id:
            task_extid = domain_registration.data.ext_id
            print(f"PC to NC domain registration task created \
({task_extid}).")

            prism_instance = TasksApi(api_client=prism_client)
            registration_task = prism_instance.get_task_by_id(
                task_extid
            )

            print("PC to NC domain registration task [bold yellow]\
RUNNING[/bold yellow] ... ", end="", flush=True)

            while True:
                if registration_task.data.status == "RUNNING":
                    print(
                          f" {registration_task.data.progress_percentage}% ... ",  # pylint: disable=line-too-long # noqa: E501
                          end="",
                          flush=True
                    )
                else:
                    if registration_task.data.status == "SUCCEEDED":
                        message_color = "green"
                    else:
                        message_color = "red"
                    print(f"[bold {message_color}]\
{registration_task.data.status}[/bold {message_color}].")
                    break
                time.sleep(1)
                registration_task = prism_instance.get_task_by_id(task_extid)

        else:
            print("PC to NC local domain registration cannot \
be completed. Exiting ...")
            sys.exit()

    except (IAMException, ClusterException, MDException, PrismException) as ex:
        print(
            f"Error sending request. Exception details:\n    \
{json.loads(ex.body)['data']['error'][0]['message']}"
        )


if __name__ == "__main__":
    main()
