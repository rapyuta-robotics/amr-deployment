#!/usr/bin/env python3

import yaml
import json
import argparse
import requests
import re
from deepdiff import diff
import time
from multiprocessing import Process

from rapyuta_io import Client, DiskType
from rapyuta_io import DeploymentPhaseConstants
from rapyuta_io.clients.package import ROSDistro

# package name and build name
PACKAGES = {
    'rio_amr_pa': 'PA',
    'rio_gazebo': 'PA',
    'rio_gbc': 'PA',
    'rio_gbc_no_bootstrap': 'PA',
    'rio_amr_ui': 'AMR_UI',
    'rio_gwm': 'GWM',
    'rio_db': 'DB'
}


def validate_name(name):
    return re.sub(r'[^.a-zA-Z0-9-]', "", name)


# TEMPORARY FUNCTIONS BEFORE THE SDK CREATE A PROPER DELETE PACKAGE AND DOWNLOAD MANIFEST FUNCTION
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
    response = requests.delete(url, params=request_json, headers=authorization_header)

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
    response = requests.get(url, params=request_json, headers=authorization_header)

    if 'error' in response:
        if response.text['status'] != 404:
            raise requests.ConnectionError(response.text['error'])

    package_manifest = requests.get(json.loads(response.text)["packageUrl"]).text
    return json.loads(package_manifest)


def load_config(config_file, deployment_prefix):
    with open("config/default.yaml", 'r') as stream:
        config = yaml.safe_load(stream)

    with open(config_file, 'r') as stream:
        config.update(yaml.safe_load(stream))

    if deployment_prefix is not None:
        config['deployment_prefix'] = deployment_prefix

    return config


def update_package_version(client, packages, config, package_name, deploy_from_build, ci_deployment):
    file_path = 'packages/' + package_name + '.json.j2'

    with open(file_path) as json_file:
        file_data = json_file.read()
        manifest = json.loads(file_data)

    # assumption, single component and single executable
    # patterns
    # 1. pull from specified docker tag
    # 2-1. use io-builder
    # 2-2. pull image directoly which are build by io-builder
    package_name_sufix = ''
    if 'DOCKER_IMAGE' in config['BUILD'][PACKAGES[package_name]].keys():  # pull from specified docker tag
        manifest['plans'][0]['components'][0]['executables'][0]['docker'] = config['BUILD'][PACKAGES[package_name]]['DOCKER_IMAGE']
        if package_name != 'rio_db':
            manifest['plans'][0]['components'][0]['executables'][0]['secret'] = config['SECRET']
        else:
            manifest['plans'][0]['components'][0]['executables'][0]['secret'] = "secret-rxjqzyskufisshyzpwgbgpfi"
    else:
        if deploy_from_build:
            manifest['name'] += '_builder'
            manifest['plans'][0]['components'][0]['executables'][0]['buildGUID'] = config['BUILD'][PACKAGES[package_name]]['BUILD_ID']
        else:
            manifest['name'] += '_docker'
            repo = 'docker.io/rrdockerhub/' + config['BUILD'][PACKAGES[package_name]]['REPOSITORY']
            tag = ':iogen-' + config['BUILD'][PACKAGES[package_name]]['BUILD_ID'] + \
                '-' + str(config['BUILD'][PACKAGES[package_name]]['BUILD_GEN'])
            manifest['plans'][0]['components'][0]['executables'][0]['docker'] = repo + tag
            manifest['plans'][0]['components'][0]['executables'][0]['secret'] = config['SECRET']

    # Update the package version automatically
    if ci_deployment:
        # file_data = Template(file_data).render(tag=docker_image_tag, secret=config['SECRET'])
        # manifest = json.loads(file_data)
        manifest['name'] = manifest['name'] + " "
        subpackages = [package for package in packages if package['packageName'] == manifest['name']]
        for p in subpackages:
            delete_package(config, p['packageId'])
        package = client.create_package(manifest)
        config[package_name] = client.get_package(package['packageId'])
    else:
        # Get the latest package
        # file_data = Template(file_data).render(tag=docker_image_tag, secret=config['SECRET'])
        # manifest = json.loads(file_data)
        subpackages = [package for package in packages if package['packageName'] == manifest['name']]
        if not subpackages:
            package = client.create_package(manifest)
            config[package_name] = client.get_package(
                package['packageId'])
            return

        def max_index_num(package_string):
            nums = package_string.replace('v', '').split('.')
            return int(nums[0]) * 1000000 + int(nums[1]) * 1000 + int(nums[2])

        tmp_list = [max_index_num(package.packageVersion) for package in subpackages]
        latest_package = subpackages[tmp_list.index(max(tmp_list))]

        # Create the package if the packageVersion is different
        latest_manifest = get_package_manifest(config, latest_package.packageId)
        is_same = manifest['packageVersion'] == latest_manifest['packageVersion']
        if not is_same:
            if max_index_num(latest_manifest['packageVersion']) > max_index_num(manifest['packageVersion']):
                raise Exception(
                    file_path + " has modified packageVersion smaller than the latest package version: " + latest_manifest['packageVersion'] + " on rapyuta.io. Please update Package version in the manifest.")

            print('Update package: ' + package_name)
            package = client.create_package(manifest)
            config[package_name] = client.get_package(
                package['packageId'])
            print(package_name + ', version=' + manifest['packageVersion'] +
                  ' was created. packageId=' + config[package_name]['packageId'])
        else:
            latest_manifest['packageVersion'] = manifest['packageVersion']
            if latest_manifest != manifest:
                print(file_path + ' has been modified. manifest difference: \n')
                print(diff.DeepDiff(latest_manifest, manifest))
                print('but pakcageVesion has not been changed. packageVersion:' + latest_manifest['packageVersion'])
                raise Exception(file_path + " has been modified but the versions packageVersion: " +
                                latest_manifest['packageVersion'] + " has not been changed.")

            print('No Update in package: ' + package_name)
            config[package_name] = client.get_package(
                latest_package['packageId'])


def update_packages(client, config, deploy_from_build=True, ci_deployment=False):
    print("Updating package version")

    packages = client.get_all_packages()
    for i in PACKAGES:
        update_package_version(client, packages, config, i, deploy_from_build, ci_deployment)


def destroy_packages(config):
    print("Destroying packages")

    for i in PACKAGES:
        delete_package(config, config[i]['packageId'])


def deploy(client, config, deployment_prefix=None):
    print("Deploying")
    deploy_network(client, config, deployment_prefix)

    process_intelligence = Process(target=deploy_intelligence, args=(client, config,))
    process_intelligence.start()

    process_sim = Process(target=deploy_simulation, args=(client, config,))
    process_sim.start()

    process_intelligence.join()
    process_sim.join()


def deploy_network(client, config, deployment_prefix=None):
    # Routed Network
    networks = client.get_all_routed_networks()
    network = None
    for net in networks:
        if net.name == config['deployment_prefix'] + '_routed_network' and net.get_status().status == "Running":
            network = net
            print(config['deployment_prefix'] + '_routed_network' + " was found and will be used")
            break
    if not network:
        print(config['deployment_prefix'] + '_routed_network' + ": deploy")
        # use client directory till network support resource parameter.
        # network = client.create_cloud_routed_network(config['deployment_prefix'] + '_routed_network', ROSDistro.MELODIC,
        #                                              True)
        client._catalog_client.create_routed_network(name=config['deployment_prefix'] + '_routed_network', runtime='cloud',
                                                     rosDistro=ROSDistro.MELODIC,
                                                     shared=True, parameters={'limits': {'cpu': 4, 'memory': 16384}})
        # network.poll_routed_network_till_ready(retry_count=150, sleep_interval=6)
        # print(config['deployment_prefix'] + '_routed_network' + " was created successfully")


def wait_network_deploy(client, name, sleep=10):
    networks = client.get_all_routed_networks()
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


def deploy_intelligence(client, config, deployment_prefix=None):
    autobootstrap = False
    # DB Postgres
    deployments = client.get_all_deployments(
        phases=[DeploymentPhaseConstants.SUCCEEDED, DeploymentPhaseConstants.FAILED_TO_START])
    # todo use better way to avoid hardcode multiple place
    rio_db_deployment_name = config['deployment_prefix'] + '_postgres'
    rio_db_deployment = None
    for deployment in deployments:
        if deployment.name == rio_db_deployment_name:
            print(rio_db_deployment_name + " was found and will be used and no bootstrap.")
            autobootstrap = False
            rio_db_deployment = client.get_deployment(deployment.deploymentId, retry_limit=10)
            break
    if not rio_db_deployment:
        print("DB is deploying...")
        rio_db_package = client.get_package(config['rio_db']['packageId'])
        rio_db_configuration = rio_db_package.get_provision_configuration(config['rio_db']['plans'][0]['planId'])
        for key in config['GWM_PARAMS']:
            rio_db_configuration.add_parameter('postgres', key, config['GWM_PARAMS'][key])

        rio_db_deployment = rio_db_package.provision(
            deployment_name=rio_db_deployment_name,
            provision_configuration=rio_db_configuration)
        rio_db_deployment.poll_deployment_till_ready(retry_count=150, sleep_interval=6)
        autobootstrap = True
        print(" DB deployed successfully")

    # GWM deployment
    # todo use better way to avoid hardcode multiple place
    rio_gwm_deployment_name = config['deployment_prefix'] + '_gwm'
    rio_gwm_deployment = None
    for deployment in deployments:
        if deployment.name == rio_gwm_deployment_name:
            print(rio_gwm_deployment_name + " was found and will be used.")
            rio_gwm_deployment = client.get_deployment(deployment.deploymentId, retry_limit=10)
            break
    if not rio_gwm_deployment:
        print("GWM is deploying...")
        gwm_component = 'core'
        rio_gwm_package = client.get_package(config['rio_gwm']['packageId'])
        rio_gwm_configuration = rio_gwm_package.get_provision_configuration(config['rio_gwm']['plans'][0]['planId'])

        for key in config['GWM_PARAMS']:
            rio_gwm_configuration.add_parameter(gwm_component, key, config['GWM_PARAMS'][key])

        rio_gwm_configuration.add_dependent_deployment(rio_db_deployment)

        if client.get_static_route_by_name(
                config['deployment_prefix'] + "-gwm") is None:
            client.create_static_route(config['deployment_prefix'] + "-gwm")

        rio_gwm_configuration.add_static_route(component_name=gwm_component,
                                               endpoint_name='GWM_CORE_URL',
                                               static_route=client.get_static_route_by_name(
                                                   config['deployment_prefix'] + "-gwm"))

        rio_gwm_deployment = rio_gwm_package.provision(deployment_name=config['deployment_prefix'] + '_gwm',
                                                       provision_configuration=rio_gwm_configuration)
        rio_gwm_deployment.poll_deployment_till_ready(retry_count=150, sleep_interval=6)
        print(" GWM deployed successfully")

    network = wait_network_deploy(client, config['deployment_prefix'] + '_routed_network')

    # GBC deployment
    print("GBC is deploying...")
    rio_gbc_package_name = 'rio_gbc'
    if not autobootstrap:
        rio_gbc_package_name += '_no_bootstrap'

    rio_gbc_package = client.get_package(config[rio_gbc_package_name]['packageId'])
    rio_gbc_configuration = rio_gbc_package.get_provision_configuration(
        config[rio_gbc_package_name]['plans'][0]['planId'])

    for key in config['GBC_PARAMS']:
        rio_gbc_configuration.add_parameter('gbc', key, config['GBC_PARAMS'][key])

    rio_gbc_configuration.add_dependent_deployment(rio_gwm_deployment)

    if client.get_static_route_by_name(
            config['deployment_prefix'] + "-gbc") is None:
        client.create_static_route(config['deployment_prefix'] + "-gbc")

    rio_gbc_configuration.add_static_route(component_name='gbc',
                                           endpoint_name='GWM_INTERFACE_ENDPOINT',
                                           static_route=client.get_static_route_by_name(
                                               config['deployment_prefix'] + "-gbc"))

    rio_gbc_configuration.add_routed_networks([network])
    rio_gbc_deployment = rio_gbc_package.provision(deployment_name=config['deployment_prefix'] + '_gbc',
                                                   provision_configuration=rio_gbc_configuration)
    rio_gbc_deployment.poll_deployment_till_ready(retry_count=150, sleep_interval=6)
    print(" GBC deployed successfully")

    # AMR UI deployment
    print("AMR UI is deploying...")
    rio_amr_ui_package = client.get_package(config['rio_amr_ui']['packageId'])
    rio_amr_ui_configuration = rio_amr_ui_package.get_provision_configuration(
        config['rio_amr_ui']['plans'][0]['planId'])

    for key in config['AMR_UI_PARAMS']:
        rio_amr_ui_configuration.add_parameter('gwm-ui', key, config['AMR_UI_PARAMS'][key])

    rio_amr_ui_configuration.add_dependent_deployment(rio_gwm_deployment)
    rio_amr_ui_configuration.add_dependent_deployment(rio_gbc_deployment)

    if client.get_static_route_by_name(
            config['deployment_prefix'] + "-amr-ui") is None:
        client.create_static_route(config['deployment_prefix'] + "-amr-ui")

    rio_amr_ui_configuration.add_static_route(component_name='gwm-ui',
                                              endpoint_name='GWM_UI',
                                              static_route=client.get_static_route_by_name(
                                                  config['deployment_prefix'] + "-amr-ui"))

    rio_amr_ui_deployment = rio_amr_ui_package.provision(deployment_name=config['deployment_prefix'] + '_amr_ui',
                                                         provision_configuration=rio_amr_ui_configuration)

    result = rio_amr_ui_deployment.poll_deployment_till_ready(retry_count=150, sleep_interval=6)
    print(" AMR UI deployed successfully: " + result['componentInfo'][0]['networkEndpoints']['GWM_UI'])


def deploy_simulation(client, config, deployment_prefix=None):
    network = wait_network_deploy(client, config['deployment_prefix'] + '_routed_network')
    # Gazebo Deployment
    print("GAZEBO is deploying...")
    gazebo_package = client.get_package(config['rio_gazebo']['packageId'])
    gazebo_configuration = gazebo_package.get_provision_configuration(config['rio_gazebo']['plans'][0]['planId'])
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
    gazebo_configuration.add_routed_networks([network])
    gazebo_configuration.set_component_alias('gazebo', 'gazebo')
    gazebo_deployment = gazebo_package.provision(
        deployment_name=config['deployment_prefix'] + '_gazebo',
        provision_configuration=gazebo_configuration)

    result = gazebo_deployment.poll_deployment_till_ready(retry_count=1000, sleep_interval=10)
    print(' Gazebo deployed succesfully: ' + result['componentInfo'][0]['networkEndpoints']['VNC_EP'])

    # AMR deployments
    amr_deployments = [None] * len(config['AMR_PARAMS'])
    amr_package = client.get_package(config['rio_amr_pa']['packageId'])
    aliases = []
    for i in range(len(config['AMR_PARAMS'])):
        print("AMR" + str(i + 1) + " is deploying...")
        amr_configuration = amr_package.get_provision_configuration(
            config['rio_amr_pa']['plans'][0]['planId'])
        for key in config['AMR_PARAMS'][i]:
            amr_configuration.add_parameter(
                'amr', key, config['AMR_PARAMS'][i][key])
        alias = 'amr' + \
            str(i + 1) if 'NAME' not in config['AMR_PARAMS'][i] else config['AMR_PARAMS'][i]['NAME']
        aliases.append(alias)
        amr_configuration.set_component_alias('amr', alias)
        amr_configuration.add_routed_networks([network])
        amr_deployments[i] = amr_package.provision(
            deployment_name=config['deployment_prefix'] + '_' + alias,
            provision_configuration=amr_configuration)
    for i in range(len(config['AMR_PARAMS'])):
        amr_deployments[i].poll_deployment_till_ready(
            retry_count=1000, sleep_interval=10)
        print(" " + aliases[i] + " deployed successfully")


def deprovision(client, config, deployment_prefix):
    print("Deprovisioning")

    deployments = client.get_all_deployments(
        phases=[DeploymentPhaseConstants.SUCCEEDED, DeploymentPhaseConstants.FAILED_TO_START])

    # temp solution to avoid deprovision db
    # todo move to top of this file or config file
    DEPLOYMENT_NAMES = [
        'gazebo',
        'amr_ui',
        'gbc'
    ]
    deployment_names = [deployment_prefix + '_' + i for i in DEPLOYMENT_NAMES]
    db_deployment_name = deployment_prefix + '_postgress'
    gwm_deployment_name = deployment_prefix + '_gwm'
    amr_deployment_prefix = deployment_prefix + '_' + 'amr'  # to find amr deployment

    for deployment in deployments:
        if (deployment.name in deployment_names or
            amr_deployment_prefix == deployment.name[0:len(amr_deployment_prefix)] or
            (config['deprovision_db'] and deployment.name == db_deployment_name) or
                (config['deprovision_gwm'] and deployment.name == gwm_deployment_name)):
            print("Deprovisioning " + deployment.name)
            deployment.deprovision(3)

    if config['deprovision_routed_network']:
        networks = client.get_all_routed_networks()
        for network in networks:
            if deployment_prefix in network.name:
                network.delete()
                break


# Usage: python deploy.py [config.yaml] [True/False for CI deployment
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Deployment script for hitachi')
    parser.add_argument('--prefix', default=None, help='Deployment prefix for the deployment on rapyuta.io')
    parser.add_argument('--deploy_from_build', action='store_true',
                        default=False, help='create package/deploy with io-build')
    parser.add_argument('--config', default='config/default.yaml', help='File path for the config file to use')
    parser.add_argument('--deprovision', '-d', action='store_const', const=sum, default=False,
                        help='Whether or not you only want to deprovision')
    parser.add_argument('--destroy', action='store_const', const=sum, default=False,
                        help='Whether or not you only want to destroy the package')
    args = parser.parse_args()

    if args.prefix is not None:
        valid_prefix = validate_name(args.prefix)
    else:
        valid_prefix = None
    config = load_config(args.config, valid_prefix)
    client = Client(config['AUTH_TOKEN'], config['PROJECT_ID'])

    if args.deprovision:
        deprovision(client, config, config['deployment_prefix'])
        if args.destroy:
            update_packages(client, config, args.deploy_from_build, True)
            destroy_packages(config)
    else:
        update_packages(client, config, args.deploy_from_build)
        deprovision(client, config, config['deployment_prefix'])
        deploy(client, config, config['deployment_prefix'])
        # if input("Deprovision? (y/N)").lower() == "y":
        #     deprovision(client, config, config['deployment_prefix'])
        #     if args.destroy:
        #         destroy_packages(config)
