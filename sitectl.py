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

AUTOBOOTSTRAP = os.environ.get("AUTOBOOTSTRAP", False)
GWM_CORE_URL = os.environ.get("GWM_CORE_URL", "http://localhost:8000")
GWM_AUTH_TOKEN = os.environ.get('GWM_AUTH_TOKEN', 'autobootstrap')
GWM_INTERFACE_ORG_ID = os.environ.get('GWM_INTERFACE_ORG_ID', '1')

DEFAULT_HEADER = {
    "accept": "application/json",
    "Content-Type": "application/json",
    'Authorization': 'Token %s' % GWM_AUTH_TOKEN,
    'X-RRAMR-Org': GWM_INTERFACE_ORG_ID
}

if AUTOBOOTSTRAP:
    GWM_CORE_URL_HOST = os.environ.get('GWM_CORE_URL_HOST', 'localhost').rstrip('/')
    GWM_CORE_URL_PORT = str(os.environ.get('GWM_CORE_URL_PORT', '8000'))
    if not GWM_CORE_URL_PORT.isdigit():
        sys.exit("Port must be numeric")
    proto = 'https' if GWM_CORE_URL_PORT == '443' else 'http'
    GWM_CORE_URL = "%s://%s:%s" % (proto, GWM_CORE_URL_HOST, GWM_CORE_URL_PORT)

GWM_INTERFACE_ENDPOINT_HOST = os.environ.get('GWM_INTERFACE_ENDPOINT_HOST', 'localhost').rstrip('/')
GWM_INTERFACE_ENDPOINT_PORT = str(os.environ.get('GWM_INTERFACE_ENDPOINT_PORT', '8080'))
if not GWM_INTERFACE_ENDPOINT_PORT.isdigit():
    sys.exit("Port must be numeric")
gwm_interface_proto = 'wss' if GWM_INTERFACE_ENDPOINT_PORT == '443' else 'ws'
GWM_INTERFACE_URL = "%s://%s:%s" % (gwm_interface_proto, GWM_INTERFACE_ENDPOINT_HOST, GWM_INTERFACE_ENDPOINT_PORT)
GWM_INTERFACE_URL = str(os.environ.get('GWM_INTERFACE_URL', GWM_INTERFACE_URL))

session = requests.Session()
retries = Retry(total=10, backoff_factor=0.5)
session.mount(GWM_CORE_URL, HTTPAdapter(max_retries=retries))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='SiteCtl to manage sites.')
    parser.add_argument('--site', metavar='site', type=str, help='name of site', default='tatsumi')
    parser.add_argument('--path', metavar='path', type=str, help='path on disk with bootstrap sites', default='')
    parser.add_argument('--action', metavar='action', type=str, help='create or harvest', default='create',
                        choices=['create', 'harvest'])
    parser.add_argument('--package', metavar='package', type=str, help='rospackage in which site folder lies',
                        default='')
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
        try:
            import rospkg
        except ImportError:
            sys.exit("unable to import rospack; consider using the --path option or source your ros workspace")

        r = rospkg.RosPack()
        try:
            path = r.get_path(args.package)
        except rospkg.ResourceNotFound:
            sys.exit("No such rospkg %s found" % args.package)
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
        result = session.post(GWM_CORE_URL + '/v1/site/import_site', headers=DEFAULT_HEADER, json=data)
        if result.status_code == 201:
            print("Successfully created site %s" % site)
        elif result.status_code == 409:
            if not args.f:
                exit('Site is already present consider using the `-f` flag')
            else:
                result = session.get(GWM_CORE_URL + '/v1/site/%s' % site, headers=DEFAULT_HEADER)
                site_id = result.json()['id']
                print("deleting older site as forced")
                session.delete(GWM_CORE_URL + '/v1/site/' + str(site_id), headers=DEFAULT_HEADER)
                session.post(GWM_CORE_URL + '/v1/site/import_site', headers=DEFAULT_HEADER, json=data)
                print("Successfully created site %s" % site)
        else:
            print(result.text)
            exit("Failed to create the site")
        print("updating map layer images")
        map_layers = {map_element['name']: map_element['layers']
                      for map_element in data['maps']}
        image_headers = DEFAULT_HEADER.copy()
        image_headers.pop('accept')
        image_headers.pop('Content-Type')
        image_headers["X-RRAMR-Site"] = str(site_id)
        for name, layers in map_layers.items():
            for layer in layers:
                layer_image = os.path.join(site_path, 'map_' + name + "_" + layer["name"] + '.png')
                result = session.put(GWM_CORE_URL + '/v1/map/%s/layer/%s/upload_layer_image' % (name, layer["name"]),
                                     headers=image_headers,
                                     files={'image': open(layer_image, 'rb')})
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
        result = session.get(GWM_CORE_URL + '/v1/site/%s' % args.site, headers=DEFAULT_HEADER)
        if result.status_code == 404:
            exit("No such site found :%s" % args.site)
        if len(result.json()):
            site_id = result.json()['id']
            site_json = session.get(GWM_CORE_URL + '/v1/site/%s/export' % site_id, headers=DEFAULT_HEADER).json()
            with open(os.path.join(site_path, 'site.json'), 'w') as f:
                json.dump(site_json, f, indent=4, sort_keys=True)
            for map_ in site_json['maps']:
                for layer_ in map_['layers']:
                    image_url = layer_['image']
                    image_file_name = "map_" + map_["name"] + "_" + layer_["name"] + ".png"
                    resp = session.get(image_url, headers=DEFAULT_HEADER, stream=True)
                    with open(os.path.join(site_path, image_file_name), 'wb') as f:
                        resp.raw.decode_content = True
                        shutil.copyfileobj(resp.raw, f)

''' #TEMP REMOVE LATER
def process_and_simplify_file(path):
    data = None
    spot_counter = 0
    region_counter = 0
    spot_map = {}
    with open(path, 'r') as f:
        data = json.load(f)
    for map in data['maps']:
        node_map = {}
        for idx, node in enumerate(map['nodes'], start=1):
            node_map[node['id']] = idx
            node['id'] = idx
        for idx, edge in enumerate(map['edges'], start=1):
            edge['id'] = idx
            edge['node1'] = node_map[edge['node1']]
            edge['node2'] = node_map[edge['node2']]
        for idx, spot in enumerate(map['spots'], start=spot_counter + 1):
            spot_map[spot['id']] = idx
            spot['id'] = idx
            spot_counter = idx
            if spot['node']:
                spot['node'] = node_map[spot['node']]
        for idx, region in enumerate(map['regions'], start=region_counter + 1):
            region['id'] = idx
            region_counter = idx
            region['name'] = "region_%s" % str(idx)
    with open(path, 'w') as f:
        json.dump(data, f, indent=4, sort_keys=True)
    with open(path[0:-5] + '_spotmap.json', 'w') as f:
        json.dump(spot_map, f, indent=4, sort_keys=True)

'''
