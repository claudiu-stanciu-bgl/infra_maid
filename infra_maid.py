import json
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
        f.write(data)


def main():
    whitelist = ['^data']
    blacklist = ['.*cdm.*', '.*shadow.*']
    ec2 = boto3.resource('ec2')
    running_instances = get_instances(ec2, )

    # whitelisted_instances = filter(lambda i: is_matching_instance(i, whitelist), ec2_instances)
    matching_instances = filter(lambda i: is_matching_instance(i, whitelist) and not is_matching_instance(i, blacklist),
                                running_instances)

    name_ids = []
    for instance in matching_instances:
        for tag in instance.tags:
            if tag['Key'] == 'Name':
                name_ids.append({'id': instance.id, 'name': tag['Value']})

    save_local("running_ids.json", json.dumps(name_ids, sort_keys=True, indent=2))


if __name__ == '__main__':
    main()
