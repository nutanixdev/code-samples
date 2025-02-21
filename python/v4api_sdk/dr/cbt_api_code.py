import sys

'''
This example is specific to VM recovery points.
'''

# Import ntnx dataprotection api libraries.
import ntnx_dataprotection_py_client


# Discover cluster specific libraries.
from ntnx_dataprotection_py_client.models.dataprotection.v4.content.ClusterDiscoverSpec import ClusterDiscoverSpec
from ntnx_dataprotection_py_client.models.dataprotection.v4.common.ClusterInfo import ClusterInfo
from ntnx_dataprotection_py_client.models.dataprotection.v4.content.ClusterDiscoverOperation import ClusterDiscoverOperation
from ntnx_dataprotection_py_client.models.dataprotection.v4.content.ComputeChangedRegionsClusterDiscoverSpec import ComputeChangedRegionsClusterDiscoverSpec
from ntnx_dataprotection_py_client.models.dataprotection.v4.content.VmDiskRecoveryPointReference import VmDiskRecoveryPointReference
from ntnx_dataprotection_py_client.models.dataprotection.v4.content.VmRecoveryPointChangedRegionsComputeSpec import VmRecoveryPointChangedRegionsComputeSpec


def get_pc_client_config():
    # Configure the client.
    config = ntnx_dataprotection_py_client.Configuration()
    # IPv4/IPv6 address or FQDN of the cluster
    config.host = sys.argv[1]
    # Port to which to connect to.
    config.port = 9440
    # Max retry attempts while reconnecting on a loss of connection
    config.max_retry_attempts = 3
    # Backoff factor to use during retry attempts
    config.backoff_factor = 3
    # UserName to connect to the cluster
    config.username = <USERNAME>
    # Password to connect to the cluster
    config.password = <PASSWORD>
    return config


def get_pe_client_config(target_cluster_ip):
    # Configure the client.
    config = ntnx_dataprotection_py_client.Configuration()
    # IPv4/IPv6 address or FQDN of the cluster
    config.host = target_cluster_ip
    # Port to which to connect to.
    config.port = 9440
    # Max retry attempts while reconnecting on a loss of connection
    config.max_retry_attempts = 3
    # Backoff factor to use during retry attempts
    config.backoff_factor = 3
    return config

def prepare_vm_disk_recovery_point_reference(recovery_point_ext_id, vm_recovery_point_ext_id, disk_recovery_point_ext_id):
    disk_recovery_point = VmDiskRecoveryPointReference()
    disk_recovery_point.recovery_point_ext_id = recovery_point_ext_id
    disk_recovery_point.vm_recovery_point_ext_id = vm_recovery_point_ext_id
    disk_recovery_point.disk_recovery_point_ext_id = disk_recovery_point_ext_id
    return disk_recovery_point

def prepare_discover_cluster_request_body(base_disk_recovery_point, reference_disk_recovery_point=None):
    # Discover cluster body model.
    cluster_discover_spec = ClusterDiscoverSpec()
    # Set the operation for which you want to send the discover cluster request.
    cluster_discover_spec.operation = ClusterDiscoverOperation.COMPUTE_CHANGED_REGIONS
    # prepare COMPUTE_CHANGED_REGIONS spec body.
    cbt_spec = ComputeChangedRegionsClusterDiscoverSpec()
    cbt_spec.disk_recovery_point = base_disk_recovery_point
    if reference_disk_recovery_point:
        cbt_spec.reference_disk_recovery_point = reference_disk_recovery_point

    # Set the vm cbt spec in cluster discover spec body.
    cluster_discover_spec.spec = cbt_spec
    return cluster_discover_spec


def get_pc_recovery_point_api_client():
    # Get the client configuration.
    pc_client_config = get_pc_client_config()
    # Intialize the PC ApiClient.
    pc_client = ntnx_dataprotection_py_client.ApiClient(configuration=pc_client_config)
    pc_recovery_points_api = ntnx_dataprotection_py_client.RecoveryPointsApi(api_client=pc_client)
    return pc_recovery_points_api


def get_pe_recovery_point_api_client(target_cluster_ip, certificate=None):
    # Get the client configuration.
    pe_client_config = get_pe_client_config(target_cluster_ip)
    # Intialize the PC ApiClient.
    pe_client = ntnx_dataprotection_py_client.ApiClient(configuration=pe_client_config)
    # Set the cookie header.
    igw_header = "NTNX_IGW_SESSION={}".format(certificate)
    pe_client.add_default_header("cookie", igw_header)
    pe_recovery_points_api = ntnx_dataprotection_py_client.RecoveryPointsApi(api_client=pe_client)
    return pe_recovery_points_api

def prepare_vm_changed_regions_request_body(offset, length=None, block_size_byte=None, ref_recovery_point_ext_id=None,
                                            ref_vm_recovery_point_ext_id=None, ref_disk_recovery_point_ext_id=None):
    body = VmRecoveryPointChangedRegionsComputeSpec()
    body.offset = offset # Int64 number.
    if length:
        body.length = length # Int64 number.
    if block_size_byte:
        body.block_size_byte = block_size_byte # Int64 number.
    if ref_recovery_point_ext_id:
        body.reference_recovery_point_ext_id = ref_recovery_point_ext_id
        body.reference_vm_recovery_point_ext_id = ref_vm_recovery_point_ext_id
        body.reference_disk_recovery_point_ext_id = ref_disk_recovery_point_ext_id
    return body
                                                                                                                                  
if __name__ == "__main__":
    recovery_point_ext_id = sys.argv[2]
    vm_recovery_point_ext_id = sys.argv[3]
    disk_recovery_point_ext_id = sys.argv[4]
    base_disk_recovery_point = prepare_vm_disk_recovery_point_reference(recovery_point_ext_id, vm_recovery_point_ext_id, disk_recovery_point_ext_id)
    # This code is testing without reference recovery point.
    # reference_disk_recovery_point = prepare_vm_disk_recovery_point_reference(ref_recovery_point_ext_id, ref_vm_recovery_point_ext_id, ref_disk_recovery_point_ext_id)
    clusterDiscoverSpec = prepare_discover_cluster_request_body(base_disk_recovery_point=base_disk_recovery_point)
    pe_auth_certificate = None
    try:
        pc_rp_api_client = get_pc_recovery_point_api_client()
        pc_api_response = pc_rp_api_client.discover_cluster_for_recovery_point_id(extId=recovery_point_ext_id, body=clusterDiscoverSpec)
        print(pc_api_response)
        pe_auth_certificate = pc_api_response.data.jwt_token
    except ntnx_dataprotection_py_client.rest.ApiException as e:
        print(e)


    # PE API call.
    try:
        offset = 0
        nextOffset = -1
        target_cluster_ip = pc_api_response.data.cluster_ip.ipv4.value
        pe_rp_api_client = get_pe_recovery_point_api_client(target_cluster_ip, certificate=pe_auth_certificate)
        while nextOffset != 0:
            request_body = prepare_vm_changed_regions_request_body(offset)
            pe_api_response = pe_rp_api_client.vm_recovery_point_compute_changed_regions(recoveryPointExtId=recovery_point_ext_id, vmRecoveryPointExtId=vm_recovery_point_ext_id, extId=disk_recovery_point_ext_id, body=request_body)
            print(pe_api_response)
            offset = int(pe_api_response.metadata.extra_info[0].value)
            nextOffset = int(pe_api_response.metadata.extra_info[0].value)
    except ntnx_dataprotection_py_client.rest.ApiException as e:
        print(e)
