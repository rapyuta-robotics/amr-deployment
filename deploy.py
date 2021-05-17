#!/usr/bin/env python
import os
import yaml
import json
import argparse
import requests
import re
from jinja2 import Template
from deepdiff import diff
import time
from multiprocessing import Process

from rapyuta_io import Client, DiskType, Secret, SecretConfigDocker, DeploymentPhaseConstants, DeploymentStatusConstants
from rapyuta_io.clients.native_network import NativeNetwork, Parameters, NativeNetworkLimits
from rapyuta_io.clients.package import Runtime, ROSDistro

# python2 compat
try:
    input = raw_input
except NameError:
    pass

# package name and build name
PACKAGES = {
    'rio_amr_pa': 'PA',
    'rio_gazebo': 'PA',
    'rio_gbc': 'PA',
    'rio_amr_ui': 'AMR_UI',
    'rio_gwm': 'GWM',
    'rio_db': 'DB'
}


def validate_name(name):
    return re.sub(r'[^.a-zA-Z0-9-]', "", name)


# TEMPORARY FUNCTIONS BEFORE THE SDK CREATE A PROPER DELETE PACKAGE AND
# DOWNLOAD MANIFEST FUNCTION
def delete_package(config, package_uid):
    url = "https://gacatalog.apps.rapyuta.io/serviceclass/delete"
    authorization_header = {
        "accept": "application/json",
        "project": config['PROJECT_ID'],
        'Authorization': 'Bearer ' + config['AUTH_TOKEN']
    }
    request_json = {
        "package_uid": package_uid,
    }
    response = requests.delete(
        url,
        params=request_json,
        headers=authorization_header)

    if 'error' in response:
        if response.status_code != 404:
            raise requests.ConnectionError(response.text['error'])

    return response.status_code == 200


def get_package_manifest(config, package_uid):
    url = "https://gacatalog.apps.rapyuta.io/serviceclass/status"
    authorization_header = {
        "accept": "application/json",
        "project": config['PROJECT_ID'],
        'Authorization': 'Bearer ' + config['AUTH_TOKEN']
    }
    request_json = {
        "package_uid": package_uid,
    }
    response = requests.get(
        url,
        params=request_json,
        headers=authorization_header)

    if 'error' in response:
        if response.text['status'] != 404:
            raise requests.ConnectionError(response.text['error'])

    package_manifest = requests.get(
        json.loads(response.text)["packageUrl"]).text
    return json.loads(package_manifest)


def get_secret_id_by_name(client, name):
    secrets = client.list_secrets()
    secret_id = ''
    for secret in secrets:
        if secret.name == name:
            secret_id = secret.guid
            break
    return secret_id


def get_build_id_by_name(client, name):
    builds = client.list_builds()
    build_id = None
    for build in builds:
        if build.buildName == name:
            build_id = build.guid
            break
    return build_id


def get_network_by_name(
        client,
        name,
        status='Running'):
    networks = client.list_native_networks()
    network = None
    for net in networks:
        if net.name == name and net.get_status().status == status:
            network = net
            break
    return network


def get_deployment_by_name(
    client,
    name,
    phases=(
        DeploymentPhaseConstants.SUCCEEDED,
        DeploymentPhaseConstants.FAILED_TO_START)):
    deployments = client.get_all_deployments(phases=phases)
    deployment = None
    for dep in deployments:
        if dep.name == name:
            deployment = client.get_deployment(
                dep.deploymentId, retry_limit=10)
            break

    return deployment


def load_config(config_file, deployment_prefix):
    with open("config/default.yaml", 'r') as stream:
        config = yaml.safe_load(stream)

    with open("config/basic_user_config.yaml", 'r') as stream:
        config.update(yaml.safe_load(stream))

    if config_file is not None:
        with open(config_file, 'r') as stream:
            data = yaml.safe_load(stream)
            GWM_PARAMS = data.pop('GWM_PARAMS')
            config.update(data)
            config['GWM_PARAMS'].update(GWM_PARAMS)
            config['GBC_PARAMS']['GWM_AUTH_TOKEN'] = config['GWM_PARAMS']['AUTO_AUTH_TOKEN']
            config['GAZEBO_PARAMS']['GWM_AUTH_TOKEN'] = config['GWM_PARAMS']['AUTO_AUTH_TOKEN']

    if deployment_prefix is not None:
        config['deployment_prefix'] = deployment_prefix

    return config


def update_package_version(
        client,
        packages,
        config,
        package_name,
        secret_id,
        ci_deployment):
    file_path = 'packages/' + package_name + '.json.j2'
    with open(file_path) as json_file:
        file_data = json_file.read()

    # assumption, single component and single executable
    # patterns
    # 1. pull from specified docker tag
    # 2. use io-builder
    if ci_deployment:
        print(package_name)
        if package_name == 'rio_amr_pa' or package_name == 'rio_gazebo' or package_name == 'rio_gbc':
            docker_image_name = 'rrdockerhub/io_amr_pa:' + os.getenv('DEVTAG')
        elif package_name == 'rio_amr_ui':
            docker_image_name = 'rrdockerhub/io_amr_ui:' + os.getenv('DEVTAG')
        elif package_name == 'rio_gwm':
            docker_image_name = 'rrdockerhub/io_amr_gwm:' + os.getenv('DEVTAG')
        elif package_name == 'rio_db':
            docker_image_name = 'mdillon/postgis:latest'
        template_args = {
            'docker': docker_image_name,
            'secret': secret_id
        }
    elif 'DOCKER_IMAGE' in config['BUILD'][PACKAGES[package_name]].keys(
    ):  # pull from specified docker tag
        template_args = {
            'docker': config['BUILD'][PACKAGES[package_name]]['DOCKER_IMAGE'],
            'secret': secret_id
        }
    else:
        build_id = get_build_id_by_name(
            client, config['BUILD'][PACKAGES[package_name]]['BUILD_NAME'])
        if not build_id:
            print('Can\'t find build: ' +
                  config['BUILD'][PACKAGES[package_name]]['BUILD_NAME'])

        template_args = {
            'buildGUID': build_id
        }

    file_data = Template(file_data).render(
        secret=secret_id, source=template_args)
    manifest = json.loads(file_data)

    # Update the package version automatically
    if ci_deployment:
        # file_data = Template(file_data).render(tag=docker_image_tag, secret=config['SECRET'])
        # manifest = json.loads(file_data)
        manifest['name'] = manifest['name'] + " " + os.getenv('DEVTAG')
        subpackages = [
            package for package in packages if package['packageName'] == manifest['name']]
        for p in subpackages:
            delete_package(config, p['packageId'])
        package = client.create_package(manifest)
        config[package_name] = client.get_package(package['packageId'])
    else:
        # Get the latest package
        # file_data = Template(file_data).render(tag=docker_image_tag, secret=config['SECRET'])
        # manifest = json.loads(file_data)
        subpackages = [
            package for package in packages if package['packageName'] == manifest['name']]
        if not subpackages:
            package = client.create_package(manifest)
            config[package_name] = client.get_package(
                package['packageId'])
            return

        def max_index_num(package_string):
            nums = package_string.replace('v', '').split('.')
            return int(nums[0]) * 1000000 + int(nums[1]) * 1000 + int(nums[2])

        tmp_list = [max_index_num(package.packageVersion)
                    for package in subpackages]
        latest_package = subpackages[tmp_list.index(max(tmp_list))]

        # Create the package if the packageVersion is different
        latest_manifest = get_package_manifest(
            config, latest_package.packageId)
        is_same = manifest['packageVersion'] == latest_manifest['packageVersion']
        if not is_same:
            if max_index_num(
                    latest_manifest['packageVersion']) > max_index_num(
                    manifest['packageVersion']):
                raise Exception(
                    file_path +
                    " has modified packageVersion smaller than the latest package version: " +
                    latest_manifest['packageVersion'] +
                    " on rapyuta.io. Please update Package version in the manifest.")

            print('Update package: ' + package_name)
            package = client.create_package(manifest)
            config[package_name] = client.get_package(
                package['packageId'])
            print(
                package_name +
                ', version=' +
                manifest['packageVersion'] +
                ' was created. packageId=' +
                config[package_name]['packageId'])
        else:
            latest_manifest['packageVersion'] = manifest['packageVersion']
            if latest_manifest != manifest:
                print(file_path + ' has been modified. manifest difference: \n')
                print(diff.DeepDiff(latest_manifest, manifest))
                print(
                    'but pakcageVesion has not been changed. packageVersion:' +
                    latest_manifest['packageVersion'])
                raise Exception(
                    file_path +
                    " has been modified but the versions packageVersion: " +
                    latest_manifest['packageVersion'] +
                    " has not been changed.")

            print('No Update in package: ' + package_name)
            config[package_name] = client.get_package(
                latest_package['packageId'])


def update_packages(client, config, ci_deployment=False):
    print("Updating package version")

    secret_id = get_secret_id_by_name(client, config['SECRET'])
    if not secret_id:
        print('Can\'t find secret: ' + config['SECRET'])

    packages = client.get_all_packages()
    for i in PACKAGES:
        update_package_version(
            client,
            packages,
            config,
            i,
            secret_id,
            ci_deployment)


def deploy(client, config):
    print("Deploying")
    deploy_network(client, config)

    process_intelligence = Process(
        target=deploy_intelligence, args=(
            client, config,))
    process_intelligence.start()

    process_sim = Process(target=deploy_simulation, args=(client, config,))
    process_sim.start()

    process_intelligence.join()
    process_sim.join()


def deploy_network(client, config):
    # Native Network
    network_name = config['deployment_prefix'] + '_native_network'
    network = get_network_by_name(client, network_name)
    if not network:
        print(network_name + ": deploy")
        parameters = Parameters(NativeNetworkLimits.SMALL)
        native_network = NativeNetwork(
            network_name, Runtime.CLOUD, ROSDistro.MELODIC, parameters=parameters)
        client._catalog_client.create_native_network(native_network)


def wait_network_deploy(client, name, sleep=10):
    networks = client.list_native_networks()
    network = None
    while(True):
        for net in networks:
            if net.name == name:
                if net.get_status().status == "Running" and net.get_status().phase == "Succeeded":
                    network = net
                    print(name + " was found and will be used")
                    return network
                else:
                    break

        print('Waiting ' + name + ' become running')
        time.sleep(sleep)


def deploy_intelligence(client, config):
    # DB Postgres
    print("DB is deploying...")
    rio_db_deployment_name = config['deployment_prefix'] + '_postgres'
    rio_db_deployment = get_deployment_by_name(client, rio_db_deployment_name)
    if not rio_db_deployment:
        rio_db_package = client.get_package(config['rio_db']['packageId'])
        rio_db_configuration = rio_db_package.get_provision_configuration(
            config['rio_db']['plans'][0]['planId'])
        for key in config['DB_PARAMS']:
            rio_db_configuration.add_parameter(
                'postgres', key, config['DB_PARAMS'][key])
        rio_db_deployment = rio_db_package.provision(
            deployment_name=rio_db_deployment_name,
            provision_configuration=rio_db_configuration)
        rio_db_deployment.poll_deployment_till_ready(
            retry_count=150, sleep_interval=6)
        print(" DB deployed successfully")
    else:
        print(
            rio_db_deployment_name +
            " was found and will be used.")

    # GWM deployment
    print("GWM is deploying...")
    rio_gwm_deployment_name = config['deployment_prefix'] + '_gwm'
    rio_gwm_deployment = get_deployment_by_name(
        client, rio_gwm_deployment_name)
    if not rio_gwm_deployment:
        gwm_component = 'core'
        rio_gwm_package = client.get_package(config['rio_gwm']['packageId'])
        rio_gwm_configuration = rio_gwm_package.get_provision_configuration(
            config['rio_gwm']['plans'][0]['planId'])

        for key in config['GWM_PARAMS']:
            rio_gwm_configuration.add_parameter(
                gwm_component, key, config['GWM_PARAMS'][key])

        rio_gwm_configuration.add_dependent_deployment(rio_db_deployment)

        if client.get_static_route_by_name(
                config['deployment_prefix'] + "-gwm") is None:
            client.create_static_route(config['deployment_prefix'] + "-gwm")

        rio_gwm_configuration.add_static_route(
            component_name=gwm_component,
            endpoint_name='GWM_CORE_URL',
            static_route=client.get_static_route_by_name(
                config['deployment_prefix'] + "-gwm"))

        rio_gwm_deployment = rio_gwm_package.provision(
            deployment_name=config['deployment_prefix'] + '_gwm',
            provision_configuration=rio_gwm_configuration)
        result = rio_gwm_deployment.poll_deployment_till_ready(
            retry_count=150, sleep_interval=6)
        print(" GWM deployed successfully: " +
              result['componentInfo'][0]['networkEndpoints']['GWM_CORE_URL']+'/swagger/')

    else:
        print(
            rio_gwm_deployment_name +
            " was found and will be used.")

    network = wait_network_deploy(
        client,
        config['deployment_prefix'] +
        '_native_network')

    # GBC deployment
    print("GBC is deploying...")
    rio_gbc_package = client.get_package(config['rio_gbc']['packageId'])
    rio_gbc_configuration = rio_gbc_package.get_provision_configuration(
        config['rio_gbc']['plans'][0]['planId'])

    for key in config['GBC_PARAMS']:
        rio_gbc_configuration.add_parameter(
            'gbc', key, config['GBC_PARAMS'][key])

    rio_gbc_configuration.add_dependent_deployment(rio_gwm_deployment)

    if client.get_static_route_by_name(
            config['deployment_prefix'] + "-gbc") is None:
        client.create_static_route(config['deployment_prefix'] + "-gbc")

    rio_gbc_configuration.add_static_route(
        component_name='gbc',
        endpoint_name='GWM_INTERFACE_ENDPOINT',
        static_route=client.get_static_route_by_name(
            config['deployment_prefix'] + "-gbc"))

    rio_gbc_configuration.add_native_network(network)
    rio_gbc_deployment = rio_gbc_package.provision(
        deployment_name=config['deployment_prefix'] + '_gbc',
        provision_configuration=rio_gbc_configuration)
    rio_gbc_deployment.poll_deployment_till_ready(
        retry_count=150, sleep_interval=6)
    print(" GBC deployed successfully")

    # AMR UI deployment
    print("AMR UI is deploying...")
    rio_amr_ui_package = client.get_package(config['rio_amr_ui']['packageId'])
    rio_amr_ui_configuration = rio_amr_ui_package.get_provision_configuration(
        config['rio_amr_ui']['plans'][0]['planId'])

    for key in config['AMR_UI_PARAMS']:
        rio_amr_ui_configuration.add_parameter(
            'gwm-ui', key, config['AMR_UI_PARAMS'][key])

    rio_amr_ui_configuration.add_dependent_deployment(rio_gwm_deployment)
    rio_amr_ui_configuration.add_dependent_deployment(rio_gbc_deployment)

    if client.get_static_route_by_name(
            config['deployment_prefix'] + "-amr-ui") is None:
        client.create_static_route(config['deployment_prefix'] + "-amr-ui")

    rio_amr_ui_configuration.add_static_route(
        component_name='gwm-ui',
        endpoint_name='GWM_UI',
        static_route=client.get_static_route_by_name(
            config['deployment_prefix'] + "-amr-ui"))

    rio_amr_ui_deployment = rio_amr_ui_package.provision(
        deployment_name=config['deployment_prefix'] + '_amr_ui',
        provision_configuration=rio_amr_ui_configuration)
    result = rio_amr_ui_deployment.poll_deployment_till_ready(
        retry_count=150, sleep_interval=6)
    print(" AMR UI deployed successfully: " +
          result['componentInfo'][0]['networkEndpoints']['GWM_UI'])


def deploy_simulation(client, config):
    network = wait_network_deploy(
        client,
        config['deployment_prefix'] +
        '_native_network')
    # Gazebo Deployment
    print("GAZEBO is deploying...")
    gazebo_package = client.get_package(config['rio_gazebo']['packageId'])
    gazebo_configuration = gazebo_package.get_provision_configuration(
        config['rio_gazebo']['plans'][0]['planId'])
    for key in config['GAZEBO_PARAMS']:
        gazebo_configuration.add_parameter('gazebo', key,
                                           config['GAZEBO_PARAMS'][key])

    if client.get_static_route_by_name(
            config['deployment_prefix'] + "-gazebo-ui") is None:
        client.create_static_route(config['deployment_prefix'] + "-gazebo-ui")
    gazebo_configuration.add_static_route(
        component_name='gazebo',
        endpoint_name='VNC_EP',
        static_route=client.get_static_route_by_name(
            config['deployment_prefix'] + "-gazebo-ui")
    )
    gazebo_configuration.add_native_network(network)
    gazebo_configuration.set_component_alias('gazebo', 'gazebo')
    gazebo_deployment = gazebo_package.provision(
        deployment_name=config['deployment_prefix'] + '_gazebo',
        provision_configuration=gazebo_configuration)

    result = gazebo_deployment.poll_deployment_till_ready(
        retry_count=1000, sleep_interval=10)
    print(' Gazebo deployed succesfully: ' +
          result['componentInfo'][0]['networkEndpoints']['VNC_EP'])

    # AMR deployments
    amr_deployments = [None] * len(config['AMR_PARAMS'])
    amr_package = client.get_package(config['rio_amr_pa']['packageId'])
    for i in range(len(config['AMR_PARAMS'])):
        print("AMR" + str(i + 1) + " is deploying...")
        amr_configuration = amr_package.get_provision_configuration(
            config['rio_amr_pa']['plans'][0]['planId'])

        for key in config['AMR_COMMON_PARAMS']:
            amr_configuration.add_parameter(
                'amr', key, config['AMR_COMMON_PARAMS'][key])
        for key in config['AMR_PARAMS'][i]:
            amr_configuration.add_parameter(
                'amr', key, config['AMR_PARAMS'][i][key])
        amr_configuration.set_component_alias('amr', 'amr' + str(i + 1))
        amr_configuration.add_native_network(network)

        amr_deployments[i] = amr_package.provision(
            deployment_name=config['deployment_prefix'] + '_amr' + str(i + 1),
            provision_configuration=amr_configuration)

    for i in range(len(config['AMR_PARAMS'])):
        amr_deployments[i].poll_deployment_till_ready(
            retry_count=1000, sleep_interval=10)
        print(" AMR " + str(i+1) + " deployed successfully")


def deprovision(client, config):
    print("Deprovisioning")

    deployments = client.get_all_deployments(
        phases=[
            DeploymentPhaseConstants.SUCCEEDED,
            DeploymentPhaseConstants.FAILED_TO_START])

    # temp solution to avoid deprovision db and gwm
    # todo move to top of this file or config file
    DEPLOYMENT_NAMES = [
        'gazebo',
        'amr_ui',
        'gbc'
    ]
    deployment_names = [
        config['deployment_prefix'] +
        '_' +
        i for i in DEPLOYMENT_NAMES]
    db_deployment_name = config['deployment_prefix'] + '_postgres'
    gwm_deployment_name = config['deployment_prefix'] + '_gwm'
    amr_deployment_prefix = config['deployment_prefix'] + \
        '_' + 'amr'  # to find amr deployment

    for deployment in deployments:
        if (deployment.name in deployment_names or
            amr_deployment_prefix == deployment.name[0:len(amr_deployment_prefix)] or
            (config['deprovision_db'] and deployment.name == db_deployment_name) or
                (config['deprovision_gwm'] and deployment.name == gwm_deployment_name)):
            print("Deprovisioning " + deployment.name)
            deployment.deprovision(3)

    if config['deprovision_native_network']:
        networks = client.list_native_networks()
        for network in networks:
            if config['deployment_prefix'] in network.name:
                client.delete_native_network(network.guid)
                break


def create_secret(client):
    if get_secret_id_by_name(client=client, name=config['SECRET']) == '':
        secret_config = SecretConfigDocker(username=config['DOCKER_USERNAME'], password=config['DOCKER_PASSWORD'],
                                           email=config['DOCKER_EMAIL'])
        secret = Secret(name=config['SECRET'], secret_config=secret_config)
        client.create_secret(secret)


# Usage: python deploy.py [config.yaml] [True/False for CI deployment
if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Deployment script for io_amr')
    parser.add_argument(
        '--ci-deployment',
        action='store_const',
        const=sum,
        default=False,
        help='Create Packages for CI, will be deleted later')
    parser.add_argument(
        '--prefix',
        default=None,
        help='Deployment prefix for the deployment on rapyuta.io')
    parser.add_argument(
        '--config',
        help='File path for the config file to use')
    parser.add_argument(
        '--deprovision',
        '-d',
        action='store_const',
        const=sum,
        default=False,
        help='Whether or not you only want to deprovision')
    args = parser.parse_args()

    if args.prefix is not None:
        valid_prefix = validate_name(args.prefix)
    else:
        valid_prefix = None
    config = load_config(args.config, valid_prefix)
    client = Client(config['AUTH_TOKEN'], config['PROJECT_ID'])
    create_secret(client=client)

    if args.deprovision:
        deprovision(client, config)
    else:
        update_packages(client, config, args.ci_deployment)
        deprovision(client, config)
        deploy(client, config)
        if input("Deprovision? (y/N)").lower() == "y" and args.ci_deployment == False:
            deprovision(client, config)
