#!/usr/bin/env python
import sys, os
import random
import pprint
import requests
import time
import uuid

BASE_URL = os.getenv('WAREHOUSE_URL', 'http://localhost:8000/')
SITE_URL = os.getenv('SITE_URL', 'http://localhost:8080/')
AUTH_TOKEN = os.getenv('GWM_AUTH_TOKEN', 'autobootstrap')
ORG_ID = os.getenv('ORG_ID', '1')
SITE_NAME = os.getenv('WORLD', 'tatsumi')

def spotsList():
    spots_list = [
        {"pick_spot": 13, "drop_spot": 9},
        {"pick_spot": 2, "drop_spot": 7},
        {"pick_spot": 3, "drop_spot": 8},
        {"pick_spot": 4, "drop_spot": 11},
        {"pick_spot": 5, "drop_spot": 10},
        {"pick_spot": 6, "drop_spot": 7},
        {"pick_spot": 12, "drop_spot": 11},
        {"pick_spot": 1, "drop_spot": 8},
        {"pick_spot": 5, "drop_spot": 10},
        {"pick_spot": 3, "drop_spot": 7},
        {"pick_spot": 4, "drop_spot": 11},
        {"pick_spot": 2, "drop_spot": 8},
        {"pick_spot": 1, "drop_spot": 9},
        {"pick_spot": 12, "drop_spot": 7},
        {"pick_spot": 4, "drop_spot": 11},
        {"pick_spot": 5, "drop_spot": 10},
        {"pick_spot": 6, "drop_spot": 8},
        {"pick_spot": 3, "drop_spot": 7},
        {"pick_spot": 2, "drop_spot": 9},
        {"pick_spot": 13, "drop_spot": 11}
    ]
    return spots_list

def createWork(ext_id, work_type, dest_spot=None, agent=0, src_spot=None, priority=1):
    spot_info = ""
    if dest_spot is not None:
        spot_info += ',"dest_spot":' + str(dest_spot)
    if src_spot is not None:
        spot_info += ',"src_spots":[' + str(src_spot) + ']'
    agent_data = (',"assigned_agent":{}'.format(agent) if agent != 0 else "")
    payload = '{' + '"ext_tracking_id":"{}","type":"{}"{},"status":"NEW","priority":{}{}'.format(ext_id, work_type,
                                                                                                 agent_data, priority,
                                                                                                 spot_info) + '}'
    return payload


def makeHeaders():
    return {'Authorization': 'Token ' + AUTH_TOKEN,
            'X-RRAMR-Org': ORG_ID,
            'X-RRAMR-Site': SITE_NAME,
            'Content-Type': 'application/json'}


def ensureConnection(timeout):
    """Wait for WMS to come up"""
    print("Trying to connect to warehouse at url " + BASE_URL + " using authentication token " + AUTH_TOKEN)
    print("Use environment variables WAREHOUSE_URL and GWM_AUTH_TOKEN to change these settings")
    start = time.time()
    while True:
        if time.time() - start > timeout:
            print("Timed out trying to connect to server")
            sys.exit(1)
        try:
            print(BASE_URL + 'v1/agent')
            response = requests.get(BASE_URL + 'v1/agent', headers=makeHeaders())
            if response.status_code < 300:
                print("Connected")
                return
            else:
                print("Response code {}".format(response.status_code))
                time.sleep(3)
        except requests.exceptions.RequestException as e:
            print("Connection refused with {}.  Retrying...".format(e))
            time.sleep(3)
            continue

def sendPayloadMove(pick_spot, drop_spot):
    ext_work_id = str(uuid.uuid4())
    request_url = BASE_URL + 'v1/work'
    payload = createWork(ext_work_id, "PAYLOAD_MOVE", dest_spot=drop_spot, src_spot=pick_spot)
    try:
        response = requests.post(request_url, headers=makeHeaders(), data=payload)
    except:
        print('Exception while sending payload request')
        return
    if response.status_code >= 300:
        print("Failed to send request")
        return
    return response.json()['id']


def getSpots(spot_type):
    ext_work_id = str(uuid.uuid4())
    request_url = BASE_URL + 'v1/spot'
    try:
        response = requests.get(request_url + '?type=' + str(spot_type), headers=makeHeaders())
    except:
        print('Exception while sending payload request')
        return
    if response.status_code >= 300:
        print("Failed to send request")
        return
    return response.json()


def demo_random_payload_moves(num_moves):
    action_spots = getSpots("action")
    drop_spots = getSpots("drop")
    work_queue = []
    drop_queue = set(range(0, len(drop_spots) - 1))
    pick_queue = set(range(0, len(action_spots) - 1))
    previous_drops = []
    previous_pick = []
    for i in range(0, num_moves):
        dropable_spots = list(drop_queue - set(previous_drops))
        pickable_spots = list(pick_queue - set(previous_pick))
        j = random.randint(0, len(dropable_spots) - 1)
        k = random.randint(0, len(pickable_spots) - 1)
        previous_drops.append(dropable_spots[j])
        previous_pick.append(pickable_spots[k])
        if len(dropable_spots) > 3:
            previous_drops.pop(0)
        if len(pickable_spots) > 3:
            previous_drops.pop(0)
        work_queue.append(sendPayloadMove(action_spots[pickable_spots[k]]['id'], drop_spots[dropable_spots[j]]['id']))
    return work_queue

def demo_listed_payload_moves(spots_list):
    work_queue = []
    for spots in spots_list:
        work_queue.append(sendPayloadMove(spots["pick_spot"], spots["drop_spot"]))
    return work_queue

if __name__ == '__main__':
    ensureConnection(60)
    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(getSpots("drop")[0]['id'])
    # print(demo_random_payload_moves(20))
    print(demo_listed_payload_moves(spotsList()))