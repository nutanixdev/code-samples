"""
Use the Nutanix v4 Python SDKs to carry out Nutanix Objects Storage operations
Requires Prism Central 7.5 or later and AOS 7.5 or later
Author: Chris Rasmussen, Senior Technical Marketing Engineer, Nutanix
Date: March 2026
"""

import re
import sys
import uuid
from pprint import pprint
import time
import urllib3
from rich import print
import boto3
from botocore.exceptions import ClientError

import ntnx_clustermgmt_py_client
from ntnx_clustermgmt_py_client import Configuration as ClusterConfiguration
from ntnx_clustermgmt_py_client import ApiClient as ClusterClient
from ntnx_clustermgmt_py_client.rest import ApiException as ClusterException

import ntnx_networking_py_client
from ntnx_networking_py_client import Configuration as NetworkingConfiguration
from ntnx_networking_py_client import ApiClient as NetworkingClient
from ntnx_networking_py_client.rest import ApiException as NetworkingException

import ntnx_objects_py_client
from ntnx_objects_py_client import Configuration as ObjectsConfiguration
from ntnx_objects_py_client import ApiClient as ObjectsClient
from ntnx_objects_py_client.rest import ApiException as ObjectsException

from ntnx_objects_py_client.models.objects.v4.config.ObjectStore import ObjectStore
from ntnx_objects_py_client.models.common.v1.config.IPAddress import IPAddress
from ntnx_objects_py_client.models.common.v1.config.IPv4Address import IPv4Address

import ntnx_iam_py_client
from ntnx_iam_py_client import Configuration as IamConfiguration
from ntnx_iam_py_client import ApiClient as IamClient
from ntnx_iam_py_client.rest import ApiException as IamException
from ntnx_iam_py_client.models.iam.v4.authn.User import User
from ntnx_iam_py_client.models.iam.v4.authn.Key import Key
from ntnx_iam_py_client.models.iam.v4.authn.CreationType import CreationType
from ntnx_iam_py_client.models.iam.v4.authn.UserStatusType import UserStatusType
from ntnx_iam_py_client.models.iam.v4.authn.UserType import UserType
from ntnx_iam_py_client.models.iam.v4.authn.KeyKind import KeyKind

# small library that manages commonly-used tasks across these code samples
from tme.utils import Utils


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
        # create the configuration instance
        # this per-namespace class manages all Prism Central connection settings
        cluster_config = ClusterConfiguration()
        objects_config = ObjectsConfiguration()
        networking_config = NetworkingConfiguration()
        iam_config = IamConfiguration()

        for config in [cluster_config, objects_config, networking_config, iam_config]:
            config.host = script_config.pc_ip
            config.port = "9440"
            config.username = script_config.pc_username
            config.password = script_config.pc_password
            config.verify_ssl = False

        # create the instance of the ApiClient class
        cluster_client = ClusterClient(configuration=cluster_config)
        objects_client = ObjectsClient(configuration=objects_config)
        networking_client = NetworkingClient(configuration=networking_config)
        iam_client = IamClient(configuration=iam_config)

        # create the API class instances
        cluster_instance = ntnx_clustermgmt_py_client.api.ClustersApi(
            api_client=cluster_client
        )
        objects_instance = ntnx_objects_py_client.api.ObjectStoresApi(
            api_client=objects_client
        )
        networking_instance = ntnx_networking_py_client.api.SubnetsApi(
            api_client=networking_client
        )
        iam_instance = ntnx_iam_py_client.api.UsersApi(api_client=iam_client)

        print("""\nThis demo will:
    - List all AOS clusters registered to the specified Prism Central instance 
    - List all subnets configured in the selected Prism Element cluster
    - Collect new Object Store and Bucket names from the user
    - Prompt for network details to use during Object Store creation
    - Create a new Object Store based on the specified name
      - Existing Object Stores will be listed to find existing matches
    - Create a new Bucket based on the specified name
      - Existing Buckets will be listed to find existing matches
    - Create a new user of type Service Account for use with the Nutanix Objects Browser
      - Existing user accounts will be listed to find existing matches
      - For existing user accounts, script user will be asked if they want to continue
    - Create a new OBJECT_KEY (API key) and assign it to the new Service Account user\n
""")

        # use an Odata filter to retrieve a list of clusters, filtered by AOS clusters ONLY
        # in the context of this query, the valid cluster function values are 'AOS' and 'PRISM_CENTRAL'
        print("Retrieving cluster list ...")
        cluster_list = cluster_instance.list_clusters(
            async_req=False,
            _filter="config/clusterFunction/any(a:a eq Clustermgmt.Config.ClusterFunctionRef'AOS')",
        )

        # do some verification and make sure the user creates the image on the correct cluster
        found_clusters = []

        for cluster in cluster_list.data:
            found_clusters.append({"name": cluster.name, "ext_id": cluster.ext_id})
        print(
            f"({len(cluster_list.data)}) AOS clusters were found; this does not include Prism Central clusters."
        )
        pprint(found_clusters)
        expected_cluster_name = input(
            "\nEnter the name of the destination cluster: "
        ).lower()

        matches = [
            cluster
            for cluster in found_clusters
            if cluster["name"].lower() == expected_cluster_name.lower()
        ]
        if not matches:
            print(
                f"No cluster found matching the name {expected_cluster_name}.  Exiting."
            )
            sys.exit()

        # get the cluster ext_id
        cluster_ext_id = matches[0]["ext_id"]

        print("\nRetrieving subnet list ...")
        subnets_list = networking_instance.list_subnets(async_req=False)

        found_subnets = []
        for subnet in subnets_list.data:
            found_subnets.append({"name": subnet.name, "ext_id": subnet.ext_id})
        print(f"({len(subnets_list.data)}) subnets were found.")
        pprint(found_subnets)
        print("\nThis demo uses a single subnet for all network services.")
        expected_subnet_name = input(
            "\nEnter the name of the subnet from the list above: "
        ).lower()

        matches = [
            subnet
            for subnet in found_subnets
            if subnet["name"].lower() == expected_subnet_name.lower()
        ]
        if not matches:
            print(
                f"No subnet found matching the name {expected_subnet_name}.  Exiting."
            )
            sys.exit()

        # get the subnet ext_id
        subnet_ext_id = matches[0]["ext_id"]

        # collect details for use in upcoming steps
        store_pattern = r"^(?=.{1,16}$)[A-Za-z](?:[A-Za-z0-9-]*[A-Za-z0-9])?$"
        store_name = ""
        print("Requesting compliant Object Store name ...")
        while not re.search(store_pattern, store_name):
            store_name = input("\nEnter the name of the new Object Store: ")
        print("Object Store name meets requirements, continuing ...")

        bucket_pattern = r"^[a-z][a-z0-9.-]{1,62}[a-z0-9]$"
        bucket_name = ""
        print("Requesting compliant Bucket name ...")
        while not re.search(bucket_pattern, bucket_name):
            bucket_name = input("\nEnter a name for the new bucket: ")
        print("Bucket name meets requirements, continuing ...")

        print(
            "\nAPI keys of type OBJECT_KEY can only be associated with users of type Service Account.  This demo will create a new service account, then create a new API key for the new user.\n"
        )
        service_account_username = input("Enter a name for the Service Account user: ")

        print(f"\nChecking for existing Object Store named {store_name} ...")

        store_list = objects_instance.list_objectstores(
            async_req=False, _filter=f"name eq '{store_name}'"
        )

        if not store_list.metadata.total_available_results == 0:
            print("(1) matching Object Store found, retrieving configuration ...")

            # get the first public IP of the existing store
            # this will be used as the endpoint for the upcoming boto3 operations
            public_ip = store_list.data[0].public_network_ips[0].ipv4.value
            print(f"Object Store's first public IP: {public_ip}")
        else:
            print(
                "(0) matching Object Stores found, continuing with Object Store creation ..."
            )

            storage_vip = input(
                "Enter the storage network's VIP (must be outside the DHCP range): "
            )
            dns_ip = input(
                "Enter the storage network's DNS IP (must be outside the DHCP range): "
            )
            public_ip = input(
                "Enter the public network IP (must be outside the DHCP range): "
            )

            worker_nodes = 1
            domain_name = "msp.cluster.local"
            capacity = 100

            print("\nSummary of new Object Store:")
            print(f"    Name: {store_name}")
            print(f"    Cluster name: {expected_cluster_name}")
            print(f"    Subnet name: {expected_subnet_name}")
            print(f"    Storage VIP: {storage_vip}")
            print(f"    DNS IP: {dns_ip}")
            print(f"    Public IP: {public_ip}")
            print(f"    Domain: {domain_name}")
            print("    Number of Worker Nodes: 1")
            print("    Object Store size: 100GiB")

            create_store = utils.confirm(
                "\nCreate Object Store now?  Note: No input validation is done during the request."
            )

            if create_store:
                # create a new objects store
                # build the payload that will create the new Object Store
                new_store = ObjectStore(
                    name=store_name,
                    description="Object Store created with the Nutanix v4 Python SDK",
                    domain=domain_name,
                    num_worker_nodes=worker_nodes,
                    cluster_ext_id=cluster_ext_id,
                    storage_network_reference=subnet_ext_id,
                    storage_network_vip=IPAddress(
                        ipv4=IPv4Address(
                            prefix_length=32,
                            value=storage_vip,
                        )
                    ),
                    storage_network_dns_ip=IPAddress(
                        ipv4=IPv4Address(prefix_length=32, value=dns_ip)
                    ),
                    public_network_reference=subnet_ext_id,
                    public_network_ips=[
                        IPAddress(ipv4=IPv4Address(prefix_length=32, value=public_ip))
                    ],
                    total_capacity_gi_b=capacity,
                )

                print(f"Creating Objects Store named {new_store.name} ...")
                store_create = objects_instance.create_objectstore(body=new_store)

                # grab the ext ID of the objects store create task
                # this method is a little cumbersome but allows task IDs from
                # different endpoints and APIs to be used with the
                # monitor_task function
                create_ext_id = store_create.data.ext_id
                utils.monitor_task(
                    task_ext_id=create_ext_id,
                    task_name="Create Objects Store",
                    pc_ip=script_config.pc_ip,
                    username=script_config.pc_username,
                    password=script_config.pc_password,
                )
                print("Objects Store created.")
            else:
                print("Objects Store creation cancelled.")

        # do some quick validation to ensure there are no conflicts in upcoming steps
        user_validation = iam_instance.list_users(
            async_req=False,
            _filter=f"username eq '{service_account_username}' and userType eq Iam.Authn.UserType'SERVICE_ACCOUNT'",
        )
        if len(user_validation.data) == 0:
            # create a new user of type service account
            # first, build the payload
            print("Building new Service Account user payload ...")
            service_account = User(
                username=service_account_username,
                email="no-reply@acme.com",
                display_name="Objects User",
                description="Objects user of type Service Account",
                creation_type=CreationType.USERDEFINED,
                status=UserStatusType.ACTIVE,
                user_type=UserType.SERVICE_ACCOUNT,
            )
            # now, create the user
            print("Creating new user of type Service Account ...")
            create_user = iam_instance.create_user(
                async_req=False, body=service_account
            )

            # user extid is required for creating the new user's Objects key
            user_extid = create_user.data.ext_id

        else:
            continue_with_existing_user = utils.confirm(
                f"\n(1) existing users named {service_account_username} found. Continue with this existing user account?"
            )
            if not continue_with_existing_user:
                print("Exiting ...")
                sys.exit()
            else:
                print(
                    f"Continuing with existing user account named {service_account_username} ..."
                )
                print(user_validation)
                user_extid = user_validation.data[0].ext_id

        # build the Objects key payload
        print("Building new Object key payload ...")
        object_key_id = uuid.uuid1()
        key = Key(
            name=f"objects_key_{object_key_id}",
            description="Objects Storage Key",
            key_type=KeyKind.OBJECT_KEY,
        )

        # create the new Objects key
        print(
            f"Creating new user key of type OBJECT_KEY named objects_key_{object_key_id} ..."
        )
        try:
            objects_key = iam_instance.create_user_key(user_extid, key)
        except IamException as ex:
            print("An exception occurred while creating the user's Object key:\n")
            print("Displaying exception details in 5 seconds ...")
            time.sleep(5)
            print(ex)
            sys.exit()

        # make sure the Object key was created
        if objects_key:
            access_key = objects_key.data.key_details.access_key
            secret_key = objects_key.data.key_details.secret_key
            print("Objects Key created:")
            print(f"    Access key: {access_key}")
            print(f"    Secret key: {secret_key}\n")

            # create a new bucket on the new Object Store
            print(f"Creating bucket named {bucket_name} ...")

            # this section uses the AWS boto3 library
            session = boto3.session.Session()

            # setup the s3 session
            # this uses the AWS access and secret keys obtained when
            # the Objects Key was created in previous steps
            s3c = session.client(
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                endpoint_url=f"http://{public_ip}",
                service_name="s3",
                use_ssl=False,
            )

            # attempt to retrieve a bucket matching the entered name
            try:
                s3c.head_bucket(Bucket=bucket_name)
                print(f"A bucket named {bucket_name} already exists, exiting ...")
                sys.exit()
            except ClientError:
                # a bucket matching the supplied name does not exist
                try:
                    print("(0) matching buckets found, attempting to create bucket ...")
                    s3c.create_bucket(Bucket=bucket_name)
                    print(f"Bucket named {bucket_name} created successfully.")
                except Exception as ex:
                    # unhandled exception
                    print("Exception occurred while creating bucket:")
                    print(f"{ex}")
        else:
            print("The Object key could not be created.")

    except (ClusterException, NetworkingException, ObjectsException) as ex:
        print(
            f"Unable to authenticate using the supplied credentials.  \
                        Please check your username and/or password, then try again.  \
                        Exception details: {ex}"
        )


if __name__ == "__main__":
    main()
