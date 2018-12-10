import datetime
import json
import os
import re

import boto3


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
        json.dump(data, f, sort_keys=True, indent=2)


def load_local(filename):
    with open(filename, 'r') as f:
        data = json.load(f)
    return data


def stop_instances(ec2):
    running_instances = get_instances(ec2)

    stop_patterns = ['^data']
    ignore_patterns = ['.*cdm.*', '.*shadow.*']

    matching_instances = filter(
        lambda i: is_matching_instance(i, stop_patterns) and not is_matching_instance(i, ignore_patterns),
        running_instances
    )

    running_instances = []
    for instance in matching_instances:
        for tag in instance.tags:
            if tag['Key'] == 'Name':
                running_instances.append({'id': instance.id, 'name': tag['Value']})

    filename = 'instances.json'
    save_local(filename, running_instances)

    print('Shutdown instances. Exiting ...')


def start_instances():
    filename = 'instances.json'
    if os.path.isfile(filename):
        stopped_instances = load_local(filename)
        for instance in stopped_instances:
            print(instance['id'])
        print('Started instances')

    else:
        print('No instances.json file found. No instance started. Exiting ...')


def check_action(ec2):
    current_time = datetime.datetime.now().time()
    # current_time = datetime.time(10)
    start_time = datetime.time(8, 0)
    shutdown_time = datetime.time(20, 0)

    if start_time <= current_time < shutdown_time:
        start_instances()
    else:
        stop_instances(ec2, )


def main():
    ec2 = boto3.resource('ec2')
    check_action(ec2)


if __name__ == '__main__':
    main()
