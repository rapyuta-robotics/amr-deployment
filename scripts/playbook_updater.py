#!/usr/bin/env python
import os
import subprocess
import time
import json
import requests
from rapyuta_io import BuildStatus
import rapyuta_io
import pprint

project_id = "project-xbaeosxiygjtkhuanbwhjmhi"
auth_token = "G7mNtDL2BpS678zI3aAq2wDTCR9vluG3SsPGLFLK"

def package_list():
    # pack_list = [
    #     {"package_name": "server", "package_id": "pkg-vlgatdunibgivmnsfyvnivty"},
    #     {"package_name": "simulator", "package_id": "pkg-aritmtitccpgchpojrtayonq"},
    #     {"package_name": "amr_ui", "package_id": "pkg-olouyhwsbblfuegstwordpzd"},
    #     {"package_name": "postgres", "package_id": "pkg-beavpmifdhmkrddgtasgilxi"},
    #     {"package_name": "gwm", "package_id": "pkg-bzraiovgfcfumdvloodvtlgr"},
    #     {"package_name": "amr", "package_id": "pkg-fnxxkckyveinjpanbqufzgoc"},
    #     {"package_name": "server_cloud", "package_id": "pkg-lcbwfjxpzombqppngyrrdzyh"},
    #     {"package_name": "amr_ui_cloud", "package_id": "pkg-eviegdbjycknlfsycqeojczp"},
    #     {"package_name": "postgres_cloud", "package_id": "pkg-dpjhwktrjmxntqmerfcchadf"},
    #     {"package_name": "gwm_cloud", "package_id": "pkg-eyddkkkkwvswaimblqqjwuxs"}
    # ]
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


def main():

    packages = package_list()

    for package in packages:
        subpackages = get_all_subpackages_from_io(project_id, auth_token, package["package_name"])
        for subpackage in subpackages:
            subpackage_manifest = get_subpackage_manifest_from_io(project_id, auth_token, subpackage["packageId"])
            for i in range(0, len(subpackage_manifest["plans"][0]["components"][0]["executables"])):
                container = subpackage_manifest["plans"][0]["components"][0]["executables"][i]
                if "buildGUID" in container:
                    build = get_build_info_from_io(project_id, auth_token, container["buildGUID"])

                    for j in range(1, len(build["buildRequests"])):
                        latest_build = build["buildRequests"][len(build["buildRequests"]) - j]

                        if latest_build["errorString"] == "":
                            docker_image = latest_build["executableImageInfo"]["imageInfo"][0]["imageName"]
                            subpackage_manifest["plans"][0]["components"][0]["executables"][i]["docker"] = docker_image
                            del subpackage_manifest["plans"][0]["components"][0]["executables"][i]["buildGUID"]
                            break

                        if (len(build["buildRequests"]) - j) <= 0:
                            print("no successful builds found for subpackage")


            #Save to file
            file = open('packages/'+package["package_name"]+'/'+subpackage_manifest["packageVersion"]+'.json', 'w')
            file.write(json.dumps(subpackage_manifest, indent=2))
            file.close()

if __name__ == '__main__':
    main()