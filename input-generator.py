#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright 2017-present i2CAT
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#   author          =   Leonardo Ochoa-Aday (i2CAT Foundation)
#   author_email    =   leonardo.ochoa@i2cat.net
#

"""
MTO Input Generator
"""

import os
import math
import json
import time
import requests
import datetime
import configparser

from fog05mm1 import Mm1
from coolname import generate_slug


class MTOException(Exception):
    pass


class InputGenerator:
    """
    MTO Input Generator Class
    """

    def __init__(self):
        config = configparser.ConfigParser()
        config.read('config.cfg')
        self.base_url = "{0}://{1}:{2}".format(
            config["mto"]["protocol"],
            config["mto"]["host"],
            config["mto"]["port"])
        self.vim_url = "{0}/api/v0.1/nfv_mano/vim".format(self.base_url)
        self.ns_descriptors_url = "{0}/api/v0.1/nfv_mano/ns_descriptors". \
            format(self.base_url)
        self.vim_network_name = config.get('vim_openstack', 'network')
        self.instantiate_url = "{0}/api/v0.1/generic_service". \
            format(self.base_url)
        self.headers = {"Accept": "application/json"}
        self.token = None
        _vim_fog05_host = config.get('vim_fog05', 'host')
        _vim_fog05_port = config.get('vim_fog05', 'port')
        self.vim_fog05_user = config.get('vim_fog05', 'user')
        self.vim_fog05_user_pass = config.get('vim_fog05', 'user_pass')
        self.vim_fog05_tenant = config.get('vim_fog05', 'tenant')
        self.vim_fog05_type = config.get('vim_fog05', 'type')
        self.vim_fog05_main_api_url = "{0}:{1}".format(_vim_fog05_host,
                                                       _vim_fog05_port)
        self.__conf = config['meao']
        self.endpoint = self.__conf['host'] + ':' + self.__conf['port'] + self.__conf['url']
        self.api = Mm1(self.endpoint)

    def post_vim(self, name, description, config=None):
        vim_data = {"name": name,
                    "vim_tenant_name": self.vim_fog05_tenant,
                    "vim_url": self.vim_fog05_main_api_url,
                    "vim_user": self.vim_fog05_user,
                    "vim_password": self.vim_fog05_user_pass,
                    "vim_type": self.vim_fog05_type,
                    "description": description}
        if config is not None:
            vim_data["config"] = config
        response = requests.post(self.vim_url,
                                 headers=self.headers,
                                 verify=False,
                                 json=vim_data)
        try:
            vim_id_post = json.loads(response.text)
            if "id" not in vim_id_post:
                raise MTOException
            return vim_id_post
        except ValueError:
            raise MTOException

    def get_ns_descriptors(self):
        response = requests.get(self.ns_descriptors_url,
                                headers=self.headers,
                                verify=False)
        return json.loads(response.text)

    def post_ns_instance(self, nsd_id, name,
                         description,
                         vim_account_id):
        ns_data_int = {"nsdId": nsd_id,
                       "nsName": name,
                       "nsDescription": description,
                       "vimAccountId": vim_account_id}
        response = requests.post(self.instantiate_url,
                                 headers=self.headers,
                                 verify=False,
                                 json=ns_data_int)
        instantiation_data = json.loads(response.text)
        return instantiation_data

    def get_ns_instance(self, nsr_id=None):
        if nsr_id is not None:
            inst_url = "{0}/{1}".format(self.instantiate_url,
                                        nsr_id)
        else:
            inst_url = "{0}".format(self.instantiate_url)
        response = requests.get(inst_url,
                                headers=self.headers,
                                verify=False)
        if response.status_code not in (200, 201, 202):
            raise MTOException
        return json.loads(response.text)

    def register_mec_appd(self):
        platform_id = 'testp'
        appd_simple_example = {
            "appDId": "example-meapp1",
            "appName": "example_mec_application",
            "appProvider": "ADLINK",
            "appDVersion": "1.0",
            "appSoftVersion": "",
            "mecVersion": [
                "1"
            ],
            "appDescription": "Simple MEC Application",
            "appServiceRequired": [],
            "appServiceOptional": [],
            "appServiceProduced": [],
            "appFeatureRequired": [],
            "appFeatureOptional": [],
            "transportDependencies": [],
            "appTrafficRule": [],
            "appDNSRule": [],
            "appLatency": {
                "timeUnit": 10,
                "latency": "ms"
            }
        }
        return self.api.applications.add(platform_id, appd_simple_example)

    def delete_ns_instance(self, nsr_id):
        inst_url = "{0}/{1}".format(self.instantiate_url,
                                    nsr_id)
        return requests.delete("{0}".format(inst_url),
                               headers=self.headers,
                               verify=False)

    def delete_vim(self, vim_id_int):
        return requests.delete("{0}/{1}".format(self.vim_url,
                                                vim_id_int),
                               headers=self.headers,
                               verify=False)


if __name__ == "__main__":
    TIMEOUT_FOR_NS = 300     # 5 min
    NUMBER_OF_INPUTS = [1]
    DATA_STORE_PATH = 'D:/GitHub/mto-evaluation/notebooks/results'

    init_time = time.time()
    input_generator = InputGenerator()

    list_of_ns = []
    list_of_ns_tmp = []
    list_of_vim = []
    for inputs in NUMBER_OF_INPUTS:
        for request in range(inputs):
            print("\n  ---  INPUT {0}/{1} ({2}) ---  ".format(
                request, inputs+1,
                datetime.datetime.now()))

            # 1) create fog05 vim
            vim_id = input_generator.post_vim(name=generate_slug(),
                                              description='MTO EVAL Tests')
            print("\n1) VIM ACCOUNT CREATED: {0}".format(vim_id))
            list_of_vim.append(vim_id['id'])

            # 2) get NSD
            ns_descriptors = input_generator.get_ns_descriptors()
            alpine_nsd_id = [x["_id"] for x in ns_descriptors
                             if x["name"] == "alpine_2vnf_ns"][0]
            print("\n2) NSD: {0}".format(alpine_nsd_id))

            # 3) instantiate NS
            ns_instance = input_generator.post_ns_instance(nsd_id=alpine_nsd_id,
                                                           name=generate_slug(),
                                                           description='MTO EVAL Tests',
                                                           vim_account_id=vim_id['id'])
            print("\n3) NS INSTANCE CREATED: {0}:".format(ns_instance))
            list_of_ns.append(ns_instance['id'])
            list_of_ns_tmp.append(ns_instance['id'])

        counter = 0
        time_to_live = [TIMEOUT_FOR_NS for x in
                        range(len(list_of_ns_tmp))]
        while len(list_of_ns_tmp) >= 1:
            counter += 1
            time_to_live[counter-1] -= 1
            ns_data = input_generator.get_ns_instance(list_of_ns_tmp[counter-1])
            op_status = ns_data["operational-status"]
            config_status = ns_data["config-status"]
            print("  Operational Status = {0}, Config Status = {1} -- {2} [NS TTL: {3}]"
                  .format(op_status, config_status, list_of_ns_tmp[counter-1], time_to_live))
            if op_status == "failed" or \
                    config_status == "configured" or \
                    op_status == "terminating" or \
                    time_to_live[counter-1] <= 0:
                list_of_ns_tmp.pop(counter-1)
                time_to_live.pop(counter-1)
            if counter >= len(list_of_ns_tmp):
                counter = 0

        # 4) MEC stuff here
        mec_app = input_generator.register_mec_appd()
        mec_app_info = mec_app.get("ApplicationInfo")
        print("\n4) APPD DEPLOYED IN MEC PLATFORM (testp)")

        for ns in list_of_ns:
            # 5) delete NS
            input_generator.delete_ns_instance(ns)
            print("\n5) NS INSTANCE DELETED: {0}".format(ns))

        for vim in list_of_vim:
            # 6) delete fog05 vim
            input_generator.delete_vim(vim_id_int=vim)
            print("\n6) VIM ACCOUNT DELETED: {0}".format(vim))

        elapse = (time.time() - init_time) / 60   # unit (min)

        os.system("python zabbixhistory2csv.py -m {0} -o {1}/scenario-2/{2}-request".format(
            math.ceil(elapse), DATA_STORE_PATH, inputs))
