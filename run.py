#!/usr/bin/env python

import os
import sys
import json
import time
import logging
import requests
import argparse
import pprint
import code

# add directory of this file to PATH, so that the package will be found
sys.path.append(os.path.dirname(os.path.realpath(__file__)))

# import Pokemon Go API lib
from pgoapi import pgoapi
from pgoapi import utilities as util

log = logging.getLogger(__name__)

def init_config():
    parser = argparse.ArgumentParser()
    config_file = "config.json"

    # If config file exists, load variables from json
    load   = {}
    if os.path.isfile(config_file):
        with open(config_file) as data:
            load.update(json.load(data))

    # Read passed in Arguments
    required = lambda x: not x in load
    parser.add_argument("-a", "--auth_service", help="Auth Service ('ptc' or 'google')",
        required=required("auth_service"))
    parser.add_argument("-u", "--username", help="Username", required=required("username"))
    parser.add_argument("-p", "--password", help="Password")
    parser.add_argument("-l", "--location", help="Location", required=required("location"))
    parser.add_argument("-d", "--debug", help="Debug Mode", action='store_true')
    parser.add_argument("-t", "--test", help="Only parse the specified location", action='store_true')
    parser.set_defaults(DEBUG=False, TEST=False)
    config = parser.parse_args()

    # Passed in arguments shoud trump
    for key in config.__dict__:
        if key in load and config.__dict__[key] == None:
            config.__dict__[key] = str(load[key])

    if config.__dict__["password"] is None:
        log.info("Secure Password Input (if there is no password prompt, use --password <pw>):")
        config.__dict__["password"] = getpass.getpass()

    if config.auth_service not in ['ptc', 'google']:
      log.error("Invalid Auth service specified! ('ptc' or 'google')")
      return None

    return config

def main():
    # log settings
    # log format
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(module)10s] [%(levelname)5s] %(message)s')
    # log level for http request class
    logging.getLogger("requests").setLevel(logging.WARNING)
    # log level for main pgoapi class
    logging.getLogger("pgoapi").setLevel(logging.INFO)
    # log level for internal pgoapi class
    logging.getLogger("rpc_api").setLevel(logging.INFO)

    config = init_config()
    if not config:
        return

    if config.debug:
        logging.getLogger("requests").setLevel(logging.DEBUG)
        logging.getLogger("pgoapi").setLevel(logging.DEBUG)
        logging.getLogger("rpc_api").setLevel(logging.DEBUG)

    if config.test:
        return

    # instantiate pgoapi
    api = pgoapi.PGoApi()

    api.set_position(config.latitude, config.longitude, 0.0)

    if not api.login(config.auth_service, config.username, config.password):
        return

    # get inventory call
    # ----------------------
    response = api.get_inventory()

    approot = os.path.dirname(os.path.realpath(__file__))

    with open(os.path.join(approot, 'data/moves.json')) as data_file:
        moves = json.load(data_file)

    with open(os.path.join(approot, 'data/pokemon.json')) as data_file:
        pokemon = json.load(data_file)

    def format(i):
        i = i['inventory_item_data']['pokemon_data']
        i = {k: v for k, v in i.items() if k in ['nickname','move_1', 'move_2', 'pokemon_id', 'individual_defense', 'stamina', 'cp', 'individual_stamina', 'individual_attack']}
        i['individual_defense'] =  i.get('individual_defense', 0)
        i['individual_attack'] =  i.get('individual_attack', 0)
        i['individual_stamina'] =  i.get('individual_stamina', 0)
        i['power_quotient'] = round(((float(i['individual_defense']) + float(i['individual_attack']) + float(i['individual_stamina'])) / 45) * 100)
        i['name'] = list(filter(lambda j: int(j['Number']) == i['pokemon_id'], pokemon))[0]['Name']
        i['move_1'] = list(filter(lambda j: j['id'] == i['move_1'], moves))[0]['name']
        i['move_2'] = list(filter(lambda j: j['id'] == i['move_2'], moves))[0]['name']
        return i

    all_pokemon = filter(lambda i: 'pokemon_data' in i['inventory_item_data'] and 'is_egg' not in i['inventory_item_data']['pokemon_data'], response['responses']['GET_INVENTORY']['inventory_delta']['inventory_items'])
    all_pokemon = list(map(format, all_pokemon))
    all_pokemon.sort(key=lambda x: x['pokemon_id'], reverse=True)

    print(tabulate(all_pokemon, headers = "keys"))

if __name__ == '__main__':
    main()