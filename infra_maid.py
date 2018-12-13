import datetime
import json
import logging
import re

import boto3

log_format = '%(asctime)-15s %(levelname)s - %(message)s'
logging.basicConfig(
    level=logging.INFO,
    format=log_format,
    filename='/tmp/infra_maid.log'
)

console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter(log_format)
console.setFormatter(formatter)

logger = logging.getLogger('infra_maid')
logger.addHandler(console)


def get_aws_resource(resource, role_arn, session_name, session_duration):
    """
    :return: aws resource with role assumed
    """
    client = boto3.client('sts')

    response = client.assume_role(
        RoleArn=role_arn,
        RoleSessionName=session_name,
        DurationSeconds=session_duration
    )

    credentials = response['Credentials']

    resource = boto3.resource(
        resource,
        region_name='eu-west-1',
        aws_access_key_id=credentials['AccessKeyId'],
        aws_secret_access_key=credentials['SecretAccessKey'],
        aws_session_token=credentials['SessionToken']
    )
    return resource


def match_patterns(patterns, data):
    """
    Match multiple regex patterns against some data string
    :param patterns:
    :param data:
    :return: True if any pattern matches
    """
    for pattern in patterns:
        if re.match(pattern, data):
            return True
    return False


def get_instances(ec2_resource, ec2_state='running'):
    """
    Return all ec2 instances matching the specified state
    :param ec2_resource:
    :param ec2_state:
    :return:
    """
    return ec2_resource.instances.filter(
        Filters=[{'Name': 'instance-state-name', 'Values': [ec2_state]}])


def is_matching_instance(ec2_instance, patterns):
    for tag in ec2_instance.tags:
        if tag['Key'] == 'Name' and match_patterns(patterns, tag['Value']):
            return True
    return False


def save_local(filename, data):
    with open(filename, 'w') as f:
        f.writelines(data)


def save_s3(s3, bucket, key, data):
    s3_obj = s3.Object(bucket, key)
    s3_obj.put(Body=data)


def load_local(filename):
    with open(filename, 'r') as f:
        return f.readlines()


def load_s3(s3, bucket, key):
    return s3.Object(bucket, key).get()['Body'].read().decode('utf-8')


def stop_instances(ec2, s3, args):
    running_instances = get_instances(ec2)

    stop_patterns = load_local("config/stop_patterns.txt")
    ignore_patterns = load_local("config/ignore_patterns.txt")

    matching_instances = filter(
        lambda i: is_matching_instance(i, stop_patterns) and not is_matching_instance(i, ignore_patterns),
        running_instances
    )

    running_instances = []
    for instance in matching_instances:
        for tag in instance.tags:
            if tag['Key'] == 'Name':
                running_instances.append(
                    {'id': instance.id, 'name': tag['Value'], 'instance_type': instance.instance_type})
                # TODO stop instances
                response = instance.stop(DryRun=True)
                logger.info(
                    "Stopping Instance-ID: '%s', state: ",
                    response['StoppingInstances'][0]['InstanceId'],
                    response['StoppingInstances'][0]['CurrentState']['Name']
                )

    save_s3(s3, args['bucket'], args['key_instances'], json.dumps(running_instances))

    logger.info('Shutdown instances. Exiting ...')


def start_instances(ec2, s3, args):
    stopped_instances = json.loads(load_s3(s3, args['bucket'], args['key_instances']))

    for instance in stopped_instances:
        # TODO start instances
        response = ec2.Instance(instance['id']).start(DryRun=True)
        logger.info(
            "Starting Instance-ID: '%s', state: ",
            response['StartingInstances'][0]['InstanceId'],
            response['StartingInstances'][0]['CurrentState']['Name']
        )
    logger.info('Started instances')


def check_action():
    # current_time = datetime.datetime.now().time()
    current_time = datetime.time(20)

    start_time = datetime.time(8, 0)
    shutdown_time = datetime.time(20, 0)

    if start_time <= current_time < shutdown_time:
        return 'start'
    else:
        return 'stop'


def main():
    aws_role_arn = 'arn:aws:iam::207220154943:role/ctm-data-nonprod-role'
    aws_session_name = 'infra_maid'
    aws_session_duration = 1800
    ec2 = get_aws_resource('ec2', aws_role_arn, aws_session_name, aws_session_duration)
    s3 = get_aws_resource('s3', aws_role_arn, aws_session_name, aws_session_duration)

    args = dict()
    args['bucket'] = 'ctm-bi-claudiu-test'
    args['key_instances'] = 'infra_maid/instances.json'

    action_type = check_action()
    if action_type is 'start':
        start_instances(ec2, s3, args)
    else:
        stop_instances(ec2, s3, args)


if __name__ == '__main__':
    main()
