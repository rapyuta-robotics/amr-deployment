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

project_id = "project-xbaeosxiygjtkhuanbwhjmhi"
auth_token = "BsCVpr9sJshIhvvMrOFpMofszIMgXAF4fhLdx2Mi"

def package_list():
    pack_list = [
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

    return pack_list

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
            print("askdfhlaskdfjhalskdjfhsa " + tmp_list)
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
    project_id = ''
    auth_token = ''
    try:
        opts, args = getopt.getopt(argv, "hp:a:", ["help","project_id=", "auth_token="])
    except getopt.GetoptError as err:
        print(err)
        sys.exit(2)
    for opt, arg in opts:
        if opt in ('-h', '--help'):
            print('Run from amr-deployment directory')
            print('scripts/manifest_updater.py -p <project_id> -a <auth_token>')
            sys.exit()
        elif opt in ("-p", "--project_id"):
            project_id = arg
        elif opt in ("-a", "--auth_token"):
            auth_token = arg
    return project_id, auth_token

def main(project_id, auth_token):

    packages = package_list()

    for package in packages:
        # print("Getting all subpackages in package: " + package["package_name"])
        subpackages = get_all_subpackages_from_io(project_id, auth_token, package["package_name"])

        work_path = 'packages/' + package["package_name"] + '/'
        package_files = [f for f in listdir(work_path) if isfile(join(work_path, f))]
        print("Getting all currently existing versions for package: " + package["package_name"])
        print(package_files)

        version= {}

        for subpackage in subpackages:
            subpackage_manifest = get_subpackage_manifest_from_io(project_id, auth_token, subpackage["packageId"])

            #Get strings for version
            current_version = subpackage_manifest["packageVersion"]+'.json'
            old_version = subpackage_manifest["packageVersion"]

            #Change version from vX.X.X-X to X.X.X 
            version_string = subpackage_manifest["packageVersion"].replace('v', '')
            major, minor, patch_prerel = version_string.split('.')
            patch_prerel = patch_prerel.split('-')
            patch = patch_prerel[0]
            prerel = 0
            if len(patch_prerel) == 2:
                prerel = int(patch_prerel[1])
            
            #String and Int Versioning
            subpackage_version=int(major) * 10**4 + int(minor) * 10**2 + int(patch)
            subpackage_string_version = major + "." + minor + "." + patch
            
            #Check if subpackage_version is already in dictionary if not, add to dictionary
            if (subpackage_version not in version):
                version[subpackage_version] = prerel

            #Check if current prerel is larger than the one in the dictionary. If so update the prerel version and create a new pacakge.json
            if(prerel >= version[subpackage_version]):
                #Set the minor version
                version[subpackage_version] = prerel
                print("Pulling subpackage " + subpackage_manifest["packageVersion"] + " of " + package["package_name"])

                for container_id in range(0, len(subpackage_manifest["plans"][0]["components"])):
                    for executable_id in range(0, len(subpackage_manifest["plans"][0]["components"][container_id]["executables"])):
                        container = subpackage_manifest["plans"][0]["components"][container_id]["executables"][executable_id]

                        #Replace Description and Package version.
                        del subpackage_manifest["description"]
                        subpackage_manifest["description"] = "This package was created from " + old_version
                        print("Replacing description in subpackage " + old_version)

                        #Remove secret
                        if "secret" in container:
                            del subpackage_manifest["plans"][0]["components"][container_id]["executables"][executable_id]["secret"]
                            print("Removing secret in subpackage " + subpackage_manifest["packageVersion"] + " for executable " + subpackage_manifest["plans"][0]["components"][container_id]["executables"][executable_id]["name"])

                        #Replace Build with Docker image
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

                            #Case for only having a single build
                            if (len(build["buildRequests"]) == 1):
                                latest_build = build["buildRequests"][0]
                                print("Replacing BuildGUID " + container["buildGUID"] + " with Image " + latest_build["executableImageInfo"]["imageInfo"][0]["imageName"])
                                docker_image = latest_build["executableImageInfo"]["imageInfo"][0]["imageName"]
                                subpackage_manifest["plans"][0]["components"][container_id]["executables"][executable_id]["docker"] = docker_image
                                del subpackage_manifest["plans"][0]["components"][container_id]["executables"][executable_id]["buildGUID"]                
                        
                        print("Replacing packageVersion in subpackage " + subpackage_manifest["packageVersion"])
                        del subpackage_manifest["packageVersion"]
                        subpackage_manifest["packageVersion"] = "v" + subpackage_string_version

                #Save to file
                file = open('packages/'+package["package_name"]+'/'+ 'v' + subpackage_string_version +'.json', 'w')
                file.write(json.dumps(subpackage_manifest, indent=2))
                file.close()
            else:
                print("version " + subpackage_manifest["packageVersion"] + " exists, will not overwrite")

if __name__ == '__main__':
    # project_id, auth_token = get_args(sys.argv[1:])
    main(project_id, auth_token)
