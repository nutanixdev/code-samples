/**
 *
 * IMPORTANT NOTE: To run this application you will need to add a reference to System.Web.Extensions
 * Please see the repository readme for instructions on how to do this, if you haven't already done so
 *
*/

using System;
using Newtonsoft.Json;
using System.IO;
using System.Net;
using System.Text;
using System.Web.Script.Serialization;

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
                Payload = "{\"kind\":\"vm\",\"length\":500}",
                Method = "POST"
            };

            RESTClient Client = new RESTClient(Parameters);

            HttpWebResponse HttpResponse = null;

            /**
             * first we'll send a request that we can use to find out how many VMs are
             * in this cluster
             * if the number of VMs on the cluster is >500, we'll run additional requests
             * later to handle them in groups of <=500
            */

            /**
             * the RESTClient.SendRequest method contains basic exception handling
             * you should modify this to avoid catching generic exceptions,
             * if you plan to use any of this in your own apps
             *
             * this note is here for those wondering why there's no try/catch handling
             * around the send request action below
            */

            RequestResponse CountVmRequest = new RequestResponse();
            /**
             * send the request
            */
            CountVmRequest = Client.SendRequest();

            /**
             * process the response
             * at this time we're just counting the VMs and, based on the number of VMs
             * in the cluster, will either show them all or make subsequent requests to
             * get the remaining VMs
            */

            /**
             * if the response code isn't 1, something went wrong
             * in this basic demo, 1 is successful, 99 is failure
             * these custom codes are returned from the RESTClient.SendRequest() method
             * we are also handling exceptions in the RESTClient.SendRequest() - please see
             * that method for details on how exceptions are handled
            */
            if (CountVmRequest.Code == 99)
            {
                Console.WriteLine("Error code 99 indicates the API request either failed or returned an invalid/unexpected response.  Additional information follows.\n");
                Console.WriteLine(CountVmRequest.Message);
                Console.WriteLine(CountVmRequest.Details);
            }
            else
            {
                var JsonSerializer = new JavaScriptSerializer();
                dynamic JsonObject = JsonSerializer.Deserialize<dynamic>(CountVmRequest.Message);

                /**
                 * grab the number of VMs from this initial request
                 * we'll use this number to calculate how many interations
                 * to make in upcoming requests
                */
                int VmCount = Convert.ToInt16(JsonObject["metadata"]["total_matches"]);
                Console.WriteLine("Total VMs in this cluster: " + VmCount);
                Console.WriteLine("Total VMs in this request (iteration #0): " + Convert.ToInt16(JsonObject["metadata"]["length"]));

                /**
                 * the nutanix "vms" API will only ever return 500 VMs
                 * this will apply even if the "length" parameter is set to a value >500
                */
                if (VmCount >= 500)
                {

                    /**
                     * at this point you would "do something" based on knowing there are
                     * >500 VMs in the cluster
                     *
                     * for example, you could iterate over the VMs, collecting the necessary information, etc
                     *
                     * for our demo, we've already got a response containing
                     * information about the first 500 VMs so there's no need
                     * to submit a request for the first 500 again (expensive and unnecessary)
                    */
                    Console.WriteLine("There are more than 500 VMs in this cluster.");
                    Console.WriteLine("Multiple iterations/requests are required to collect all VM information.");

                    /**
                     * by immediately setting the offset to 500, subsequent requests
                     * will start from VM at index 501 and go forward from there
                     * again, we've already got the response above for the first 500 VMs
                     *
                     * we're using chunks of 500 VMs here, but in a real app there's no
                     * reason why this chunk needs to be 500
                     * note, however, the 500 is the MAXIMUM number of VMs returned in a
                     * single request
                    */
                    int MaxVmsInResponse = 500;
                    int Offset = MaxVmsInResponse;

                    /**
                     * work out how many interations are required
                     * simple math based on the number of times a 500 VM response will be received
                    */
                    int Iterations = VmCount / MaxVmsInResponse;
                    Console.WriteLine("Total iterations required, including the initial request: " + (Iterations + 1));

                    /**
                     * starting at 1 here because we've already completed iteration "0"
                    */
                    for (int Iterator = 1; Iterator <= Iterations; Iterator++)
                    {
                        RequestParameters IterationParameters = new RequestParameters()
                        {
                            URI = "https://" + ClusterIp + ":9440/api/nutanix/v3/vms/list",
                            Username = ClusterUsername,
                            Password = ClusterPassword,
                            Payload = "{\"kind\":\"vm\",\"length\":500,\"offset\":" + Offset + "}",
                            Method = "POST"
                        };

                        /**
                         * reuse the previous RESTClient instance
                        */
                        Client.Parameters = IterationParameters;
                        RequestResponse IterationRequest = Client.SendRequest();

                        dynamic IterationJsonObject = JsonSerializer.Deserialize<dynamic>(IterationRequest.Message);
                        int IterationVmCount = Convert.ToInt16(IterationJsonObject["metadata"]["length"]);
                        Console.WriteLine("Total VMs in this request (iteration #" + Iterator + "): " + IterationVmCount);
                        Offset = Offset + MaxVmsInResponse;
                    }
                }
                else
                {
                    /**
                     * at this point you would "do something" based on there being
                     * <500 VMs in the cluster
                     *
                     * iterate over the VMs, collecting the necessary informatin, etc
                    */
                    Console.WriteLine("There are fewer than 500 VMs in this cluster.");
                    Console.WriteLine("Only a single iteration/request is required to collect all VM information.");

                    /**
                     * do something useful here
                     * this isn't an unintentional comment - it's where you'd do something useful  :)
                    */
                }
            }

            /**
             * make sure we clean up after ourselves
            */
            if (HttpResponse != null)
            {
                ((IDisposable)HttpResponse).Dispose();
            }
            /**
             * wait for the user to press a key
             * this is only here because there's an assumption/guess that, initially at least,
             * this small demo app will be run inside Visual Studio
            */
            Console.WriteLine("\nPress any key to exit.");
            Console.ReadKey();

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
    }

    /*
     * class to hold the responses from our requests
     * this isn't strictly necessary but does package things nicely
    */
    class RequestResponse
    {

        public int Code { get; set; }
        public string Message { get; set; }
        public string Details { get; set; }

    }

    /*
     * class to manage all our request criteria and carry out the request itself
     * we're doing it this was as the app will make multiple requests and we don't
     * want to duplicate code unnecessarily
    */
    class RESTClient
    {

        public RESTClient(RequestParameters Parameters)
        {
            this.Parameters = Parameters;
        }

        public RequestParameters Parameters;

        public RequestResponse SendRequest()
        {

            /*
                * for the purposes of this demo, many Nutanix clusters will still use self-signed certificates
                * if SSL errors are not ignored, connections will be refused since we aren't automatically accepting self-signed certs in this app
            */

            ServicePointManager.ServerCertificateValidationCallback = ((sender, certificate, chain, sslPolicyErrors) => true);
            ServicePointManager.Expect100Continue = true;
            ServicePointManager.SecurityProtocol = SecurityProtocolType.Tls12;

            RequestResponse Response = new RequestResponse();
            HttpWebResponse HttpResponse = null;

            try
            {

                var request = (HttpWebRequest)WebRequest.Create(Parameters.URI);
                request.Method = Parameters.Method;

                /*
                    * this section only applies if the user as selected to send a POST request
                    * if the POST method is selected, we also need to process and send the POST body
                */
                if (Parameters.Method != "GET")
                {
                    var requestBody = Encoding.ASCII.GetBytes(Parameters.Payload);
                    var newStream = request.GetRequestStream();
                    newStream.Write(requestBody, 0, requestBody.Length);
                    newStream.Close();
                }

                /*
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

                /*
                    * make sure the request doesn't sit there forever ...
                    * set this to a more appropriate value if accessing API URIs over slow/high-latency connections (e.g. VPN)
                */
                request.Timeout = 5000;

                HttpResponse = (HttpWebResponse)request.GetResponse();
                using (Stream HttpResponseStream = HttpResponse.GetResponseStream())
                {
                    if (HttpResponseStream != null)
                    {
                        using (StreamReader reader = new StreamReader(HttpResponseStream))
                        {
                            Response.Code = 1;
                            Response.Message = reader.ReadToEnd();
                        }
                    }
                }
            }
            catch (System.Net.WebException ex)
            {
                /**
                 * network error, request properties, auth errors
                */
                Response.Code = 99;
                Response.Message = "An error occurred while making the request (e.g. network, request properties, authentication).";
                Response.Details = "{\"errors\":[\"" + ex.Message.ToString() + "\"]}";
            }
            catch (System.Net.ProtocolViolationException ex)
            {
                /**
                 * payload error, e.g. malformed JSON body
                */
                Response.Code = 99;
                Response.Message = "A payload/request body error occurred while making the request.";
                Response.Details = "{\"errors\":[\"" + ex.Message.ToString() + "\"]}";
            }
            catch (Exception ex)
            {
                /**
                 * don't catch generic "Exception" in production ...
                */
                Response.Code = 99;
                Response.Message = "An unhandled exception occurred while making the request.";
                Response.Details = "{\"errors\":[\"" + ex.Message.ToString() + "\"]}";
            }
            finally
            {
                if (HttpResponse != null)
                {
                    ((IDisposable)HttpResponse).Dispose();
                }
            }

            return Response;
        }

    }

}
