/*
 * create_image_sdk.js 
 *
 * Code sample showing basic usage of the Nutanix v4 API SDK for JS
 * 
 * This demo reads configuration from config.json, connects to Prism Central,
 * authenticates then creates a Prism Central disk image.
 *
 * Requirements:
 *
 * Prism Central 7.3 or later and AOS 7.3 later
*/

const sdk = require("@nutanix-api/vmm-js-client/dist/lib/index");
let client = new sdk.ApiClient();

client.addDefaultHeader("Accept-Encoding","gzip, deflate, br");

const fs = require('fs');

// load the configuration from on-disk config.json
fs.readFile('./config.json', 'utf8', (err, data) => {
	if (err) {
		console.log(`Unable to load config from ./config.json: ${err}`);
	} else {
		// parse JSON string to JSON object
		const config = JSON.parse(data);

		// setup the connection configuration
		// for this demo, only Prism Central IP, port, username, password and debug mode are read from on-disk configuration
		// Prism Central IPv4/IPv6 address or FQDN
		client.host = config.pc_ip;
		// HTTP port for connection
		client.port = config.pc_port;
		// connection credentials
		client.username = config.username;
		client.password = config.password;
		// don't verify SSL certificates; not recommended in production
		client.verifySsl = false;
		// show extra debug info during demo
		client.debug = config.debug;
		client.cache = false;

		console.log(`Prism Central IP or FQDN: ${client.host}`);
		console.log(`Username: ${client.username}`);
                console.log(`Image will be created from: ${config.image_url}`);

		let clientApi = new sdk.ImagesApi(client);

                image_payload = {
                    name: "rocky10cloud_js_sdk",
                    type: "DISK_IMAGE",
                    description: "Rocky Linux 10 Cloud Image from v4 JS SDK",
                    source: {
                        url: config.image_url,
                        $objectType: "vmm.v4.content.UrlSource"
                    },
                    clusterLocationExtIds: [
                        config.cluster_extid
                    ]
                }

		clientApi.createImage(image_payload).then(({ data, response }) => {
			console.log(`API returned the following status code: ${response.status}`);
			console.log(data.getData())
		}).catch((err) => {
			console.log(`Error is ${err}`);
		})
	}
})
