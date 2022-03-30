#!/usr/bin/env python
import os
from os import listdir
from os.path import isfile, join
import subprocess
import time
import json
import requests
from rapyuta_io import BuildStatus
import rapyuta_io
import pprint
import sys, getopt

class package_list():

    def __init__(self):
        self.pack_list = [
            {"package_name": "server", "package_id": None},
            {"package_name": "simulator", "package_id": None},
            {"package_name": "amr_ui", "package_id": None},
            {"package_name": "postgres", "package_id": None},
            {"package_name": "gwm", "package_id": None},
            {"package_name": "amr", "package_id": None},
            {"package_name": "server_cloud", "package_id": None},
            {"package_name": "amr_ui_cloud", "package_id": None},
            {"package_name": "postgres_cloud", "package_id": None},
            {"package_name": "gwm_cloud", "package_id": None}
        ]

    def get_list(self):
        return self.pack_list
    def new_list(self, packages):
        packname_list = [p.strip() for p in packages.split(',')]
        self.pack_list = []
        for packname in packname_list:
            self.pack_list.append({"package_name": packname, "package_id": None})


def get_build_info_from_io(project_id, auth_token, build_id):

    client = rapyuta_io.Client(auth_token, project_id)
    build = client.get_build(build_id, include_build_requests=True)
    return build

def get_package_manifest_from_io(project_id, auth_token, package_uid, package_name, package_version):

    client = rapyuta_io.Client(auth_token, project_id)

    if package_uid is None:
        packages = client.get_all_packages()
        subpackages = [package for package in packages if str(package.packageName) == package_name]
        if package_version == 'max':
            tmp_list = [semver_to_int(str(package.packageVersion)) for package in subpackages]
            latest_package = subpackages[tmp_list.index(max(tmp_list))]
            package_uid = latest_package.packageId
        else:
            for subpackage in subpackages:
                if str(subpackage.packageVersion) == package_version:
                    package_uid = subpackage.packageId
                    break
        if package_uid is None:
            raise Exception("Package with the given uid or name and version does not exist in the source project.")
    url = "https://gacatalog.apps.rapyuta.io/serviceclass/status"
    authorization_header = {
        "accept": "application/json",
        "project": project_id,
        'Authorization': 'Bearer ' + auth_token
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

    package_manifest = requests.get(response.json()["packageUrl"]).json()
    return package_manifest

def get_all_subpackages_from_io(project_id, auth_token, package_name):

    client = rapyuta_io.Client(auth_token, project_id)

    packages = client.get_all_packages()
    subpackages = [package for package in packages if str(package.packageName) == package_name]

    return subpackages

def get_subpackage_manifest_from_io(project_id, auth_token, package_uid):
    url = "https://gacatalog.apps.rapyuta.io/serviceclass/status"
    authorization_header = {
        "accept": "application/json",
        "project": project_id,
        'Authorization': 'Bearer ' + auth_token
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

    package_manifest = requests.get(response.json()["packageUrl"]).json()
    return package_manifest

def semver_to_int(version_string):
    version_string = version_string.replace('v', '')
    major, minor, patch_prerel = version_string.split('.')
    patch_prerel = patch_prerel.split('-')
    patch = patch_prerel[0]
    prerel = '0'
    if len(patch_prerel) == 2:
        prerel = patch_prerel[1]

    return int(major) * 10**6 + int(minor) * 10**3 + int(patch) * 10 + int(prerel)


def get_args(argv):
    source_project_id = ''
    target_project_id = ''
    auth_token = ''
    target_packages = ''
    try:
        opts, args = getopt.getopt(argv, "hs:t:a:p:", ["help","source_project=", "target_project=", "auth_token=", "target_packages="])
    except getopt.GetoptError as err:
        print(err)
        sys.exit(2)
    for opt, arg in opts:
        if opt in ('-h', '--help'):
            print('Run from amr-deployment directory')
            print('scripts/manifest_updater.py -s <source_project> -t <target_project> -a <auth_token> -p <target_packages>')
            sys.exit()
        elif opt in ("-s", "--source_project"):
            source_project_id = arg
        elif opt in ("-t", "--target_project"):
            target_project_id = arg
        elif opt in ("-a", "--auth_token"):
            auth_token = arg
        elif opt in ("-p", "--target_packages"):
            target_packages = arg
    return source_project_id, target_project_id, auth_token, target_packages

def get_packages(project_id, auth_token, packages):

    for package in packages:
        print("Getting all subpackages in package: " + package["package_name"])
        subpackages = get_all_subpackages_from_io(project_id, auth_token, package["package_name"])

        if (os.path.isdir('temp_packages/') == False):
            os.mkdir('temp_packages/')
        if (os.path.isdir('temp_packages/' + package["package_name"]) == False):
            os.mkdir('temp_packages/' + package["package_name"])

        work_path = 'temp_packages/' + package["package_name"] + '/'
        package_files = [f for f in listdir(work_path) if isfile(join(work_path, f))]
        print("Getting all currently existing versions for package: " + package["package_name"])
        print(package_files)

        for subpackage in subpackages:
            subpackage_manifest = get_subpackage_manifest_from_io(project_id, auth_token, subpackage["packageId"])

            current_version = subpackage_manifest["packageVersion"]+'.json'
            if(current_version not in package_files):
                print("Pulling subpackage " + subpackage_manifest["packageVersion"] + " of " + package["package_name"])

                for container_id in range(0, len(subpackage_manifest["plans"][0]["components"])):
                    for executable_id in range(0, len(subpackage_manifest["plans"][0]["components"][container_id]["executables"])):
                        container = subpackage_manifest["plans"][0]["components"][container_id]["executables"][executable_id]

                        if "secret" in container:
                            del subpackage_manifest["plans"][0]["components"][container_id]["executables"][executable_id]["secret"]
                            print("Removing secret in subpackage " + subpackage_manifest["packageVersion"] + " for executable " + subpackage_manifest["plans"][0]["components"][container_id]["executables"][executable_id]["name"])

                        if "buildGUID" in container:
                            build = get_build_info_from_io(project_id, auth_token, container["buildGUID"])
                            print("Found buildGUID for executable " + subpackage_manifest["plans"][0]["components"][container_id]["executables"][executable_id]["name"])
                            print(build["buildRequests"])
                            for j in range(1, len(build["buildRequests"])):
                                latest_build = build["buildRequests"][len(build["buildRequests"]) - j]

                                if latest_build["errorString"] == "":
                                    print("Replacing BuildGUID " + container["buildGUID"] + " with Image " +latest_build["executableImageInfo"]["imageInfo"][0]["imageName"])
                                    docker_image = latest_build["executableImageInfo"]["imageInfo"][0]["imageName"]
                                    subpackage_manifest["plans"][0]["components"][container_id]["executables"][executable_id]["docker"] = docker_image
                                    del subpackage_manifest["plans"][0]["components"][container_id]["executables"][executable_id]["buildGUID"]
                                    break

                                if (len(build["buildRequests"]) - j) <= 0:
                                    print("no successful builds found for subpackage")

                            # case for only having a single build
                            if (len(build["buildRequests"]) == 1):
                                latest_build = build["buildRequests"][0]
                                print("Replacing BuildGUID " + container["buildGUID"] + " with Image " + latest_build["executableImageInfo"]["imageInfo"][0]["imageName"])
                                docker_image = latest_build["executableImageInfo"]["imageInfo"][0]["imageName"]
                                subpackage_manifest["plans"][0]["components"][container_id]["executables"][executable_id]["docker"] = docker_image
                                del subpackage_manifest["plans"][0]["components"][container_id]["executables"][executable_id]["buildGUID"]


                # Save to file

                file = open('temp_packages/'+package["package_name"]+'/'+subpackage_manifest["packageVersion"]+'.json', 'w')
                file.write(json.dumps(subpackage_manifest, indent=2))
                file.close()
            else:
                print("version " + subpackage_manifest["packageVersion"] + " exists, will not overwrite")


def push_package(project_id, auth_token, packages):
    client = rapyuta_io.Client(auth_token, project_id)

    for package in packages:
        work_path = 'temp_packages/' + package["package_name"] + '/'
        package_files = [f for f in listdir(work_path) if isfile(join(work_path, f))]
        subpackages = get_all_subpackages_from_io(project_id, auth_token, package["package_name"])
        subpackage_listnames = []
        for subpackage in subpackages:
            subpackage_manifest = get_subpackage_manifest_from_io(project_id, auth_token, subpackage["packageId"])

            subpackage_listnames.append(subpackage_manifest["packageVersion"]+'.json')

        for file in package_files:
            if file not in subpackage_listnames:
                print('Pushing package ' + package["package_name"] + ' to ' +target_project_id)
                with open(work_path+file) as json_file:
                    file_data = json_file.read()
                manifest = json.loads(file_data)
                manifest['name'] = package["package_name"]

                client.create_package(manifest)
            else:
                print('Package: ' + package["package_name"] + ' already exists in ' + target_project_id)

if __name__ == '__main__':
    source_project_id, target_project_id, auth_token, target_packages = get_args(sys.argv[1:])

    if(target_packages != ''):
        packages = package_list()
        packages.new_list(target_packages)
    else:
        packages = package_list()

    # Get packages from source
    print('Getting packages from source project ' + source_project_id)
    get_packages(source_project_id, auth_token, packages.get_list())

    print('Pushing packages to target project ' + target_project_id)
    push_package(target_project_id, auth_token, packages.get_list())