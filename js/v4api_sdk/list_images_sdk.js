// list_images_sdk.js
//
// Code sample showing basic usage of the Nutanix v4 API SDK for JS
//
// This demo read configuration from config.json, connects to Prism Central,
// authenticates then returns a list of images.  The list is formatted to show
// image names and their size in bytes
//
// Requirements:
//
// - Prism Central pc.2022.6 or later

const sdk = require('@nutanix-api/vmm-js-client/dist/lib/index')
const client = new sdk.ApiClient()

const fs = require('fs')

// load the configuration from on-disk config.json
fs.readFile('./config.json', 'utf8', (err, data) => {
  if (err) {
    console.log(`Unable to load config from ./config.json: ${err}`)
  } else {
    // parse JSON string to JSON object
    const config = JSON.parse(data)

    // setup the connection configuration
    // for this demo, only Prism Central IP, username, password and debug mode are read from on-disk configuration
    client.host = config.pc_ip // IPv4/IPv6 address or FQDN of the cluster
    client.port = 9440 // Port to which to connect to
    client.username = config.username // UserName to connect to the cluster
    client.password = config.password // Password to connect to the cluster
    client.maxRetryAttempts = 1 // Max retry attempts while reconnecting on a loss of connection
    client.retryInterval = 1000 // Interval in ms to use during retry attempts
    client.verifySsl = false
    client.debug = config.debug

    console.log('Prism Central IP or FQDN: ' + client.host)
    console.log('Username: ' + client.username)

    const imagesApi = new sdk.ImagesApi(client)

    const imagesListOptions = {}
    imagesListOptions.$page = 0
    imagesListOptions.$limit = 20
    imagesListOptions.$filter = ''
    imagesListOptions.$orderBy = ''

    imagesApi.getImagesList(imagesListOptions).then(({ data, response }) => {
      console.log(data.resultsTotal + ' images found')
      data.getData().forEach(element => console.log('Image found with name "' + element.name + '", size bytes ' + element.sizeBytes))
    }).catch((err) => {
      console.log(`Error is ${err}`)
    })
  }
})
