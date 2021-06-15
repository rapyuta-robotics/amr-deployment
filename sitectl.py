#!/usr/bin/env python2.7

import argparse
import json
import os
import shutil
import sys

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

dir_path = os.path.dirname(os.path.realpath(__file__))

DEFAULT_HEADER = {
    "accept": "application/json",
    "Content-Type": "application/json",
    'Authorization': 'Token autobootstrap',
    'X-RRAMR-Org': '1'
}
AUTOBOOTSTRAP = os.environ.get("AUTOBOOTSTRAP", False)

GWM_URL = os.environ.get("GWM_CORE_URL", "http://localhost:8000")
if AUTOBOOTSTRAP:
    GWM_CORE_URL_HOST = os.environ.get('GWM_CORE_URL_HOST', 'localhost').rstrip('/')
    GWM_CORE_URL_PORT = str(os.environ.get('GWM_CORE_URL_PORT', '8000'))
    if not GWM_CORE_URL_PORT.isdigit():
        sys.exit("Port must be numeric")
    proto = 'https' if GWM_CORE_URL_PORT == '443' else 'http'
    GWM_URL = "%s://%s:%s" % (proto, GWM_CORE_URL_HOST, GWM_CORE_URL_PORT)

GWM_INTERFACE_ENDPOINT_HOST = os.environ.get('GWM_INTERFACE_ENDPOINT_HOST', 'localhost').rstrip('/')
GWM_INTERFACE_ENDPOINT_PORT = str(os.environ.get('GWM_INTERFACE_ENDPOINT_PORT', '8080'))
if not GWM_INTERFACE_ENDPOINT_PORT.isdigit():
    sys.exit("Port must be numeric")
gwm_interface_proto = 'wss' if GWM_INTERFACE_ENDPOINT_PORT == '443' else 'ws'
GWM_INTERFACE_URL = "%s://%s:%s" % (gwm_interface_proto, GWM_INTERFACE_ENDPOINT_HOST, GWM_INTERFACE_ENDPOINT_PORT)

session = requests.Session()
retries = Retry(total=10, backoff_factor=0.5)
session.mount(GWM_URL, HTTPAdapter(max_retries=retries))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='SiteCtl to manage sites.')
    parser.add_argument('--site', metavar='site', type=str, help='name of site', default='tatsumi')
    parser.add_argument('--path', metavar='path', type=str, help='path on disk with bootstrap sites', default='')
    parser.add_argument('--action', metavar='action', type=str, help='create or harvest', default='create',
                        choices=['create', 'harvest'])
    parser.add_argument('--package', metavar='package', type=str, help='rospackage in which site folder lies', default='')
    parser.add_argument('-f', action="store_true", help='force overwrite')

    args, unknown = parser.parse_known_args()
    # Ignore unknown arguments if they are hidden args used by roslaunch
    unknown_nonfiltered = [s for s in unknown if s[:2] != '__']
    if unknown_nonfiltered:
        sys.exit("{}\nUnknown option: {}".format(sys.argv, unknown_nonfiltered[0]))
    site = args.site
    path = args.path
    if args.package != "":
        if path != "":
            sys.exit("Cannot set both package and path")
        import rospkg
        r = rospkg.RosPack()
        path = r.get_path(args.package)
    if path == "":
        site_path = os.path.join(dir_path, site)
    else:
        if os.path.isabs(os.path.join(path, args.site)):
            site_path = os.path.join(path, args.site)
        else:
            site_path = os.path.normpath(os.path.join(dir_path, path, args.site))
    if args.action == "create":
        print("import path : %s" % site_path)
        if not os.path.isdir(site_path):
            exit("No data found at path %s not found on disk" % site_path)
        file_path = os.path.join(site_path, 'site.json')
        if not os.path.exists(file_path):
            exit("site.json description not found on disk at path %s" % site_path)
        data = None
        with open(file_path, 'r') as f:
            data = json.load(f)
        data["endpoint"] = GWM_INTERFACE_URL
        site = data["name"]
        site_id = data["id"]
        result = session.post(GWM_URL + '/v1/site/import_site', headers=DEFAULT_HEADER, json=data)
        if result.status_code == 201:
            print("Successfully created site %s" % site)
        elif result.status_code == 409:
            if not args.f:
                exit('Site is already present consider using the `-f` flag')
            else:
                result = session.get(GWM_URL + '/v1/site/%s' % site, headers=DEFAULT_HEADER)
                site_id = result.json()['id']
                print("deleting older site as forced")
                session.delete(GWM_URL + '/v1/site/' + str(site_id), headers=DEFAULT_HEADER)
                session.post(GWM_URL + '/v1/site/import_site', headers=DEFAULT_HEADER, json=data)
                print("Successfully created site %s" % site)
        else:
            print(result.text)
            exit("Failed to create the site")
        print("updating maps")
        map_images = {element['name']: os.path.join(site_path, 'map_' + element['name'] + '.png') for element in
                      data['maps']}
        image_headers = DEFAULT_HEADER.copy()
        image_headers.pop('accept')
        image_headers.pop('Content-Type')
        image_headers["X-RRAMR-Site"] = str(site_id)
        for name, file in map_images.iteritems():
            result = session.put(GWM_URL + '/v1/map/%s/image' % name, headers=image_headers,
                                 files={'image': open(file, 'rb')})
            if result.status_code != 200:
                print(result.text)
    else:
        print("export path : %s" % site_path)
        if os.path.isdir(site_path):
            if args.f:
                shutil.rmtree(site_path, ignore_errors=True)
            else:
                exit('Data exists and will be destroyed use the `-f` flag to force this ')
        os.makedirs(site_path)
        result = session.get(GWM_URL + '/v1/site/%s' % args.site, headers=DEFAULT_HEADER)
        if result.status_code == 404:
            exit("No such site found :%s" % args.site)
        if len(result.json()):
            site_id = result.json()['id']
            site_json = session.get(GWM_URL + '/v1/site/%s/export' % site_id, headers=DEFAULT_HEADER).json()
            with open(os.path.join(site_path, 'site.json'), 'w') as f:
                json.dump(site_json, f, indent=4, sort_keys=True)
            for map_ in site_json['maps']:
                image_url = map_['image']
                image_file_name = "map_" + map_["name"] + ".png"
                resp = session.get(image_url, headers=DEFAULT_HEADER, stream=True)
                with open(os.path.join(site_path, image_file_name), 'wb') as f:
                    resp.raw.decode_content = True
                    shutil.copyfileobj(resp.raw, f)
