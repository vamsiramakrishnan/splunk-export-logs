# Splunk-Export-Flow-Logs

## Introduction 
The Flow Logs of a VCN is central to any kind of debugging in the network and proves to be an extremely useful tool in understanding traffic flow patterns in the context of security as well.

![](https://github.com/vamsiramakrishnan/splunk-export-audit/blob/master/media/TheSimpleArchitecture.png)
A Scalable and Low Cost Splunk event exporter to publish OCI Audit Logs to Splunk.

## Components
-   The 'OCI Logging Service ' is required to enable flow logs for a given subnet.
-   The `OCI Events Service` is  queried for audit events every 2 minutes for all regions and all compartments relevant to the tenancy. 
-   The `OCI Functions` trigger a Function that enriches logs and publishes events to the Splunk HTTP Event Collector End point.
-   The `Splunk HTTP event Collector` is a simplified mechanism that splunk provides to publish events 

![](https://github.com/vamsiramakrishnan/splunk-export-audit/blob/master/media/SimpleRepresentation.png)

## Setup a Splunk Trial for Testing
* Splunk provides a 15 day Cloud trial and the capability to store about 5GB worth of event data that you forward/export to Splunk. Here's the link to sign-up [Splunk Sign Up](https://www.splunk.com/en_us/download.html)
* Select Splunk-Cloud, provide your data and Login to Splunk. 
* To setup the HTTP Event Collector which we leverage, the solution refer to link [Setup HTTP event collector](https://docs.splunk.com/Documentation/Splunk/8.0.2/Data/UsetheHTTPEventCollector)
* Points to note 

## Design Goals 
``` 
Self Perpetuating
Event driven 
Scalable 
Low-Cost
Zero maintenance
```

## Quickstart For Setup On OCI Side
This quickstart assumes you have working understanding of basic principles of OCI around IAM | Networking and you know how to get around the OCI Console. 

### Create Compartments and Groups
- `Burger-Menu` --> `Identity` --> `Compartments | Users | Groups`
1. Create a Compartment `splunk-export-compartment`
2. Create a Group  `splunk-export-users`
3. Add `Required User` to group `splunk-export-users`
4. Create a Dynamic Group `splunk-export-dg`
5. Write appropriate IAM Policies at the tenancy level and compartment level.

### Create a Dynamic Group
- `Burger-Menu` --> `Identity` --> `Dynamic Groups`
 - Create a Dynamic Group `splunk-export-dg` Instances that meet the criteria defined by any of these rules will be included in the group.
```
ANY {instance.compartment.id = [splunk-export-compartment OCID]}
ANY {resource.type = 'ApiGateway', resource.compartment.id =[splunk-export-compartment OCID]}
ANY {resource.type = 'fnfunc', resource.compartment.id = [splunk-export-compartment OCID]}
```

### Create Tenancy IAM policy - Splunk Export Group 
- `Burger-Menu` --> `Identity` --> `Policies`
 - Create an IAM Policy `splunk-export-tenancy-policy` with the following policy statements in the `root` compartment 
```
Allow group splunk-export-users to manage repos in tenancy
Allow group splunk-export-users to read audit-events in tenancy
Allow group splunk-export-users to read tenancies in tenancy
Allow group splunk-export-users to read compartments in tenancy
Allow service FaaS to read repos in tenancy
```

###  Create Tenancy IAM policy - Splunk Export Dynamic Group 
- `Burger-Menu` --> `Identity` --> `Policies`
 - Create an IAM Policy `splunk-export-dg-tenancy-policy` with the following policy statements in the `root` compartment 
```
Allow dynamic-group splunk-export-dg to read audit-events in tenancy
Allow dynamic-group splunk-export-dg to read tenancies in tenancy
Allow dynamic-group splunk-export-dg to read compartments in tenancy
```

### Create Compartment Level IAM Policy
- `Burger-Menu` --> `Identity` --> `Policies`
Create an IAM Policy `splunk-export-compartment-dg-policy` inside the compartment `splunk-export-compartment`
```
Allow service FaaS to use all-resources in compartment splunk-export-compartment
Allow dynamic-group splunk-export-dg to use ons-topics in compartment splunk-export-compartment
Allow dynamic-group splunk-export-dg to use stream-pull in compartment splunk-export-compartment
Allow dynamic-group splunk-export-dg to use stream-push in compartment splunk-export-compartment
Allow dynamic-group splunk-export-dg to use virtual-network-family in compartment splunk-export-compartment
```

### Create a VCN, Subnet & Security Lists
- `Burger-Menu` --> `Networking` --> `Virtual Cloud Networks`
 - Use VCN Quick Start to Create a VCN `splunk-export-vcn` with Internet.
 - Connectivity Go to Security List and Create a `Stateful Ingress Rule` in the `Default Security list` to allow Ingress Traffic in  `TCP 443`
 - Go to Default Security List and verify if a `Stateful Egress Rule` is available in the `Default Security List` to allow egress traffic in  `all ports and all protocols`

### Create a Function Application
- `Burger-Menu` --> `Developer Services` --> `Functions`
 - Create a Function Application `splunk-export-app` in the compartment `splunk-export-compartment` while selecting `splunk-export-vcn` and the `Public Subnet`
 - Setup Papertrail / OCI Logging Service to debug Function executions if required.  [Setup PaperTrail](https://papertrailapp.com/) , check them out. 

### Create a  OCIR Repo

 - Create a  `Private` Repository `splunk-export-repo`

### Configure Cloud Shell
15. Setup Cloud Shell in your tenancy - [Link](https://docs.cloud.oracle.com/en-us/iaas/Content/API/Concepts/cloudshellgettingstarted.htm?TocPath=Developer%20Tools%20%7C%7CUsing%20Cloud%20Shell%7C_____0)
16. Clone the Repo in the cloud shell
    `git clone https://github.com/vamsiramakrishnan/splunk-export-audit.git`
17. Login to your region's docker login `iad.ocir.io` with appropriate credentials 

###  Create & Set Fn Context 
```
fn create context splunk-export-context --provider oracle
fn use context splunk-export-context`
```
### Update the Context 
```
fn update context oracle.compartment-id [splunk-export-compartment-ocid]
fn update context api-url https://functions.[region-name].oraclecloud.com
fn update context registry [YOUR-TENANCY-NAMESPACE]/[splunk-export-repo]
```

### Deploy the Functions
Each folder within the repo represents a function , go to each folder and deploy the function using the the `fn --verbose deploy `
```
cd splunk-export-audit
cd list-regions
fn --verbose deploy splunk-export-app list-regions

cd fetch-audit-events
fn --verbose deploy splunk-export-app fetch-audit-events

cd publish-to-splunk
fn --verbose deploy splunk-export-app publish-to-splunk
```
The Deploy Automatically Triggers an Fn Build and Fn Push to the Container registry repo setup for the functions.

### Create  an API Gateway 
* `Burger-Menu` --> `Developer Services` --> `API Gateway`
 * Create an API Gateway `splunk-export-apigw` in the compartment `splunk-export-compartment`while selecting `splunk-export-vcn` and the `Public Subnet`

### Create API Gateway Deployment Endpoints
Map the endpoint as follows 
 Deployment Name | Prefix| Method | Endpoint | Fn-Name
--|--|--|--|--|
 list-regions | regions | GET | /listregions |  list-regions|

```
Note:The API Gateway is setup in this example with HTTPS without an Auth Mechanism , but this can be setup with an authorizer Function , that works with a simple Token mechanism
```
### Create Notification Channels 
- `Burger-Menu` --> `Application Integration` --> `Notifications`
- Create two notification channels `splunk-fetch-audit-event`  `splunk-publish-to-splunk`. Create subscriptions to Trigger the Functions

### Create Streaming
- `Burger-Menu` --> `Analytics` --> `Streaming`
```
Note: Using a Single Partition and Single Streaming endpoint for Audit, Can scale based on requirements
```
| Stream Attribute |  value | 
|------------------|--------|
| stream-name| splunk-export-stream |
| retention-period | 24 Hours | 
| partitions | 1 | 
| stream-pools | default-stream-pool |



### Set the Environment Variables for Each Function
These environment variables help call other functions. One after the other. 


| Fn-Name |Parameter Name  |  Description|  Example |
|--|--|--|--| 
|list-regions| records_per_fn | Batch Size of Number of Events to be processed in one go by the Next Fn | 50
|list-regions| audit_topic| OCID of Notifications topic used to trigger and notify the Fn fetch-audit-events  | ocid1.onstopic.oc1.phx.aaaaaaaa
|list-regions | stream_ocid| OCID of the Stream used to Publish the list of compartments and regions from where Audit events will be fetched | ocid1.stream.oc1.phx.amaaaaaa
|list-regions | streaming_endpoint| Endpoint of Streaming, depends on which region you provision Streaming | ocid1.stream.oc1.phx.amaaaaaa
|fetch-audit-events | records_per_fn| Batch Size of Number of Events to be processed in one go by the Next Fn | 30
|fetch-audit-events | splunk_topic| OCID of the Topic used to Notify& Trigger the publish-to-splunk Function| ocid1.onstopic.oc1.phx.aaaaaaaa
|fetch-audit-events | stream_ocid| OCID of the Stream used to Publish the actual Audit Event payload | ocid1.stream.oc1.phx.amaaaaaa
|fetch-audit-events | streaming_endpoint| Endpoint of Streaming, depends on which region you provision Streaming | ocid1.stream.oc1.phx.amaaaaaa
|publish-to-splunk| source_source_name| The Source Name that you would like Splunk to see | oci-hec-event-collector
| publish-to-splunk| source_host_name| The Source Hostname that you would like Splunk to see | oci-audit-logs
|publish-to-splunk| splunk_url| The Splunk Cloud URL ( Append input to the beginning of your splunk cloud url, do not add any http/https etc.  | input-prd-p-hh6835czm4rp.cloud.splunk.com
|publish-to-splunk| splunk_hec_token| The Token that is unqiue to that HEC  | TOKEN
|publish-to-splunk| splunk_index_name| The index into which you'd like these logs to get aggregated | main
|publish-to-splunk| stream_ocid| OCID of the Stream used to Publish the actual Audit Event payload | ocid1.stream.oc1.phx.amaaaaaa
|publish-to-splunk| streaming_endpoint| Endpoint of Streaming, depends on which region you provision Streaming | ocid1.stream.oc1.phx.amaaaaaa

## Invoke and Test !
Invoke Once and the loop will stay active as long as the tenancy does continuously pushing events to Splunk . 
```
curl --location --request GET '[apigateway-url].us-phoenix-1.oci.customer-oci.com/regions/listregions'
```
If all is well in papertrail/ oci-function-logs/metrics, proceed.
## Health Checks for Scheduled Trigger
Create a `Health Check` named `splunk-export-health-check` with the following settings 
### Target Settings
Get the API-Gateway URL where the list-regions Fn is deployed. 
**Example**
``` https://<Random-Alphanumeric-String>.apigateway.us-phoenix-1.oci.customer-oci.com/regions/listregions```
Copy the String  `<Random-Alphanumeric-String>.apigateway.us-phoenix-1.oci.customer-oci.com` and ignore the rest
### Other Health Check Settings
| Field | Setting |
|-------|---------|
|Vantage Point| *Select any One* | 
| Request Type | HTTP | 
| Protocols | HTTPS | 
| Port | 443 | 
| Path | /regions/listregions | 
| Timeout | 30s |
| Interval | 5 Min | 
| Method | GET |

```
Note:The API Gateway is setup in this example with HTTPS without an Auth Mechanism , but this can be setup with an authorizer Function , that works with a simple Token mechanism.If Auth is setup , the token can be specified in the Header of the Health Check.
```


