# Splunk-Export-Flow-Logs

![](media/DataFlowArchitecture.png)

## Introduction

The Flow Logs of a VCN is central to any kind of debugging in the network and proves to be an extremely useful tool in understanding traffic flow patterns in the context of security as well.

## Design Goals

```
Event driven
Scalable
Low-Cost
Zero maintenance
Secure
Least Privilege Access
```

![Architecture](media/architecture.png)

## Components

- The `VCN Flow Logs` are what helps understand the flow of network traffic in a given subnet.
- The `OCI Logging Service` is required to enable flow log collection and storage for a given subnet. The OCI Logging service can be used to collect logs for other Oracle Cloud Native Services as well.
- The `OCI Events Service` is used to trigger Functions every time the Logging service creates an object with the flow logs of a given Subnet.
- The `OCI Functions` trigger a Function that enriches flow-logs and publishes events to the Splunk HTTP Event Collector End point.
- The `Splunk HTTP Event Collector` is a simplified mechanism that splunk provides to publish events in a standard format

![Basic Concepts](./media/basicConcepts.png)

## Other Concepts

- [VCN](https://docs.cloud.oracle.com/en-us/iaas/Content/Network/Concepts/overview.htm) Flow Logs are generated for every subnet.
- The [Subnet](https://docs.cloud.oracle.com/en-us/iaas/Content/General/Concepts/regions.htm#one) is a regional resource and therefore this has to be setip for every region your tenancy is subscribed to.
- The architecture uses Logging service that populates logs of a given resource in the Object Storage of a compartment.
- Event Service Triggers are scoped to a given compartment , so it is necessary to configure logging to populate logs in a single compartment.
- If there is a requirement to have the logs populated in multiple compartments eg. **PROD**, **UAT** etc. or , you would have to create as many events as there are compartments where VCN Flow Logs are written.

## Flow Log Enrichment Functionality

**Raw Log**

```
HEADERS
--------
<version> <srcaddr> <dstaddr> <srcport> <dstport> <protocol> <packets> <bytes> <start_time> <end_time> <action> <status>

2 172.16.2.145 172.16.2.179 82 64 13 112 441 1557424462 1557424486 REJECT OK
```

**Enriched JSON**

```
{
    "version": "",
    "srcaddr": "-",
    "dstaddr": "-",
    "srcport": "-",
    "dstport": "-",
    "protocol": "-",
    "packets": "-",
    "bytes": "-",
    "start_time": "",
    "end_time": "
    "status": "",
    "compartmentId": "",
    "compartmentName": "",
    "availabilityDomain": "",
    "vcnId": "",
    "vcnName": "",
    "subnetId": "",
    "subnetName": "",
    "vnicId": "",
    "vnicName": "",
    "securityListIds": [""],
    "securityListNames": [""],
    "nsgIds": [],
    "nsgNames": []
}
```

## Setup a Splunk Trial for Testing

- Splunk provides a 15 day Cloud trial and the capability to store about 5GB worth of event data that you forward/export to Splunk. Here's the link to sign-up [Splunk Sign Up](https://www.splunk.com/en_us/download.html)
- Select Splunk-Cloud, provide your data and Login to Splunk.
- To setup the HTTP Event Collector which we leverage, the solution refer to link [Setup HTTP event collector](https://docs.splunk.com/Documentation/Splunk/8.0.2/Data/UsetheHTTPEventCollector)
- Points to note

## Pre-requisites

- Whitelist your Tenancy for Logging
- Whitelist your Tenancy for VCN Flow Logs

Here's the [link](https://go.oracle.com/LP=78019?elqCampaignId=179851) to the process for Cloud Native LA.

## Quickstart For Setup On OCI Side

This quickstart assumes you have working understanding of basic principles of OCI around IAM | Networking and you know how to get around the OCI Console. Since Flow Logs contain sensitive network Information,

### Create Compartments and Groups

- `Burger-Menu` --> `Identity` --> `Compartments | Users | Groups`

1. Create a Compartment `flow-log-compartment`
2. Create a Group `flow-log-users`
3. Add `Required User` to group `flow-log-users`
4. Create a Dynamic Group `flow-log-dg`
5. Write appropriate IAM Policies at the tenancy level and compartment level.

### Create a Dynamic Group

- `Burger-Menu` --> `Identity` --> `Dynamic Groups`
- Create a Dynamic Group `flow-log-dg` Instances that meet the criteria defined by any of these rules will be included in the group.

```
ANY {resource.type = 'fnfunc', resource.compartment.id = [flow-log-compartment OCID]}
```

### Create Tenancy IAM policy - Splunk Export Group

- `Burger-Menu` --> `Identity` --> `Policies`
- Create an IAM Policy `flow-log-tenancy-policy` with the following policy statements in the `root` compartment

```
Allow group flow-log-users to read compartments in tenancy
Allow group flow-log-users to read virtual-network-family in tenancy
Allow group flow-log-users to use subnets in tenancy
Allow group flow-log-users to manage flow-log-configs in tenancy
Allow group flow-log-users to use flow-log-config-attachments in tenancy
Allow service FaaS to read repos in tenancy
```

### Create Tenancy IAM policy - Splunk Export Dynamic Group

- `Burger-Menu` --> `Identity` --> `Policies`
- Create an IAM Policy `flow-log-dg-tenancy-policy` with the following policy statements in the `root` compartment

```
Allow dynamic-group flow-log-dg to read virtual-network-family in tenancy
Allow dynamic-group flow-log-dg to read compartments in tenancy
```

### Create Compartment Level IAM Policy

- `Burger-Menu` --> `Identity` --> `Policies`
  Create an IAM Policy `flow-log-dg-compartment-policy` inside the compartment `flow-log-compartment`

```
Allow dynamic-group flow-log-dg to read objects in compartment flow-log-compartment
Allow dynamic-group flow-log-dg to use virtual-network-family in compartment flow-log-compartment
```

### Create a VCN, Subnet & Security Lists

- `Burger-Menu` --> `Networking` --> `Virtual Cloud Networks`
- Use VCN Quick Start to Create a VCN `flow-log-vcn` with Internet.
- Connectivity Go to Security List and Delete all a `Stateful Ingress Rules` in the `Default Security list` .
- Go to Default Security List and create a `Stateful Egress Rule` is available in the `Default Security List` to allow egress traffic for
  - `0.0.0.0/0` on port `443` protocol `TCP`
  - `0.0.0.0/0` on port `8088` protocol `TCP`
  - `0.0.0.0/0` on port `53` protocol `UDP`

### Create a Function Application

- `Burger-Menu` --> `Developer Services` --> `Functions`
- Create a Function Application `flow-log-app` in the compartment `flow-log-compartment` while selecting `flow-log-vcn` and the `Private Subnet`
- Setup Papertrail / OCI Logging Service to debug Function executions if required. [Setup PaperTrail](https://papertrailapp.com/) , check them out.

### Create a OCIR Repo

- Create a `Private` Repository `flow-log-repo`

### Configure Cloud Shell

15. Setup Cloud Shell in your tenancy - [Link](https://docs.cloud.oracle.com/en-us/iaas/Content/API/Concepts/cloudshellgettingstarted.htm?TocPath=Developer%20Tools%20%7C%7CUsing%20Cloud%20Shell%7C_____0)
16. Clone the Repo in the cloud shell
    `git clone https://github.com/vamsiramakrishnan/splunk-export-logs.git`
17. Login to your region's docker login `iad.ocir.io` with appropriate credentials

### Create & Set Fn Context

```
fn create context flow-log-context --provider oracle
fn use context flow-log-context`
```

### Update the Context

```
fn update context oracle.compartment-id [flow-log-compartment-ocid]
fn update context api-url https://functions.[region-name].oraclecloud.com
fn update context registry [YOUR-TENANCY-NAMESPACE]/[flow-log-repo]
```

### Deploy the Functions

Each folder within the repo represents a function , go to each folder and deploy the function using the the `fn --verbose deploy`

```
cd splunk-export-logs
cd enrich-flow-logs
fn --verbose deploy flow-log-app enrich-flow-logs

```

The Deploy Automatically Triggers an Fn Build and Fn Push to the Container registry repo setup for the functions.

### Set the Environment Variables for Each Function

These environment variables help call other functions. One after the other.

| Fn-Name          | Parameter Name     | Description                                                                                                   | Example                                   |
| ---------------- | ------------------ | ------------------------------------------------------------------------------------------------------------- | ----------------------------------------- |
| enrich-flow-logs | source_source_name | The Source Name that you would like Splunk to see                                                             | oci-hec-event-collector                   |
| enrich-flow-logs | source_host_name   | The Source Hostname that you would like Splunk to see                                                         | oci-vcn-flow-logs                         |
| enrich-flow-logs | splunk_url         | The Splunk Cloud URL ( Append input to the beginning of your splunk cloud url, do not add any http/https etc. | input-prd-p-hh6835czm4rp.cloud.splunk.com |
| enrich-flow-logs | splunk_hec_token   | The Token that is unqiue to that HEC                                                                          | TOKEN                                     |
| enrich-flow-logs | splunk_index_name  | The index into which you'd like these logs to get aggregated                                                  | main                                      |

## Invoke and Test !

Invoke Once and the loop will stay active as long as the tenancy does continuously pushing events to Splunk .

```
curl --location --request GET '[apigateway-url].us-phoenix-1.oci.customer-oci.com/regions/listregions'
```

If all is well in papertrail/ oci-function-logs/metrics, proceed.
