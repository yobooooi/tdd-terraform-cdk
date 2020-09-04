#!/usr/bin/env python
import configparser
import json

from constructs import Construct
from cdktf import App, TerraformStack, DataTerraformRemoteStateS3, S3Backend
from imports.aws import AwsProvider, Instance, IamRole, IamRolePolicy, IamRolePolicyAttachment, IamInstanceProfile, DataAwsS3BucketObject


class MyStack(TerraformStack):

    def __init__(self, scope: Construct, ns: str):
        super().__init__(scope, ns)

        # reading instance config file
        stack_config = configparser.ConfigParser()
        stack_config.read('conf.ini')

        # creating a provider construct
        AwsProvider(self, 'Aws', region='eu-west-1', profile='synthesis-internal-dev')

        # initialising backend
        S3Backend(self, profile='synthesis-internal-dev', bucket='cdktf-s3backend', key='cdktf-instance', region='eu-west-1')

        # reading JSON templates to create sts assuume role
        with open('templates/assume_role_policy.json') as data:
            sts_assume_policy = json.load(data)
            iam_role = IamRole( self, 'cdktf-role',
                                name=stack_config['stack']['iam_role_name'],
                                assume_role_policy=str(json.dumps(sts_assume_policy)))
        
        # iterating through config to create policy attachment objects
        for policy, policy_arn in stack_config.items('instance-managed-policies'):
            IamRolePolicyAttachment(self, 'cdktf-{0}-attachment'.format(policy),
                                    role=iam_role.id, 
                                    policy_arn=policy_arn)

        instance_profile = IamInstanceProfile(self, 'cdktf-instance-profile', role=iam_role.id)
        
        # creating ec2 instance using configparser vars
        instance = Instance(self, 'cdktf-instance', 
                            ami=stack_config['instance']['ami'], 
                            instance_type=stack_config['instance']['instance_type'], 
                            subnet_id=stack_config['instance']['subnet'],
                            tags=stack_config._sections['instance-tags'],
                            iam_instance_profile=instance_profile.id)

app = App()
MyStack(app, "tdd-terraform-cdk")

app.synth()
