using System;
using Newtonsoft.Json;
using System.IO;
using System.Net;
using System.Text;

namespace ConsoleApp1
{
    class Program
    {
        static void Main(string[] args)
        {

            /**
             * hard-coded password here - you'd need to do this properly in production
            */
            string ClusterUsername = "admin";
            string ClusterPassword = "nutanix/4u";
            string ClusterIp = "10.0.0.1";

            /**
             * instance of our RequestParameters class
             * done this way purely to nicely package the request parameters__
             *
             * important note - the current v3 API will return a MAXIMUM of 500 VMs for any single request,
             * regardless of the value specified for "length"
             *
             * to collect a list of all VMs on systems with >500 VMs, please use a
             * combination of the 'length' and 'offset' parameters.
             *
             * for example, {"kind":"vm","length":500,"offset":501} on a cluster with
             * 517 VMs would return a list of 15 VMs i.e. VMs from 501-516, excluding CVM
            */
            RequestParameters Parameters = new RequestParameters()
            {
                URI = "https://" + ClusterIp + ":9440/api/nutanix/v3/vms/list",
                Username = ClusterUsername,
                Password = ClusterPassword,
                Payload = "{\"kind\":\"vm\"}",
                Method = "POST",
                Timeout = 5000
            };

            /**
             * disable verification of SSL certificates
             * this is for DEMO purposes only
             * don't do this in production!
             * it's only here now because many Nutanix clusters still use the default
             * self-signed certificate
            */
            ServicePointManager.ServerCertificateValidationCallback = ((sender, certificate, chain, sslPolicyErrors) => true);
            ServicePointManager.Expect100Continue = true;
            ServicePointManager.SecurityProtocol = SecurityProtocolType.Tls12;

            HttpWebResponse HttpResponse = null;

            /**
             * setup our request and configure the various properties we'll need to make the request
             * this is done using the parameters we setup at the top of this CS file
            */
            var request = (HttpWebRequest)WebRequest.Create(Parameters.URI);
            request.Method = Parameters.Method;
            request.Timeout = Parameters.Timeout;

            /**
             * setup the request headers
             *
             * for this app, we are only worried about the authentication type (Basic)
             * and the valid encoding (application/json for Nutanix clusters)
            */
            String authHeader = System.Convert.ToBase64String(System.Text.ASCIIEncoding.ASCII.GetBytes(Parameters.Username + ":" + Parameters.Password));
            request.Headers.Add("Authorization", "Basic " + authHeader);
            request.Headers.Add("Accept-Encoding", "application/json");
            request.ContentType = "application/json";
            request.Accept = "application/json";

            /**
             * extremely basic exception handling
             * you'll need to do this properly e.g. don't just catch generic exceptions
            */
            try
            {
                /**
                 * setup the request body (payload)
                 * this demo, by default, tells the Prism REST API v3 to look for entities of kind "vm"
                */
                var requestBody = Encoding.ASCII.GetBytes(Parameters.Payload);
                var newStream = request.GetRequestStream();
                newStream.Write(requestBody, 0, requestBody.Length);
                newStream.Close();

                HttpResponse = (HttpWebResponse)request.GetResponse();

                /**
                 * process the response
                 * for this demo, we'll just dump the entire response to the screen
                 * in reality you'll want to do something with it
                */
                using (Stream HttpResponseStream = HttpResponse.GetResponseStream())
                {
                    if (HttpResponseStream != null)
                    {
                        using (StreamReader reader = new StreamReader(HttpResponseStream))
                        {
                            DisplayResponse(reader.ReadToEnd());
                        }
                    }
                }

                /**
                 * here is an example of getting the cluster name from a request to GET /api/nutanix/v2.0/cluster
                 *
                 * NutanixCluster cluster = JsonConvert.DeserializeObject<NutanixCluster>(Response.Message);
                 * DisplayResponse("{\"cluster\":{\"name\":\"" + cluster.Name.ToString() + "\",\"version\":\"" + cluster.Version.ToString() + "\"}}");
                */

            }
            catch ( System.Net.WebException ex )
            {
                Console.WriteLine("An error occurred while making the request (e.g. network, request properties, authentication).");
                Console.WriteLine(ex.Message.ToString());
            }
            catch( System.Net.ProtocolViolationException ex )
            {
                Console.WriteLine("A payload/request body error occurred while making the request.");
                Console.WriteLine(ex.Message.ToString());
            }
            finally
            {
                /**
                 * if we got a response from the request, make sure we clean up behind ourselves
                */
                if (HttpResponse != null)
                {
                    ((IDisposable)HttpResponse).Dispose();
                }
                Console.WriteLine("Press any key to exit.");
                /**
                 * wait for the user to press a key
                 * this is only here because there's an assumption/guess that, initially at least,
                 * this small demo app will be run inside Visual Studio
                */
                Console.ReadKey();
            }

        }

        /**
         * take a string, run it through JsonPrettify and show the response in the txtResponse textbox
        */
        private static void DisplayResponse(string DebugText)
        {
            try
            {
                Console.WriteLine(JsonPrettify(DebugText) + Environment.NewLine + Environment.NewLine);
            }
            catch (Exception ex)
            {
                Console.WriteLine(ex.Message.ToString() + Environment.NewLine);
            }
        }

        /**
         * Take a JSON-formatted string and "prettify" it i.e. insert new line and tab characters where appropriate
         * from https://stackoverflow.com/questions/2661063/how-do-i-get-formatted-json-in-net-using-c
        */
        private static string JsonPrettify(string json)
        {
            using (var stringReader = new StringReader(json))
            using (var stringWriter = new StringWriter())
            {
                var jsonReader = new JsonTextReader(stringReader);
                var jsonWriter = new JsonTextWriter(stringWriter) { Formatting = Formatting.Indented };
                jsonWriter.WriteToken(jsonReader);
                return stringWriter.ToString();
            }
        }
    }

    /**
     * basic class to manage our request parameters
     * this app could easily be written without "packaging" this way,
     * but it is nice and clean for those that want to extend
     * this app later
    */
    class RequestParameters
    {
        public String URI;
        public String Username;
        public String Password;
        public String Payload;
        public String Method;
        public int Timeout;
    }

}
