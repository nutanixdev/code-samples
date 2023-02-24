"""
Use the Nutanix v4 Python SDK to create a Prism Central VM
"""

import getpass
import argparse
import sys
import uuid
from base64 import b64encode
from pprint import pprint
import urllib3

import ntnx_vmm_py_client
import ntnx_prism_py_client
import ntnx_clustermgmt_py_client
import ntnx_networking_py_client
import ntnx_storage_py_client

from ntnx_vmm_py_client import Configuration as VMMConfiguration
from ntnx_vmm_py_client import ApiClient as VMMClient

from ntnx_prism_py_client import Configuration as PrismConfiguration
from ntnx_prism_py_client import ApiClient as PrismClient

from ntnx_clustermgmt_py_client import Configuration as ClusterConfiguration
from ntnx_clustermgmt_py_client import ApiClient as ClusterClient

from ntnx_networking_py_client import Configuration as NetworkingConfiguration
from ntnx_networking_py_client import ApiClient as NetworkingClient

from ntnx_storage_py_client import Configuration as StorageConfiguration
from ntnx_storage_py_client import ApiClient as StorageClient

from tme import Utils


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
        entities = instance.get_clusters(async_req=False)
        offset = 1
    elif entity_name == "image":
        entities = instance.get_images_list(async_req=False)
    elif entity_name == "subnet":
        entities = instance.list_subnets(async_req=False)
    else:
        print(f"{entity_name} is not supported.  Exiting.")
        sys.exit()

    # do some verification and make sure the user selects
    # the correct entity
    found_entities = []
    for entity in entities.data:
        if not entity.name in exclusions:
            found_entities.append({"name": entity.name, "ext_id": entity.ext_id})
    print(f"The following {entity_name}s ({len(entities.data)-offset}) were found.")
    pprint(found_entities)
    expected_entity_name = input(
        f"\nPlease enter the name of the selected {entity_name}: "
    ).lower()
    matches = [
        x for x in found_entities if x["name"].lower() == expected_entity_name.lower()
    ]
    if not matches:
        print(
            f"No {entity_name} was found matching the name {expected_entity_name}.  Exiting."
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
                "Password cannot be empty.  \
    Please enter a password or Ctrl-C/Ctrl-D to exit."
            )
            cluster_password = getpass.getpass(
                prompt="Please enter your Prism Central \
password: ",
                stream=None,
            )

    vmm_config = VMMConfiguration()
    prism_config = PrismConfiguration()
    cluster_config = ClusterConfiguration()
    networking_config = NetworkingConfiguration()
    storage_config = StorageConfiguration()

    for config in [
        vmm_config,
        prism_config,
        cluster_config,
        networking_config,
        storage_config,
    ]:
        config.host = pc_ip
        config.username = username
        config.password = cluster_password
        config.verify_ssl = False

    vmm_client = VMMClient(configuration=vmm_config)
    prism_client = PrismClient(configuration=prism_config)
    cluster_client = ClusterClient(configuration=cluster_config)
    networking_client = NetworkingClient(configuration=networking_config)
    storage_client = StorageClient(configuration=storage_config)

    for client in [
        vmm_client,
        prism_client,
        cluster_client,
        networking_client,
        storage_client,
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
        ntnx_clustermgmt_py_client.api.ClusterApi,
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

    # get the ext_id of the first storage container
    print("Retrieving storage container list ...")
    storage_instance = ntnx_storage_py_client.api.StorageContainerApi(
        api_client=storage_client
    )
    container_list = storage_instance.get_all_storage_containers(async_req=False)
    container_ext_id = container_list.data[0].container_ext_id
    container_name = container_list.data[0].name
    print(
        f'VM will be created on storage container named "{container_name}" \
with ext_id {container_ext_id}.\n'
    )

    # ask if the user wants to customise the VM using Cloud-Init
    # the Cloud-Init script is only relevant for CentOS Cloud based images
    print("The Cloud-Init script used by this demo has been created for \
CentOS images with Cloud-Init pre-installed.  To use your own \
Cloud-Init userdata, modify userdata.yaml."
    )
    customise_vm = utils.confirm(
        "Customise VM with Cloud-Init?"
    )

    # set the name for the new VM
    # a UUID is appended to make sure each new VM is uniquely named
    vm_name = f"api_v4_sdk-{uuid.uuid4()}"

    # tell the VM which cluster it will live on
    cluster_ref = (
        ntnx_vmm_py_client.Ntnx.vmm.v4.ahv.config.ClusterReference.ClusterReference()
    )
    cluster_ref.ext_id = cluster_ext_id

    # set the network connection settings for the new VM
    vm_nic = ntnx_vmm_py_client.Ntnx.vmm.v4.ahv.config.Nic.Nic()

    # NIC model and initial connection status
    vm_nic.backing_info = (
        ntnx_vmm_py_client.Ntnx.vmm.v4.ahv.config.EmulatedNic.EmulatedNic()
    )
    vm_nic.backing_info.is_connected = True
    vm_nic.backing_info.model = (
        ntnx_vmm_py_client.Ntnx.vmm.v4.ahv.config.EmulatedNicModel.EmulatedNicModel.E1000
    )

    # NIC type
    vm_nic.network_info = (
        ntnx_vmm_py_client.Ntnx.vmm.v4.ahv.config.NicNetworkInfo.NicNetworkInfo()
    )
    vm_nic.network_info.nic_type = (
        ntnx_vmm_py_client.Ntnx.vmm.v4.ahv.config.NicType.NicType.NORMAL_NIC
    )

    # the subnet the NIC will connect to
    # uses the subnet ext_id obtained earlier
    vm_nic.network_info.subnet = (
        ntnx_vmm_py_client.Ntnx.vmm.v4.ahv.config.SubnetReference.SubnetReference()
    )
    vm_nic.network_info.subnet.ext_id = subnet_ext_id

    # create a CDROM device for the new VM
    # optional but useful
    cdrom = ntnx_vmm_py_client.Ntnx.vmm.v4.ahv.config.Cdrom.Cdrom()
    cdrom.disk_address = (
        ntnx_vmm_py_client.Ntnx.vmm.v4.ahv.config.CdromAddress.CdromAddress()
    )
    cdrom.disk_address.bus_type = (
        ntnx_vmm_py_client.Ntnx.vmm.v4.ahv.config.CdromBusType.CdromBusType.IDE
    )
    cdrom.disk_address.index = 0
    cloned_disk = ntnx_vmm_py_client.Ntnx.vmm.v4.ahv.config.Disk.Disk()
    cloned_disk.backing_info = ntnx_vmm_py_client.Ntnx.vmm.v4.ahv.config.VmDisk.VmDisk()
    cloned_disk.backing_info.data_source = (
        ntnx_vmm_py_client.Ntnx.vmm.v4.ahv.config.DataSource.DataSource()
    )
    cloned_disk.backing_info.data_source.reference = (
        ntnx_vmm_py_client.Ntnx.vmm.v4.ahv.config.ImageReference.ImageReference()
    )
    cloned_disk.backing_info.data_source.reference.image_ext_id = image_ext_id
    cloned_disk.disk_address = (
        ntnx_vmm_py_client.Ntnx.vmm.v4.ahv.config.DiskAddress.DiskAddress()
    )
    cloned_disk.disk_address.bus_type = (
        ntnx_vmm_py_client.Ntnx.vmm.v4.ahv.config.DiskBusType.DiskBusType.SCSI
    )
    cloned_disk.disk_address.index = 0
    cloned_disk.scsi_passthrough_enabled = True

    # the second SCSI disk is empty, 40GB in size
    empty_disk = ntnx_vmm_py_client.Ntnx.vmm.v4.ahv.config.Disk.Disk()
    empty_disk.backing_info = ntnx_vmm_py_client.Ntnx.vmm.v4.ahv.config.VmDisk.VmDisk()
    empty_disk.backing_info.disk_size_bytes = 42949672960
    empty_disk.backing_info.storage_container = (
        ntnx_vmm_py_client.Ntnx.vmm.v4.ahv.config.VmDiskContainerReference.VmDiskContainerReference()
    )
    empty_disk.backing_info.storage_container.ext_id = container_ext_id
    empty_disk.disk_address = (
        ntnx_vmm_py_client.Ntnx.vmm.v4.ahv.config.DiskAddress.DiskAddress()
    )
    empty_disk.disk_address.bus_type = (
        ntnx_vmm_py_client.Ntnx.vmm.v4.ahv.config.DiskBusType.DiskBusType.SCSI
    )
    empty_disk.disk_address.index = 1

    # create the instance of the VM object
    # and use all the settings created up to this point
    new_vm = ntnx_vmm_py_client.Ntnx.vmm.v4.ahv.config.Vm.Vm()
    new_vm.name = vm_name
    new_vm.description = "VM created using Nutanix v4 Python SDK"
    new_vm.num_sockets = 1
    new_vm.num_cores_per_socket = 1
    new_vm.branding_enabled = True
    new_vm.memory_size_bytes = 8589934592
    new_vm.cluster = cluster_ref
    new_vm.nics = [vm_nic]
    new_vm.cdroms = [cdrom]
    new_vm.disks = [cloned_disk, empty_disk]

    # did the user say Yes to customising the VM?
    if customise_vm:
        print("VM will be customised with Cloud-Init.")
        new_vm.guest_customization = (
            ntnx_vmm_py_client.Ntnx.vmm.v4.ahv.config.GuestCustomization.GuestCustomization()
        )
        new_vm.guest_customization.config = (
            ntnx_vmm_py_client.Ntnx.vmm.v4.ahv.config.CloudInit.CloudInit()
        )
        new_vm.guest_customization.config.cloud_init_script = (
            ntnx_vmm_py_client.Ntnx.vmm.v4.ahv.config.Userdata.Userdata()
        )
        new_vm.guest_customization.config.datasource_type = (
            ntnx_vmm_py_client.Ntnx.vmm.v4.ahv.config.CloudInitDataSourceType.CloudInitDataSourceType.CONFIG_DRIVE_V2
        )

        with open("userdata.yaml", "r", encoding="ascii") as userdata_file:
            userdata_encoded = b64encode(
                bytes(userdata_file.read(), encoding="ascii")
            ).decode("ascii")

        new_vm.guest_customization.config.cloud_init_script.value = userdata_encoded

    else:
        print("VM will not be customised with Cloud-Init.")

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
        prefix=""
    )
    prism_instance = ntnx_prism_py_client.api.TaskApi(api_client=prism_client)
    new_vm_ext_id = prism_instance.task_get(task_extid).data.entities_affected[0].ext_id
    print(
        f"New VM named {vm_name} has been created with \
ext_id {new_vm_ext_id}.\n"
    )


if __name__ == "__main__":
    main()
