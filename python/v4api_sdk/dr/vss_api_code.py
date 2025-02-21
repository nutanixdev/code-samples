import sys


# Import ntnx dataprotection api libraries.
import ntnx_dataprotection_py_client


# Discover cluster specific libraries.
from ntnx_dataprotection_py_client.models.dataprotection.v4.content.ClusterDiscoverSpec import ClusterDiscoverSpec
from ntnx_dataprotection_py_client.models.dataprotection.v4.common.ClusterInfo import ClusterInfo
from ntnx_dataprotection_py_client.models.dataprotection.v4.content.ClusterDiscoverOperation import ClusterDiscoverOperation
from ntnx_dataprotection_py_client.models.dataprotection.v4.content.GetVssMetadataClusterDiscoverSpec import GetVssMetadataClusterDiscoverSpec


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


def prepare_discover_cluster_request_body(vmRecoveryPointExtId=None):
    # Discover cluster body model.
    clusterDiscoverSpec = ClusterDiscoverSpec()
    # Set the operation for which you want to send the discover cluster request.
    clusterDiscoverSpec.operation = ClusterDiscoverOperation.GET_VSS_METADATA
    # prepare GET_VSS_METADATA spec body.
    vss_spec = GetVssMetadataClusterDiscoverSpec(vm_recovery_point_ext_id=vmRecoveryPointExtId)
    # Set the vss spec in cluster discover spec body.
    clusterDiscoverSpec.spec = vss_spec
    return clusterDiscoverSpec


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
                                                                                                                                  
if __name__ == "__main__":
    recovery_point_ext_id = sys.argv[2]
    vm_recovery_point_ext_id = sys.argv[3]
    clusterDiscoverSpec = prepare_discover_cluster_request_body(vmRecoveryPointExtId=vm_recovery_point_ext_id)
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
        target_cluster_ip = pc_api_response.data.cluster_ip.ipv4.value
        pe_rp_api_client = get_pe_recovery_point_api_client(target_cluster_ip, certificate=pe_auth_certificate)
        pe_api_response = pe_rp_api_client.get_vss_metadata_by_vm_recovery_point_id(recoveryPointExtId=recovery_point_ext_id,vmRecoveryPointExtId=vm_recovery_point_ext_id)
        print(pe_api_response)
    except ntnx_dataprotection_py_client.rest.ApiException as e:
        print(e)
