/*
 * list_clusters_sdk.js
 *
 * Code sample showing basic usage of the Nutanix v4 API SDK for JS
 * 
 * This demo read configuration from config.json, connects to Prism Central,
 * authenticates then returns a list of registered clusters.  The list is formatted to show
 * cluster names and their extId
 *
 * Requirements:
 *
 * Prism Central 7.3 or later and AOS 7.3 later
*/

const sdk = require("@nutanix-api/clustermgmt-js-client/dist/lib/index");
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

		let clientApi = new sdk.ClustersApi(client);

		// setup request options
		var entityListOptions = new Object();
		entityListOptions.page = 0;
		entityListOptions.limit = 20;
		entityListOptions.filter = '';
		entityListOptions.orderBy = '';

		clientApi.listClusters(entityListOptions).then(({ data, response }) => {
			console.log(`API returned the following status code: ${response.status}`);
			data.getData().forEach(element => console.log('Cluster found with name "' + element.name + '"'))
		}).catch((err) => {
			console.log(`Error is ${err}`);
		})
	}
})
