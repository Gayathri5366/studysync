"""
StudySync VPC Setup Script
Run once to create the VPC, subnet, internet gateway, route table,
and security group for the EC2 instance.

Usage:
    python timer/vpc_config.py --region eu-west-1
"""

import argparse, json, logging, os, sys
import boto3
from botocore.exceptions import BotoCoreError, ClientError

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)

VPC_CIDR = "10.0.0.0/16"
SUBNET_CIDR = "10.0.1.0/24"
TAG_PREFIX = "studysync"


def _tag(name):
    return [{"Key": "Name", "Value": name}, {"Key": "Project", "Value": "StudySync"}]


def _find_by_tag(collection, tag_name):
    for r in collection.all():
        for t in r.tags or []:
            if t["Key"] == "Name" and t["Value"] == tag_name:
                return r
    return None


def setup_vpc(region):
    ec2 = boto3.resource("ec2", region_name=region)
    client = boto3.client("ec2", region_name=region)
    result = {}

    # VPC
    vpc = _find_by_tag(ec2.vpcs, f"{TAG_PREFIX}-vpc")
    if not vpc:
        vpc = ec2.create_vpc(CidrBlock=VPC_CIDR)
        vpc.wait_until_available()
        vpc.create_tags(Tags=_tag(f"{TAG_PREFIX}-vpc"))
        client.modify_vpc_attribute(VpcId=vpc.id, EnableDnsHostnames={"Value": True})
        logger.info(f"Created VPC: {vpc.id}")
    result["vpc_id"] = vpc.id

    # Internet Gateway
    igw = _find_by_tag(ec2.internet_gateways, f"{TAG_PREFIX}-igw")
    if not igw:
        igw = ec2.create_internet_gateway()
        igw.create_tags(Tags=_tag(f"{TAG_PREFIX}-igw"))
        igw.attach_to_vpc(VpcId=vpc.id)
        logger.info(f"Created IGW: {igw.id}")
    result["igw_id"] = igw.id

    # Subnet
    subnet = _find_by_tag(ec2.subnets, f"{TAG_PREFIX}-public-subnet")
    if not subnet:
        subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock=SUBNET_CIDR,
                                   AvailabilityZone=f"{region}a")
        subnet.create_tags(Tags=_tag(f"{TAG_PREFIX}-public-subnet"))
        client.modify_subnet_attribute(SubnetId=subnet.id,
                                       MapPublicIpOnLaunch={"Value": True})
        logger.info(f"Created subnet: {subnet.id}")
    result["subnet_id"] = subnet.id

    # Route Table
    rt = _find_by_tag(ec2.route_tables, f"{TAG_PREFIX}-public-rt")
    if not rt:
        rt = ec2.create_route_table(VpcId=vpc.id)
        rt.create_tags(Tags=_tag(f"{TAG_PREFIX}-public-rt"))
        rt.create_route(DestinationCidrBlock="0.0.0.0/0", GatewayId=igw.id)
        rt.associate_with_subnet(SubnetId=subnet.id)
        logger.info(f"Created route table: {rt.id}")
    result["route_table_id"] = rt.id

    # Security Group
    sgs = client.describe_security_groups(
        Filters=[{"Name": "vpc-id", "Values": [vpc.id]},
                 {"Name": "group-name", "Values": [f"{TAG_PREFIX}-sg"]}])["SecurityGroups"]
    if sgs:
        sg_id = sgs[0]["GroupId"]
    else:
        sg_id = client.create_security_group(
            GroupName=f"{TAG_PREFIX}-sg",
            Description="StudySync: SSH + app port only",
            VpcId=vpc.id)["GroupId"]
        client.authorize_security_group_ingress(GroupId=sg_id, IpPermissions=[
            {"IpProtocol": "tcp", "FromPort": 22, "ToPort": 22,
             "IpRanges": [{"CidrIp": "0.0.0.0/0"}]},
            {"IpProtocol": "tcp", "FromPort": 8000, "ToPort": 8000,
             "IpRanges": [{"CidrIp": "0.0.0.0/0"}]},
        ])
        logger.info(f"Created security group: {sg_id}")
    result["security_group_id"] = sg_id

    logger.info("Done.\n" + json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--region", default=os.environ.get("AWS_DEFAULT_REGION", "eu-west-1"))
    args = parser.parse_args()
    try:
        setup_vpc(args.region)
    except (BotoCoreError, ClientError) as e:
        logger.error(e); sys.exit(1)