/*
Send Batch calls or multiple requests in one API Call using v3 API batch endpoint
This script uses a JSON file "batch_requests.json".
If the file is in the same directory as the go binary the code can be run as is
You can also have the code point to a file using
$ go run batchapi.go -file=<filepath/filename>
or
$ ./batchapi -file=<filepath/filename>
Two batch calls in JSON file; 1st creates a basic VM , 2nd call creates an Image from URL
*/
package main

import (
	"bytes"
	"crypto/tls"
	"flag"
	"fmt"
	"io/ioutil"
	"log"
	"net/http"

	"github.com/tidwall/gjson"
)

const (
	pcUser string = "admin"            // PC User
	pcPass string = "<PC UI password>" // PC Password
	pcIp   string = "<PC VIP>:9440"    // PC Cluster VIP
	pcUrl  string = "/api/nutanix/v3"  // URL for v2 API
	pcObj  string = "/batch"           // endpoint for batch calls
)

// Error handling function
func exitOnError(msg string, err error) {
	if err != nil {
		fmt.Println(msg)
		fmt.Println(err)
		log.Fatal()
	}
}

// Basic Post request function for posting data using v3 POST calls
func basicPost(pcObj string, jsonByteData []byte) (string, int, error) {
	var bodyTextStr string
	var httpCode int
	tr := &http.Transport{
		TLSClientConfig: &tls.Config{InsecureSkipVerify: true},
	}
	client := &http.Client{Transport: tr}
	URL := "https://" + pcIp + pcUrl + pcObj
	fmt.Println(fmt.Sprintf(`Posting data to URL: %s`, URL))
	payloadData := bytes.NewBuffer(jsonByteData)
	req, err := http.NewRequest("POST", URL, payloadData)
	req.Header.Set("Content-Type", "application/json")
	req.SetBasicAuth(pcUser, pcPass)
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

func main() {

	// Use flag to get value for filename from cli
	// Default filename is batch_requests.json in the same location as the go code.
	fileName := flag.String("file", "batch_requests.json", "filename for batch request payload")
	flag.Parse()

	// Read JSON File
	requestByteData, err := ioutil.ReadFile(*fileName)
	exitOnError("Error in accessing file", err)

	// Convert read byte value to string for GJSON
	requestString := string(requestByteData)

	// Extract the payload to be sent in the post call
	result := gjson.Get(requestString, "batch_details")

	// Convert JSON payload to byte array for POST call
	batchPayload := []byte(result.String())

	resp, code, err := basicPost(pcObj, batchPayload)
	exitOnError("Error in sending POST Call", err)

	// Condition when request was successful
	if code == 200 {
		statusCodes := gjson.Get(string(resp), "api_response_list.#.status")
		for ind, code := range statusCodes.Array() {
			if code.Int() == 202 {
				fmt.Println("Request Successful; Entity Created")
			} else {
				fmt.Printf("Status code for entity %d: %d\n", ind, code.Int())
			}
		}
	} else {
		fmt.Println("HTTP request not successful")
		fmt.Printf("HTTP status Code %d\n", code)
		fmt.Printf("HTTP Response body %s\n", string(resp))
	}

}
