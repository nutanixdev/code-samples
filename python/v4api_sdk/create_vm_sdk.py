"""
Use the Nutanix v4 Python SDK to create a Prism Central VM
Requires Prism Central pc.2024.1 or later, AOS 6.8 or later
"""

import getpass
import argparse
import sys
import uuid
from base64 import b64encode
import pprint
import urllib3

import ntnx_vmm_py_client
import ntnx_prism_py_client
import ntnx_clustermgmt_py_client
import ntnx_networking_py_client

from ntnx_vmm_py_client import Configuration as VMMConfiguration
from ntnx_vmm_py_client import ApiClient as VMMClient
import ntnx_vmm_py_client.models.vmm.v4.ahv.config as AhvVmConfig

from ntnx_prism_py_client import Configuration as PrismConfiguration
from ntnx_prism_py_client import ApiClient as PrismClient

from ntnx_clustermgmt_py_client import Configuration as ClusterConfiguration
from ntnx_clustermgmt_py_client import ApiClient as ClusterClient

from ntnx_networking_py_client import Configuration as NetworkingConfiguration
from ntnx_networking_py_client import ApiClient as NetworkingClient

from tme.utils import Utils


def confirm_entity(api, client, entity_name: str, exclusions: list) -> str:
    """
    make sure the user is selecting the correct entity
    e.g. the cluster that will own the VM, the image to
    clone the VM's base disk from
    this is moved into a function as the same steps are completed
    multiple times for different entity types
    """
    instance = api(api_client=client)
    print(f"Retrieving {entity_name} list ...")
    offset = 0
    if entity_name == "cluster":
        entities = instance.list_clusters(async_req=False)
        offset = 1
    elif entity_name == "image":
        entities = instance.list_images(async_req=False)
    elif entity_name == "subnet":
        entities = instance.list_subnets(async_req=False)
    else:
        print(f"{entity_name} is not supported.  Exiting.")
        sys.exit()

    # do some verification and make sure the user selects
    # the correct entity
    found_entities = []
    for entity in entities.data:
        if entity_name in ["subnet", "image"]:
            if entity.name not in exclusions:
                found_entities.append({"name": entity.name, "ext_id": entity.ext_id})
        else:
            if entity.name not in exclusions:
                found_entities.append({"name": entity.name, "ext_id": entity.ext_id})
    print(
        f"The following {entity_name}s ({len(entities.data)-offset}) \
 were found."
    )

    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(found_entities)

    expected_entity_name = input(
        f"\nPlease enter the name of the selected {entity_name}: "
    ).lower()
    matches = [
        x for x in found_entities if x["name"].lower() == expected_entity_name.lower()
    ]
    if not matches:
        print(
            f"No {entity_name} was found matching the name \
 {expected_entity_name}.  Exiting."
        )
        sys.exit()
    # get the entity ext_id
    ext_id = matches[0]["ext_id"]
    return ext_id


def main():
    """
    suppress warnings about insecure connections
    consider the security implications before
    doing this in a production environment
    """
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    """
    setup the command line parameters
    for this example only two parameters are required
    - the Prism Central IP address or FQDN
    - the Prism Central username; the script will prompt for
      the user's password
      so that it never needs to be stored in plain text
    """

    parser = argparse.ArgumentParser()
    parser.add_argument("pc_ip", help="Prism Central IP address or FQDN")
    parser.add_argument("username", help="Prism Central username")
    args = parser.parse_args()

    # get the cluster password
    cluster_password = getpass.getpass(
        prompt="Please enter your Prism Central \
password: ",
        stream=None,
    )

    pc_ip = args.pc_ip
    username = args.username

    # create utils instance for re-use later
    utils = Utils(pc_ip=pc_ip, username=username, password=cluster_password)

    # make sure the user enters a password
    if not cluster_password:
        while not cluster_password:
            print(
                "Password cannot be empty.  Please enter a password \
 or Ctrl-C/Ctrl-D to exit."
            )
            cluster_password = getpass.getpass(
                prompt="Please enter your Prism Central password: ",
                stream=None,
            )

    vmm_config = VMMConfiguration()
    prism_config = PrismConfiguration()
    cluster_config = ClusterConfiguration()
    networking_config = NetworkingConfiguration()

    for config in [
        vmm_config,
        prism_config,
        cluster_config,
        networking_config,
    ]:
        config.host = pc_ip
        config.username = username
        config.password = cluster_password
        config.verify_ssl = False

    vmm_client = VMMClient(configuration=vmm_config)
    prism_client = PrismClient(configuration=prism_config)
    cluster_client = ClusterClient(configuration=cluster_config)
    networking_client = NetworkingClient(configuration=networking_config)

    for client in [
        vmm_client,
        prism_client,
        cluster_client,
        networking_client,
    ]:
        client.add_default_header(
            header_name="Accept-Encoding", header_value="gzip, deflate, br"
        )

    """
    ask the user to confirm the cluster that will own the VM,
    the subnet the VM will connect to and the disk image the VM's
    boot disk will be cloned from
    """
    cluster_ext_id = confirm_entity(
        ntnx_clustermgmt_py_client.api.ClustersApi,
        cluster_client,
        "cluster",
        ["Unnamed"],
    )
    subnet_ext_id = confirm_entity(
        ntnx_networking_py_client.api.SubnetApi, networking_client, "subnet", []
    )
    image_ext_id = confirm_entity(
        ntnx_vmm_py_client.api.ImagesApi, vmm_client, "image", []
    )

    # get the ext_id of the required storage container
    # only request containers with name containing "default-container"
    print("Retrieving storage container list ...")
    print(
        'Note: Containers are filtered to match only those containing \
the text "default".'
    )
    storage_instance = ntnx_clustermgmt_py_client.api.StorageContainersApi(
        api_client=cluster_client
    )
    container_list = storage_instance.list_storage_containers(
        async_req=False, _filter="contains(name, 'default')"
    )

    container_ext_id = container_list.data[0].container_ext_id
    container_name = container_list.data[0].name
    print(
        f'VM will be created on storage container named "{container_name}" \
with ext_id {container_ext_id}.\n'
    )
    print(
        f"VM will be created on container {container_name} with ext_id \
 {container_ext_id}."
    )

    # ask if the user wants to customise the VM using Cloud-Init
    # the Cloud-Init script is only relevant for CentOS Cloud based images
    print(
        "The Cloud-Init script used by this demo has been created for \
CentOS images with Cloud-Init pre-installed.  To use your own \
Cloud-Init userdata, modify userdata.yaml."
    )
    customise_vm = utils.confirm("Customise VM with Cloud-Init?")

    # set the name for the new VM
    # a UUID is appended to make sure each new VM is uniquely named
    vm_name = f"api_v4_sdk-{uuid.uuid4()}"

    # tell the VM which cluster it will live on
    cluster_ref = AhvVmConfig.ClusterReference.ClusterReference()
    cluster_ref.ext_id = cluster_ext_id

    # create a new NIC for the VM
    # https://developers.nutanix.com/api/v1/sdk/namespaces/main/vmm/versions/v4.0.a1/languages/python/ntnx_vmm_py_client.models.vmm.v4.ahv.config.Nic.html#module-ntnx_vmm_py_client.models.vmm.v4.ahv.config.Nic
    vm_nic = AhvVmConfig.Nic.Nic(
        # NIC backing info
        backing_info=AhvVmConfig.EmulatedNic.EmulatedNic(
            # NIC model
            model=AhvVmConfig.EmulatedNicModel.EmulatedNicModel.VIRTIO,
            is_connected=True,
        ),
        # NIC network info including NIC type and subnet details
        network_info=AhvVmConfig.NicNetworkInfo.NicNetworkInfo(
            nic_type=AhvVmConfig.NicType.NicType.NORMAL_NIC,
            # subnet details
            subnet=AhvVmConfig.SubnetReference.SubnetReference(ext_id=subnet_ext_id),
            # IPv4 config e.g. DHCP
            ipv4_config=AhvVmConfig.Ipv4Config.Ipv4Config(should_assign_ip=True),
        ),
    )

    # create an empty CDROM device for the VM
    # https://developers.nutanix.com/api/v1/sdk/namespaces/main/vmm/versions/v4.0.a1/languages/python/ntnx_vmm_py_client.models.vmm.v4.ahv.config.CdRom.html#module-ntnx_vmm_py_client.models.vmm.v4.ahv.config.CdRom
    cdrom = AhvVmConfig.CdRom.CdRom(
        # CDROM address including bus type and index
        disk_address=AhvVmConfig.CdRomAddress.CdRomAddress(
            bus_type=AhvVmConfig.CdRomBusType.CdRomBusType.IDE, index=0
        )
    )

    # create the boot disk for the VM, cloned from an existing on-cluster image
    # https://developers.nutanix.com/api/v1/sdk/namespaces/main/vmm/versions/v4.0.a1/languages/python/ntnx_vmm_py_client.models.vmm.v4.ahv.config.Disk.html#module-ntnx_vmm_py_client.models.vmm.v4.ahv.config.Disk
    cloned_disk = AhvVmConfig.Disk.Disk(
        # backing info e.g. disk type, image info
        backing_info=AhvVmConfig.VmDisk.VmDisk(
            # source info for the cloned disk
            data_source=AhvVmConfig.DataSource.DataSource(
                # clone the disk from an existing image
                reference=AhvVmConfig.ImageReference.ImageReference(
                    image_ext_id=image_ext_id
                )
            )
        ),
        disk_address=AhvVmConfig.DiskAddress.DiskAddress(
            bus_type=AhvVmConfig.DiskBusType.DiskBusType.SCSI, index=0
        ),
    )

    # create an empty 40GB disk attached to the VM
    empty_disk = AhvVmConfig.Disk.Disk(
        backing_info=AhvVmConfig.VmDisk.VmDisk(
            disk_size_bytes=42949672960,
            storage_container=AhvVmConfig.VmDiskContainerReference.VmDiskContainerReference(
                ext_id=container_ext_id
            ),
        ),
        disk_address=AhvVmConfig.DiskAddress.DiskAddress(
            bus_type=AhvVmConfig.DiskBusType.DiskBusType.SCSI, index=1
        ),
    )

    # prepare the VM creation userdata
    with open("userdata.yaml", "r", encoding="ascii") as userdata_file:
        userdata_encoded = b64encode(
            bytes(userdata_file.read(), encoding="ascii")
        ).decode("ascii")

    # create the instance of the VM object
    # and use all the settings created up to this point
    # https://developers.nutanix.com/api/v1/sdk/namespaces/main/vmm/versions/v4.0.a1/languages/python/ntnx_vmm_py_client.models.vmm.v4.ahv.config.Vm.html#module-ntnx_vmm_py_client.models.vmm.v4.ahv.config.Vm
    new_vm = AhvVmConfig.Vm.Vm(
        name=vm_name,
        description="VM created using Nutanix v4 Python SDK",
        num_sockets=1,
        num_cores_per_socket=1,
        is_branding_enabled=True,
        memory_size_bytes=8589934592,
        cluster=cluster_ref,
        nics=[vm_nic],
        cd_roms=[cdrom],
        disks=[cloned_disk, empty_disk],
        guest_customization=AhvVmConfig.GuestCustomizationParams.GuestCustomizationParams(
            config=AhvVmConfig.CloudInit.CloudInit(
                cloud_init_script=AhvVmConfig.Userdata.Userdata(value=userdata_encoded),
                datasource_type=AhvVmConfig.CloudInitDataSourceType.CloudInitDataSourceType.CONFIG_DRIVE_V2,
            )
        )
        if customise_vm
        else None,
    )

    vmm_instance = ntnx_vmm_py_client.api.VmApi(api_client=vmm_client)

    print("\nCreating VM ...")
    create_vm = vmm_instance.create_vm(async_req=False, body=new_vm)

    task_extid = create_vm.data.ext_id
    utils.monitor_task(
        task_ext_id=task_extid,
        task_name="VM create",
        pc_ip=pc_ip,
        username=username,
        password=cluster_password,
        poll_timeout=1,
        prefix="",
    )
    prism_instance = ntnx_prism_py_client.api.TasksApi(api_client=prism_client)
    new_vm_ext_id = (
        prism_instance.get_task_by_id(task_extid).data.entities_affected[0].ext_id
    )
    print(
        f"New VM named {vm_name} has been created with \
ext_id {new_vm_ext_id}.\n"
    )


if __name__ == "__main__":
    main()
