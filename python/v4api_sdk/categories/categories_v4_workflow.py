'''
This script demonstrates the usage of the Categories API in the Nutanix v4 Python SDK.
'''
from time import sleep
import urllib3
import ntnx_prism_py_client
import ntnx_vmm_py_client
import ntnx_vmm_py_client.models.vmm.v4.ahv.config as AhvVmConfig
import ntnx_clustermgmt_py_client
from ntnx_vmm_py_client.models.vmm.v4.ahv.config.DisassociateVmCategoriesParams import DisassociateVmCategoriesParams as AhvConfigDisassociateVmCategoriesParams
from ntnx_vmm_py_client.models.vmm.v4.ahv.config.AssociateVmCategoriesParams import AssociateVmCategoriesParams as AhvConfigAssociateVmCategoriesParams
import argparse
import getpass

'''
suppress warnings about insecure connections
you probably shouldn't do this in production
'''
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

'''
setup our connection details for the Prism Central
'''
# Parse command line arguments
parser = argparse.ArgumentParser(description='Nutanix Categories API Workflow')
parser.add_argument('--pc_ip', required=True, help='IP address of the Prism Central')
parser.add_argument('--username', required=True, help='Username to connect to the cluster')
args = parser.parse_args()

# Prompt user for password
password = getpass.getpass(prompt='Enter password: ')

PC_IP = args.pc_ip
PORT = 9440
USERNAME = args.username
PASSWORD = password

'''
setup the categories API client
'''
def setupCategoriesApi():
    # Configure the categories client
    config = ntnx_prism_py_client.Configuration()
    # True or False for ssl verification
    config.verify_ssl = False
    # IP of the PC
    config.host = PC_IP
    # Port to which to connect to
    config.port = PORT
    # Max retry attempts while reconnecting on a loss of connection
    config.max_retry_attempts = 3
    # Backoff factor to use during retry attempts
    config.backoff_factor = 3
    # UserName to connect to the cluster
    config.username = USERNAME
    # Password to connect to the cluster
    config.password = PASSWORD
    client_ = ntnx_prism_py_client.ApiClient(configuration=config)
    # Create an instance of CategoriesApi class
    categories_api = ntnx_prism_py_client.CategoriesApi(
        api_client=client_)
    return categories_api

'''
setup the vmm API client
'''
def setupVmmApi():
    # Configure the vmm client
    config = ntnx_vmm_py_client.Configuration()
    # True or False for ssl verification
    config.verify_ssl = False
    config.host = PC_IP
    config.port = PORT
    # Max retry attempts while reconnecting on a loss of connection
    config.max_retry_attempts = 3
    # Max retry attempts while reconnecting on a loss of connection
    config.backoff_factor = 3
    # UserName to connect to the cluster
    config.username = USERNAME
    # Password to connect to the cluster
    config.password = PASSWORD
    client = ntnx_vmm_py_client.ApiClient(configuration=config)
    # Create an instance of VmApi class
    vm_api = ntnx_vmm_py_client.VmApi(api_client=client)
    return vm_api

'''
setup the clustermgmt API client
'''
def setupClusterApi():
    # Configure the clustermgmt client
    config = ntnx_clustermgmt_py_client.Configuration()
    # IP of the PC
    config.host = PC_IP
    # Port to which to connect to
    config.port = PORT
    # UserName to connect to the cluster
    config.username = USERNAME
    # Password to connect to the cluster
    config.password = PASSWORD
    config.debug = True
    # True or False for ssl verification
    config.verify_ssl = False
    clustermgmt_api_client = ntnx_clustermgmt_py_client.ApiClient(
        configuration=config)
    # Create an instance of ClustersApi class
    cluster_api = ntnx_clustermgmt_py_client.ClustersApi(
        api_client=clustermgmt_api_client)
    return cluster_api


def setup():
    cluster_api = setupClusterApi()
    vm_api = setupVmmApi()
    categories_api = setupCategoriesApi()
    return cluster_api, vm_api, categories_api

'''
Method to get the cluster UUID by name
'''
def GetClusterUuidByName(cluster_api, cluster_name):
    try:
        api_response = cluster_api.list_clusters(
            _filter=f"name eq '{cluster_name}'")
        cluster_uuid = api_response.data[0].ext_id
        return cluster_uuid
    except Exception as e:
        print("Exception when calling ClustersApi->list_clusters: %s\n" % e)
        return None

'''
Method to create a category
'''
def CreateCategory(categories_api, key="example_key", value="example_value_1", description="Description of the category"):
    cat = ntnx_prism_py_client.Category(
        key=key, value=value, description=description)
    try:
        print("Category specs: ", cat.to_dict())
        print("\nCategory creation in progress. Please wait...")
        resp = categories_api.create_category(body=cat)
        sleep(3)
        cat_ext_id = resp.data.ext_id
        return cat_ext_id
    except Exception as e:
        print("Exception when calling CategoriesApi->create_category: %s\n" % e)
        return None

'''
Method to get the VM UUID by name
'''
def GetVmUuidByName(vm_api, vm_name):
    try:
        api_response = vm_api.list_vms(_filter=f"name eq '{vm_name}'")
        vm_uuid = api_response.data[0].ext_id
        return vm_uuid
    except Exception as e:
        print("Exception when calling VmApi->list_vms: %s\n" % e)
        return None

'''
Method to create a VM
'''
def CreateVm(vm_api, cluster_uuid, vm_name="example_vm", description="VM created using Nutanix v4 Python SDK"):
    vm = AhvVmConfig.Vm.Vm(
        name=vm_name,
        description=description,
        cluster=ntnx_vmm_py_client.AhvConfigClusterReference(
            ext_id=cluster_uuid)
    )
    try:
        api_response = vm_api.create_vm(body=vm, async_req=False)
        print("VM specs: ", vm.to_dict())
        print("\nVM creation in progress. Please wait...")
        sleep(3)
        vm_uuid = GetVmUuidByName(vm_api, vm_name)
        return vm_uuid
    except Exception as e:
        print("Exception when calling VmApi->create_vm: %s\n" % e)
        return None

'''
Method to associate a category to a VM
'''
def AssociateCategoryToVm(vm_api, vm_uuid, cat_ext_id):
    try:
        resp = vm_api.get_vm_by_id(vm_uuid)
        eTag = ntnx_prism_py_client.ApiClient().get_etag(resp)
        kwargs = {"if_match": eTag}
        resp = vm_api.associate_categories(extId=vm_uuid, body=AhvConfigAssociateVmCategoriesParams(
            [ntnx_vmm_py_client.AhvConfigCategoryReference(ext_id=cat_ext_id)]), **kwargs)
        return resp
    except Exception as e:
        print("Exception when calling VmApi->associate_categories: %s\n" % e)
        return None

'''
Method to get a category by ID
'''
def GetCategoryById(categories_api, cat_ext_id):
    try:
        resp = categories_api.get_category_by_id(extId=cat_ext_id)
        return resp
    except Exception as e:
        print("Exception when calling CategoriesApi->get_category_by_id: %s\n" % e)
        return None

'''
Method to list the detailed associations of a category
'''
def ListDetailedAssociationsOfCategory(categories_api, cat_ext_id):
    try:
        resp = categories_api.get_category_by_id(
            extId=cat_ext_id, _expand="detailedAssociations")
        return resp
    except Exception as e:
        print("Exception when calling CategoriesApi->get_category_associations: %s\n" % e)
        return None

'''
Method to update the description of a category
'''
def UpdateDescriptionOfCategory(categories_api, cat_ext_id, newDescription):
    resp = GetCategoryById(categories_api, cat_ext_id)
    owner_uuid = resp.data.owner_uuid
    eTag = ntnx_prism_py_client.ApiClient().get_etag(resp)
    cat = ntnx_prism_py_client.Category(
        key="example_key", value="example_value_1", description=newDescription, owner_uuid=owner_uuid)
    kwargs = {"if_match": eTag}
    try:
        resp = categories_api.update_category_by_id(
            extId=cat_ext_id, body=cat, **kwargs)
        return resp
    except Exception as e:
        print("Exception when calling CategoriesApi->update_category_by_id (new description): %s\n" % e)
        return None

'''
Method to update the owner_uuid of a category
'''
def UpdateOwnerUuidOfCategory(categories_api, cat_ext_id, owner_uuid):
    resp = GetCategoryById(categories_api, cat_ext_id)
    description = resp.data.description
    eTag = ntnx_prism_py_client.ApiClient().get_etag(resp)
    cat = ntnx_prism_py_client.Category(
        key="example_key", value="example_value_1", description=description, owner_uuid=owner_uuid)
    kwargs = {"if_match": eTag}
    try:
        resp = categories_api.update_category_by_id(
            extId=cat_ext_id, body=cat, **kwargs)
        return resp
    except Exception as e:
        print("Exception when calling CategoriesApi->update_category_by_id (new owner_uuid): %s\n" % e)
        return None

'''
Method to list all categories
'''
def ListAllCategories(categories_api):
    try:
        resp = categories_api.list_categories()
        return resp
    except Exception as e:
        print("Exception when calling CategoriesApi->list_categories: %s\n" % e)
        return None

'''
Method to list categories with associated counts
'''
def ListCategoriesWithCount(categories_api):
    try:
        resp = categories_api.list_categories(_expand="associations")
        return resp
    except Exception as e:
        print("Exception when calling CategoriesApi->list_categories: %s\n" % e)
        return None

'''
Method to sort categories by key
'''
def SortCategoriesByKey(categories_api):
    try:
        resp = categories_api.list_categories(_orderby="key")
        return resp
    except Exception as e:
        print("Exception when calling CategoriesApi->list_categories: %s\n" % e)
        return None

'''
Method to list categories with certain attributes (e.g. value, type, description)
'''
def ListCategoriesWithAttributes(categories_api, attributes):
    try:
        resp = categories_api.list_categories(_select=attributes)
        return resp
    except Exception as e:
        print("Exception when calling CategoriesApi->list_categories: %s\n" % e)
        return None

'''
Method to list categories matching a certain key/value content (e.g. example_key/example_value)
'''
def ListCategoriesMatchingKeyAndValue(categories_api, key, value):
    try:
        resp = categories_api.list_categories(
            _filter=f"key eq '{key}' and value eq '{value}'")
        return resp
    except Exception as e:
        print("Exception when calling CategoriesApi->list_categories: %s\n" % e)
        return None

'''
Method to list categories starting with a certain string in key and value
'''
def ListCategoriesStartingWithCertainStringInKeyAndValue(categories_api, str_key, str_value):
    try:
        resp = categories_api.list_categories(
            _filter=f"startswith(key,'{str_key}') and startswith(value,'{str_value}')")
        return resp
    except Exception as e:
        print("Exception when calling CategoriesApi->list_categories: %s\n" % e)
        return None

'''
Method to list categories sorted by key and value
'''
def ListCategoriesSortedByKeyAndValue(categories_api):
    try:
        resp = categories_api.list_categories(_orderby="key,value")
        return resp
    except Exception as e:
        print("Exception when calling CategoriesApi->list_categories: %s\n" % e)
        return None

'''
Method to list categories of a certain type (USER / SYSTEM / INTERNAL)
'''
def ListCategoriesOfCertainType(categories_api, category_type):
    try:
        resp = categories_api.list_categories(
            _filter=f"type eq Prism.Config.CategoryType'{category_type}'")
        return resp
    except Exception as e:
        print("Exception when calling CategoriesApi->list_categories: %s\n" % e)
        return None

'''
Method to list categories having at least one association
'''
def ListCategoriesWithAtLeastOneAssociation(categories_api):
    try:
        resp = categories_api.list_categories(
            _expand="associations($filter=count ge 1)")
        return resp
    except Exception as e:
        print("Exception when calling CategoriesApi->list_categories: %s\n" % e)
        return None
'''
Method to list categories having associated with a particular resource type
'''
def ListCategoriesWithAssociationsOfResourceType(categories_api, resource_type):
    try:
        resp = categories_api.list_categories(
            _expand="associations($filter=resourceType eq Prism.Config.ResourceType'" + resource_type + "')")
        return resp
    except Exception as e:
        print("Exception when calling CategoriesApi->list_categories: %s\n" % e)
        return None

'''
Method to disassociate a category from a VM
'''
def DisassociateCategoryFromVm(vm_api, vm_uuid, cat_ext_id):
    try:
        resp = vm_api.get_vm_by_id(vm_uuid)
        eTag = ntnx_prism_py_client.ApiClient().get_etag(resp)
        kwargs = {"if_match": eTag}
        resp = vm_api.disassociate_categories(extId=vm_uuid, body=AhvConfigDisassociateVmCategoriesParams(
            [ntnx_vmm_py_client.AhvConfigCategoryReference(ext_id=cat_ext_id)]), **kwargs)
        return resp
    except Exception as e:
        print("Exception when calling VmApi->disassociate_categories: %s\n" % e)
        return None

'''
Method to delete a VM
'''
def DeleteVm(vm_api, vm_uuid):
    try:
        resp = vm_api.get_vm_by_id(vm_uuid)
        eTag = ntnx_prism_py_client.ApiClient().get_etag(resp)
        kwargs = {"if_match": eTag}
        resp = vm_api.delete_vm_by_id(extId=vm_uuid, **kwargs)
        return resp
    except Exception as e:
        print("Exception when calling VmApi->delete_vm_by_id: %s\n" % e)
        return None

'''
Method to delete a category
'''
def DeleteCategory(categories_api, cat_ext_id):
    try:
        resp = categories_api.delete_category_by_id(extId=cat_ext_id)
        return resp
    except Exception as e:
        print("Exception when calling CategoriesApi->delete_category_by_id: %s\n" % e)
        return None

'''
Main workflow to demonstrate the usage of the Categories API
'''
def workflow(cluster_api, vm_api, categories_api):
    # Get the cluster UUID
    cluster_uuid = None
    try:
        # get the cluster name as input
        CLUSTER_NAME = input("Enter the cluster name: ")
        cluster_uuid = GetClusterUuidByName(
            cluster_api, CLUSTER_NAME)
        print("\nCluster UUID: ", cluster_uuid)
        if cluster_uuid is None:
            print("Cluster not found. Exiting the workflow.")
            return
    except Exception as e:
        print("Exception when calling GetClusterUuidByName: %s\n" % e)
        return

    input("\n\nNext step is to create a category. Press ENTER to continue...\n")
    # ------------------------------------------------------------#
    print("\n#", "-"*50, " CREATE THE CATEGORY ", "-"*50, "#\n")
    try:
        cat_ext_id = CreateCategory(categories_api, key="example_key",
                                    value="example_value_1", description="Description of the category")
        print("\nCategory created with ext_id: ", cat_ext_id)
        if cat_ext_id is None:
            print("\nCategory not created. Exiting the workflow.")
            return
    except Exception as e:
        print("Exception when calling CreateCategory: %s\n" % e)
        return

    input("\n\nNext step is to fetch the recently created category. Press ENTER to continue...\n")
    # ------------------------------------------------------------#
    print("\n#", "-"*50, " FETCH THE CATEGORY ", "-"*50, "#\n")
    # Fetch a category
    OLD_OWNER_UUID = None
    try:
        resp = GetCategoryById(categories_api, cat_ext_id)
        print("Fetched category: ", resp.data)
        OLD_OWNER_UUID = resp.data.owner_uuid
        if resp is None:
            print("\nCategory not found. Exiting the workflow.")
            return
    except Exception as e:
        print("Exception when calling GetCategoryById: %s\n" % e)

    input("\n\nNext step is to create a VM. Press ENTER to continue...\n")
    # ------------------------------------------------------------#
    vm_uuid = None
    print("\n#", "-"*50, " CREATE THE VM ", "-"*50, "#\n")
    try:
        vm_uuid = CreateVm(vm_api, cluster_uuid, vm_name="example_vm",
                           description="VM created using Nutanix v4 Python SDK")
        print("\nVM created with ext_id: ", vm_uuid)
        if vm_uuid is None:
            print("\nVM not created. Exiting the workflow.")
            return
    except Exception as e:
        print("Exception when calling CreateVm: %s\n" % e)
        return

    input("\n\nNext step is to associate the category to the VM. Press ENTER to continue...\n")
    # ------------------------------------------------------------#
    print("\n#", "-"*50, " ASSOCIATE THE CATEGORY TO VM ", "-"*50, "#\n")
    # Associate a category from a VM
    try:
        resp = AssociateCategoryToVm(vm_api, vm_uuid, cat_ext_id)
        print("Category associated with VM: ", resp)
    except Exception as e:
        print("Exception when calling AssociateCategoryToVm: %s\n" % e)
        return

    input("\n\nNext step is to list all the associations of the category. Press ENTER to continue...\n")
    # ------------------------------------------------------------#
    print("\n#", "-"*50, " LIST THE ASSOCIATIONS OF THE CATEGORY ", "-"*50, "#\n")
    # List the associations of a category
    try:
        resp = ListDetailedAssociationsOfCategory(categories_api, cat_ext_id)
        print("Associations of the category: ", resp)
    except Exception as e:
        print("Exception when calling ListDetailedAssociationsOfCategory: %s\n" % e)

    input("\n\nNext step is to update the description of category. Press ENTER to continue...\n")
    # ------------------------------------------------------------#
    # Update a category
    print("\n#", "-"*50, " UPDATE THE DESCRIPTION OF THE CATEGORY ", "-"*50, "#\n")
    # 1. Update the description of the category
    newDescription = "New description of the category"
    print("Old description: '", resp.data.description, "'", " New description: '", newDescription, "'\n")
    try:
        resp = UpdateDescriptionOfCategory(
            categories_api, cat_ext_id, newDescription)
        print("category description updated: ", resp)
    except Exception as e:
        print("Exception when calling UpdateDescriptionOfCategory: %s\n" % e)

    input("\n\nNext step is to update the owner_uuid of category. Press ENTER to continue...\n")
    # ------------------------------------------------------------#
    print("\n#", "-"*50, " UPDATE THE OWNER_UUID OF THE CATEGORY ", "-"*50, "#\n")
    # 2. Update the Owner UUID of the category
    # Note: The owner_uuid should be a valid user_uuid
    try:
        NEW_OWNER_UUID = input("Enter the new owner_uuid (must be a valid user_uuid): ")
        print("Old owner_uuid: '", OLD_OWNER_UUID, "'", " New owner_uuid: '", NEW_OWNER_UUID, "'\n")
        resp = UpdateOwnerUuidOfCategory(
            categories_api, cat_ext_id, NEW_OWNER_UUID)
        print("category owner_uuid updated: ", resp)
    except Exception as e:
        print("Exception when calling UpdateOwnerUuidOfCategory: %s\n" % e)

    input("\n\nNext step is to list all the categories. Press ENTER to continue...\n")
    # ------------------------------------------------------------#
    # List categories
    print("\n#", "-"*50, " LIST ALL THE CATEGORIES ", "-"*50, "#\n")
    # 1. List all categories
    try:
        resp = ListAllCategories(categories_api)
        print("List of categories: ", resp)
    except Exception as e:
        print("Exception when calling ListAllCategories: %s\n" % e)

    input("\n\nNext step is to list categories with associated counts. Press ENTER to continue...\n")
    # ------------------------------------------------------------#
    print("\n#", "-"*50, " LIST CATEGORIES WITH ASSOCIATED COUNTS ", "-"*50, "#\n")
    # 2. Use expansion to show associated counts
    try:
        resp = ListCategoriesWithCount(categories_api)
        print("List of categories with count: ", resp)
    except Exception as e:
        print("Exception when calling ListCategoriesWithCount: %s\n" % e)

    input("\n\nNext step is to sort the categories by key. Press ENTER to continue...\n")
    # ------------------------------------------------------------#
    print("\n#", "-"*50, " SORT THE CATEGORIES BY KEY ", "-"*50, "#\n")
    # 3. sort by key
    try:
        resp = SortCategoriesByKey(categories_api)
        print("List of categories sorted by key: ", resp)
    except Exception as e:
        print("Exception when calling SortCategoriesByKey: %s\n" % e)

    input("\n\nNext step is to list categories with certain attributes. Press ENTER to continue...\n")
    # ------------------------------------------------------------#
    print("\n#", "-"*50, " LIST CATEGORIES WITH CERTAIN ATTRIBUTES ", "-"*50, "#\n")
    # 4. return only certain attributes in the result (e.g. value, type, description)
    try:
        resp = ListCategoriesWithAttributes(
            categories_api, "value,type,description")
        print("List of categories with only key, value and type: ", resp)
    except Exception as e:
        print("Exception when calling ListCategoriesWithAttributes: %s\n" % e)

    input("\n\nNext step is to list categories matching a certain key/value content. Press ENTER to continue...\n")
    # ------------------------------------------------------------#
    print("\n#", "-"*50,
          " LIST CATEGORIES MATCHING A CERTAIN KEY/VALUE CONTENT ", "-"*50, "#\n")
    # 5. filter categories matching a certain key/value content
    try:
        resp = ListCategoriesMatchingKeyAndValue(
            categories_api, "example_key", "example_value_1")
        print("List of categories with key 'my_category': ", resp)
    except Exception as e:
        print("Exception when calling ListCategoriesMatchingKeyAndValue: %s\n" % e)

    input("\n\nNext step is to list categories starting with a certain string in key and value. Press ENTER to continue...\n")
    # ------------------------------------------------------------#
    print("\n#", "-"*50, " LIST CATEGORIES STARTING WITH A CERTAIN STRING IN KEY AND VALUE ", "-"*50, "#\n")
    # 6. filter categories whose key or value starting with a certain string
    try:
        resp = ListCategoriesStartingWithCertainStringInKeyAndValue(
            categories_api, "ex", "ex")
        print("List of categories with key starting with 'ex' and value starting with 'ex': ", resp)
    except Exception as e:
        print("Exception when calling ListCategoriesStartingWithCertainStringInKeyAndValue: %s\n" % e)

    input("\n\nNext step is to list categories sorted by key and value. Press ENTER to continue...\n")
    # ------------------------------------------------------------#
    print("\n#", "-"*50, " LIST CATEGORIES SORTED BY KEY AND VALUE ", "-"*50, "#\n")
    # 7. sort by key and value
    try:
        resp = ListCategoriesSortedByKeyAndValue(categories_api)
        print("List of categories sorted by key and value: ", resp)
    except Exception as e:
        print("Exception when calling ListCategoriesSortedByKeyAndValue: %s\n" % e)

    input("\n\nNext step is to list categories of a certain type (USER / SYSTEM / INTERNAL). Press ENTER to continue...\n")
    # ------------------------------------------------------------#
    print("\n#", "-"*50, " LIST CATEGORIES OF A CERTAIN TYPE (USER / SYSTEM / INTERNAL) ", "-"*50, "#\n")
    # 8. filter categories w.r.t type USER / SYSTEM / INTERVAL
    try:
        resp = ListCategoriesOfCertainType(categories_api, "USER")
        print("List of categories with type USER: ", resp)
    except Exception as e:
        print("Exception when calling ListCategoriesOfCertainType: %s\n" % e)

    input("\n\nNext step is to list categories having at least one association. Press ENTER to continue...\n")
    # ------------------------------------------------------------#
    print("\n#", "-"*50,
          " LIST CATEGORIES HAVING AT LEAST ONE ASSOCIATION ", "-"*50, "#\n")
    # 9. use filters and expansion to show only those categories that have at least one association
    try:
        resp = ListCategoriesWithAtLeastOneAssociation(categories_api)
        print("List of categories with at least one association: ", resp)
    except Exception as e:
        print("Exception when calling ListCategoriesWithAtLeastOneAssociation: %s\n" % e)

    input("\n\nNext step is to list categories having association with a particular resource type. Press ENTER to continue...\n")
    # ------------------------------------------------------------#
    print("\n#", "-"*50,
          " LIST CATEGORIES HAVING ASSOCIATION WITH A PARTICULAR RESOURCE TYPE ", "-"*50, "#\n")
    # 9. use filters and expansion to show only those categories that have at least one association
    try:
        resp = ListCategoriesWithAssociationsOfResourceType(categories_api, "VM")
        print("List of categories associated with resource type VM: ", resp)
    except Exception as e:
        print("Exception when calling ListCategoriesWithAtLeastOneAssociation: %s\n" % e)

    input("\n\nNext step is to disassociate the category from the VM. Press ENTER to continue...\n")
    # ------------------------------------------------------------#
    print("\n#", "-"*50, " DISASSOCIATE THE CATEGORY FROM VM ", "-"*50, "#\n")
    # Disassociate a category from a VM
    try:
        resp = DisassociateCategoryFromVm(vm_api, vm_uuid, cat_ext_id)
        print(f"Disassociated category {cat_ext_id} from VM {vm_uuid}")
    except Exception as e:
        print("Exception when calling DisassociateCategoryFromVm: %s\n" % e)

    input("\n\nNext step is to delete the VM. Press ENTER to continue...\n")
    # ------------------------------------------------------------#
    print("\n#", "-"*50, " DELETE THE VM ", "-"*50, "#\n")
    # Delete the VM
    try:
        resp = DeleteVm(vm_api, vm_uuid)
        print(f"Deleted VM with ext_id: {vm_uuid}")
    except Exception as e:
        print("Exception when calling DeleteVm: %s\n" % e)

    input("\n\nNext step is to delete the category. Press ENTER to continue...\n")
    # ------------------------------------------------------------#
    print("\n#", "-" * 50, " DELETE THE CATEGORY ", "-" * 50, "#\n")

    # Delete a category
    try:
        resp = DeleteCategory(categories_api, cat_ext_id)
        print(f"Deleted category with ext_id: {cat_ext_id}")
    except Exception as e:
        print("Exception when calling DeleteCategory: %s\n" % e)

    # ------------------------------------------------------------#
    print("\n#", "-" * 120, "#\n")


if __name__ == '__main__':
    cluster_api, vm_api, categories_api = setup()
    workflow(cluster_api, vm_api, categories_api)
