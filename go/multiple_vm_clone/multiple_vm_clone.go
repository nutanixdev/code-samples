/*
Create multiple clones of the VM in a specified network using v2 API
The script creates 3 clones of the specified VM
Requires, Name and Target for the clone
Rest of the reaource settings can be edited within the JSON function.
*/

package main

import (
	"bytes"
	"crypto/tls"
	"fmt"
	"io/ioutil"
	"log"
	"net/http"

	"github.com/tidwall/gjson"
)

var (
	peUser        string = "admin"                                                        // PE Username
	pePass        string = "<password>  "                                                 // PE Password
	peIp          string = "<cluster_ip>:9440"                                            // PE Cluster VIP
	peUrl         string = "/PrismGateway/services/rest/v2.0/"                            // URL for v2 API
	vmName        string = "<vm_name_to_be_cloned>"                                       // VM to be cloned
	network_uuid  string = "<network_uuid>"                                               // Network UUID for the cloned VMs
	cloneNameList        = []string{"vm_clone1_name", "vm_clone2_name", "vm_clone3_name"} // Clone Names
	vmNameUUidMap map[string]string
	testMap       map[string]string
)

// Basic Get Request function for v2 GET calls
func basicGet(peObj string) (string, error) {
	var bodyTextStr string
	testMap = make(map[string]string)
	tr := &http.Transport{
		TLSClientConfig: &tls.Config{InsecureSkipVerify: true},
	}
	client := &http.Client{Transport: tr}
	URL := "https://" + peIp + peUrl + peObj
	fmt.Println(fmt.Sprintf(`Getting data from URL: %s`, URL))
	req, err := http.NewRequest("GET", URL, nil)
	if err != nil {
		fmt.Println("Error creating HTTP request")
		log.Fatal()
	}
	req.Header.Set("ContentType", "application/json")
	req.SetBasicAuth(peUser, pePass)
	resp, err := client.Do(req)
	if err != nil {
		fmt.Println("Error: ", err)
	} else {
		bodyText, _ := ioutil.ReadAll(resp.Body)
		bodyTextStr = string(bodyText)
	}
	return bodyTextStr, err
}

// Basic Post request function for posting data using v2 POST calls
func basicPost(peObj string, jsonByteData []byte) (string, int, error) {
	var bodyTextStr string
	var httpCode int
	tr := &http.Transport{
		TLSClientConfig: &tls.Config{InsecureSkipVerify: true},
	}
	client := &http.Client{Transport: tr}
	URL := "https://" + peIp + peUrl + peObj
	fmt.Println(fmt.Sprintf(`Posting data to URL: %s`, URL))
	payloadData := bytes.NewBuffer(jsonByteData)
	req, err := http.NewRequest("POST", URL, payloadData)
	req.Header.Set("ContentType", "application/json")
	req.SetBasicAuth(peUser, pePass)
	resp, err := client.Do(req)
	if err != nil {
		fmt.Println("Error: ", err)
	} else {
		bodyText, _ := ioutil.ReadAll(resp.Body)
		httpCode = int(resp.StatusCode)
		bodyTextStr = string(bodyText)
	}
	return bodyTextStr, httpCode, err
}

// Payload JSON data for cloning the VM; takes clone Name as input
// Requires Network UUID of the network the Clone will be in
// Network UUID can be obtained usinag acli net.list on the CVM
func enterCloneName(cloneName string) []byte {
	var postData string = fmt.Sprintf(`{
"spec_list":
[
{
"name":"%s",
"memory_mb":4096,
"num_vcpus":4,
"num_cores_per_vcpu":1,
"vm_nics":
[
{
"network_uuid":"`+network_uuid+`"
}
],
"override_network_config":true,
"clone_affinity":false
}
]
}`, cloneName)
	postDataByte := []byte(postData)
	return postDataByte

}

// Get uuid of the VM which is to be cloned
func getVMUUid(vmObj, vmName string) (string, error) {
	fmt.Println("In get VM uuid ")
	vmNameUUidMap = make(map[string]string)
	vmData, err := basicGet(vmObj)
	if err != nil {
		fmt.Println("Error getting VM uuid")
		fmt.Println(err)
		log.Fatal()
	}
	vmNameJ := gjson.Get(vmData, "entities.#.name")
	vmUuidJ := gjson.Get(vmData, "entities.#.uuid")
	for ind1, name := range vmNameJ.Array() {
		for ind2, uuid := range vmUuidJ.Array() {
			if ind1 == ind2 {
				vmNameUUidMap[name.String()] = uuid.String()
			}
		}
	}
	return vmNameUUidMap[vmName], err
}

// Clone source VM using POST v2 call to the /clone endpoint
// requires vm uuid , clone api endpoint and clone Name
func cloneVM(cloneName, vmObj, vmUuid string) (string, int) {
	cloneByteData := enterCloneName(cloneName)
	peObj := "vms/" + vmUuid + "/clone"
	resp, code, _ := basicPost(peObj, cloneByteData)
	return resp, code
}

func main() {
	vmObj := "vms"
	vmUuid, err := getVMUUid(vmObj, vmName)
	fmt.Printf(`VM uuid for %s is %s \n`, vmName, vmUuid)
	if err != nil {
		fmt.Printf(`VM uuid for VM %s not found \n`, vmName)
		fmt.Println(err)
		log.Fatal()
	}
	fmt.Sprintf(`Cloning for VM %s %s`, vmName, vmUuid)
	for _, cloneName := range cloneNameList {
		resp, code := cloneVM(cloneName, vmObj, vmUuid)
		if code == 201 {
			fmt.Printf(`Http code %d: Clone %s created for %s \n`, code, cloneName, vmName)
			fmt.Println(resp)
		} else {
			fmt.Println("Clone not created refer HTTP response body below: ")
			fmt.Println(resp)
		}
	}
}
