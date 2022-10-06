// list_images_sdk.go
//
// Code sample showing basic usage of the Nutanix v4 API SDK for Go(lang)
//
// This demo connects to Prism Central, authenticates then returns a list of images,
// displays the image names and their size in bytes
//
// Requirements:
//
// - Prism Central pc.2022.6 or later

package main

import (
    "fmt"
    "os"
    "flag"
    "reflect"
    "github.com/nutanix/ntnx-api-golang-clients/vmm-go-client/v4/api"
    "github.com/nutanix/ntnx-api-golang-clients/vmm-go-client/v4/client"
    v4sdkimages "github.com/nutanix/ntnx-api-golang-clients/vmm-go-client/v4/models/vmm/v4/images"
    v4sdkerror "github.com/nutanix/ntnx-api-golang-clients/vmm-go-client/v4/models/vmm/v4/error"
    "golang.org/x/term"
)

var (
    ApiClientInstance *client.ApiClient
    ImagesApiInstance *api.ImagesApi
)

func main() {

    // setup the accepted command line arguments
    pc_ip := flag.String("pc_ip", "undefined", "Prism Central IP or FQDN")
    username := flag.String("username", "undefined", "Prism Central Username")
    debug := flag.Bool("debug", false, "Enable/disable some extra debug info")
    flag.Parse()
    
    // make sure the user has provided both Prism Central IP address/FQDN and username
    if *pc_ip == "undefined" || *username == "undefined" {
        fmt.Println("Please make sure you have specified both pc_ip and username.  Usage example:")
        fmt.Println("go run list_images_sdk.go -pc_ip=10.10.10.10 -username=admin")
        panic("Insufficient command line arguments; exiting")
    }

    // show some intro info i.e. PC IP and username provided by the user
    fmt.Println("Prism Central IP or FQDN:", *pc_ip)
    fmt.Println("Username:", *username)

    // accept a hidden password from the user
    fmt.Print("Enter your Prism Central password (won't be shown on screen): ")
    password, err := term.ReadPassword(int(os.Stdin.Fd()))
    if err != nil {
        panic(err)
    }

    // not recommended; uncomment this line to show the entered password in the terminal
    // really only useful for debugging e.g. if a password is entered that causes some sort of issue
    // fmt.Println("Password:", string(password))

    // create the API client instance and configure connection parameters
    ApiClientInstance = client.NewApiClient()
    ApiClientInstance.Host = *pc_ip
    ApiClientInstance.Port = 9440
    ApiClientInstance.RetryInterval = 100
    ApiClientInstance.MaxRetryAttempts = 2
    ApiClientInstance.VerifySSL = false
    ApiClientInstance.Username = *username
    ApiClientInstance.Password = string(password)
    // debug property is set to true or false depending on use of -debug command line argument
    // defaults to false
    ApiClientInstance.Debug = *debug

    ImagesApiInstance = api.NewImagesApi(ApiClientInstance)

    page := 0
    limit := 20
    filter := ""
    orderBy := ""
    
    // attempt to get the list of images
    response, err := ImagesApiInstance.GetImagesList(&page, &limit, &filter, &orderBy)
    // these errors, if present, can include authentication and connection/timeout issues
    if err != nil {
         fmt.Println("Request failed:")
         panic(err)
    }

    // if debug mode is enabled, show some extra debug info
    if ApiClientInstance.Debug {
        fmt.Println("--- Debug info starts ---")
        fmt.Println("*ImagesApiInstance is type", reflect.TypeOf(*ImagesApiInstance))
        fmt.Println("*response.Metadata is type", reflect.TypeOf(*response.Metadata))
        fmt.Println("*response.Data is type", reflect.TypeOf(*response.Data))
        fmt.Println("Length of response.Metadata.Links list is", len(response.Metadata.Links))
        for i := 0; i < len(response.Metadata.Links); i++ {
            fmt.Println(*response.Metadata.Links[i].Href)
        }
        fmt.Println("--- Debug info ends ---")
    }

    // show the number of images
    fmt.Printf("%d images found\n", *response.Metadata.TotalAvailableResults)

    data := response.GetData()
    resultImages, ok := data.([]v4sdkimages.Image)
    // make sure no errors were found before trying to display the list of images
    if !ok {
        // we don't have images i.e. it is an error; do something with the error
        err := data.(*v4sdkerror.ErrorResponse)
        panic(err)
    }

    // if a list of images was found, iterate over and display info about them
    for _, value := range resultImages {
        // show info about the image's name and size in bytes
        fmt.Printf("Image found with name \"%v\", size bytes %v\n", *value.Name, *value.SizeBytes)
    }

    fmt.Println("Done!")

}
