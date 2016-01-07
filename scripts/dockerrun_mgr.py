#!/usr/bin/env python
import botocore.session
import json

# This is a small util designed to aid in updating single containers within a
# multiple container deployment

def _aws_client(service):
  try:
    _aws_client.session
  except AttributeError:
    _aws_client.session = botocore.session.get_session()
  import os
  region = os.environ['AWS_DEFAULT_REGION']
  return _aws_client.session.create_client(service, region_name=region)

def obtain(app, env):
  eb_client = _aws_client('elasticbeanstalk')
  # 1. get info about the environment, extract the running version label
  env_info = eb_client.describe_environments(ApplicationName=app, EnvironmentNames=[env])
  if len(env_info['Environments']) < 1:
    raise Error("Application/Environment not found")
  ver_label = env_info['Environments'][0]['VersionLabel']
  # 2. get info about the version, extract the location of the json source
  ver_info = eb_client.describe_application_versions(ApplicationName=app, VersionLabels=[ver_label])
  source_bundle = ver_info['ApplicationVersions'][0]['SourceBundle']
  (s3_bucket, s3_key) = (source_bundle['S3Bucket'], source_bundle['S3Key'])
  # 3. obtain contents of the json source
  s3_client = _aws_client('s3')
  source = s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
  if source['ContentType'] != 'application/json':
    raise Error("Version source is not a JSON document")
  return json.loads(source['Body'].read())

def update_container_def(defs, container, **kwargs):
  # find the container in the defs
  the_container = None
  for cont in defs['containerDefinitions']:
    if cont['name'] == container:
      the_container = cont
      break
  if the_container is None:
    raise Error("Container %s is not defined", container)
  # update as instructed
  if kwargs.has_key('image_version'):
    img = the_container['image']
    (repo, version) = img.split(':')
    version = kwargs['image_version']
    the_container['image'] = ":".join([repo, version])
  #
  return defs

import argparse

parser = argparse.ArgumentParser(
  description='Programmatically manage Dockerrun.aws.json versions in ElasticBeanstalk',
  epilog='This command outputs a JSON document that can be uploaded as a new version to ElasticBeanstalk')
parser.add_argument('-a', '--app', nargs=1, required=True, help='Name of the ElasticBeanstalk app')
parser.add_argument('-e', '--env', nargs=1, required=True, help='Name of the ElasticBeanstalk environment')
parser.add_argument('-c', '--container-name', nargs=1, required=True, help='Name of the container name to modify in the Dockerrun')
parser.add_argument('-V', '--image-version', nargs=1, required=True, help='Image version to assign to the container in the Dockerrun')
args = parser.parse_args()

defs = obtain(args.app[0], args.env[0])
defs = update_container_def(defs, args.container_name[0], image_version=args.image_version[0])
print json.dumps(defs,indent=2)
