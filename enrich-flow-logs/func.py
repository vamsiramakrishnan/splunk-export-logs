import io
import json
from splunk_http_event_collector import http_event_collector
from fdk import response
import oci
from base64 import b64encode, b64decode
from operator import itemgetter
import time
import zlib
from operator import itemgetter
import os


def handler(ctx, data: io.BytesIO = None):
    signer = oci.auth.signers.get_resource_principals_signer()
    incomingBody = json.loads(data.getvalue())
    vcn_flowlog_data = read_from_objectStorage(signer, incomingBody)
    oci_audit_events_JSON = http_event_collector(
        token=os.environ["splunk_hec_token"],
        host=os.environ["source_host_name"],
        input_type="json",
        http_event_port=os.environ["splunk_hec_port"],
        http_event_server=os.environ["splunk_url"],
    )
    oci_audit_events_JSON.SSL_verify = False
    oci_audit_events_JSON.popNullFields = False
    oci_audit_events_JSON.index = "main"
    for i in vcn_flowlog_data:
        payload = {}
        payload.update({"index": os.environ["splunk_index_name"]})
        payload.update({"sourcetype": "_json"})
        payload.update({"source": os.environ["splunk_source_name"]})
        payload.update({"host": os.environ["source_host_name"]})
        payload.update({"event": i})
        oci_audit_events_JSON.batchEvent(payload)
    oci_audit_events_JSON.flushBatch()
    return response.Response(
        ctx,
        response_data=json.dumps({"event":"success"}),
        headers={"Content-Type": "application/json"},
    )

def read_from_objectStorage(signer, incomingBody):
    
    # Initialize Clients & Lookup Tables
    protocols_json = {"1":"ICMP", "6":"TCP", "17":"UDP", "47":"GREs"}
    vcn_client = oci.core.VirtualNetworkClient(config={}, signer=signer)
    objectStorageClient =  oci.object_storage.ObjectStorageClient(config={}, signer=signer)
    identityClient =  oci.identity.IdentityClient(config={}, signer=signer)
    
    
    # Read namespace , Bucket Name , Resource Name, Compartment name 
    namespace =  incomingBody['data']['additionalDetails']['namespace']
    bucketName = incomingBody['data']['additionalDetails']['bucketName']
    availabilityDomain =  incomingBody['data']['availabilityDomain']
    resourceName =  incomingBody['data']['resourceName']
    compartmentId =  incomingBody['data']['compartmentId']

 
    #Read Object from event and fetch VNIC, Subnet Metadata
    obj = objectStorageClient.get_object(namespace, bucketName , resourceName)
    obj_headers = oci.util.to_dict(obj.headers)
    subnetId = obj_headers['opc-meta-logs-identifier-vnicsubnetocid']
    vnicId = obj_headers['opc-meta-logs-identifier-vnicocid']

    # Get Subnet Information
    subnet= oci.util.to_dict(vcn_client.get_subnet(subnetId).data)
    subnetName =  subnet['display_name']
    subnetCompartmentId = subnet['compartment_id']
    
    # Get compartment
    subnetCompartmentName = oci.util.to_dict(identityClient.get_compartment(subnetCompartmentId).data)['name']
    
    # Get VCN Information
    vcnId = subnet['vcn_id']
    vcnName = oci.util.to_dict(vcn_client.get_vcn(vcnId).data)['display_name']
    
    # Get Security List Information
    securityListIds = subnet['security_list_ids']
    securityListNames = [oci.util.to_dict(vcn_client.get_security_list(securityListId).data)['display_name'] for securityListId in securityListIds]
    
    # Get VNIC Name
    vnicId = oci.util.to_dict(vcn_client.get_vnic(vnicId).data)['id']
    vnicName = vnicId['display_name']
    
    #Get NSG Information
    nsgIds = vnicId['nsg_ids']
    nsgNames = [oci.util.to_dict(vcn_client.get_vcn(nsgId).data)['display_name'] for nsgId in nsgIds]
    
    publicIps =[]
    
    # List Public & Private IPs in Subnet
    publicIps.extend(oci.util.to_dict(vcn_client.list_public_ips(scope='REGION', lifetime ='RESERVED', compartment_id = subnetCompartmentId).data))
    publicIps.extend(oci.util.to_dict(vcn_client.list_public_ips(scope='REGION', lifetime ='EPHERMERAL', compartment_id = subnetCompartmentId).data))
    publicIps.extend(oci.util.to_dict(vcn_client.list_public_ips(scope='AVAILABILITY_DOMAIN ', availability_domain = availabilityDomain lifetime ='EPHEMERAL', compartment_id = subnetCompartmentId).data))
    
    privateIps = oci.util.to_dict(vcn_client.list_private_ips().data)
    
    
    fileName = resourceName.split('/')[1]+ "_" + resourceName.split('/')[2]
    stream = zlib.decompressobj(32 + zlib.MAX_WBITS)  # offset 32 to skip the header
    rawText = []
    for chunk in obj.data.raw.stream(decode_content=False):
        rawText.extend(stream.decompress(chunk).decode("utf-8").split("\n"))

    metadataDict =  {"compartmentId": subnetCompartmentId, 
                     "compartmentName": subnetCompartmentName,
                     "availabilityDomain": availabilityDomain, 
                     "vcnId": vcnId, 
                     "vcnName": vcnName,
                     "subnetId": subnetId,
                     "subnetName": subnetName,
                     "vnicId": vnicId,
                     "vnicName": vnicName,
                     "securityListIds": securityListIds, 
                     "securityListNames": securityListNames,
                     'nsgIds': nsgIds, 
                     'nsgNames': nsgNames}

    logDict = flow_log_parse(rawText, protocols_json, metadataDict)
    
    return logDict

def flow_log_parse(rawText, protocol_json, metadataDict):
    logDict = []
    for line in rawText:
        logComponents = line.split(' ')
        if len(logComponents) == 12:
            logDictElement = {
             'version': logComponents[0],
             'srcaddr': logComponents[1],
             'dstaddr': logComponents[2], 
             'srcport': logComponents[3],
             'dstport': logComponents[4],
             'protocol': protocol_json[logComponents[5]] if logComponents[5] in protocol_json.keys() else logComponents[5], 
             'packets': logComponents[6],
             'bytes': logComponents[7],
             'start_time': str(time.ctime(int(logComponents[8]))), 
             'end_time': str(time.ctime(int(logComponents[9]))), 
             'action': logComponents[10], 
             'status': logComponents[11]
            }
        logDictElement.update(metadataDict)
        logDict.append(logDictElement)
    return logDict