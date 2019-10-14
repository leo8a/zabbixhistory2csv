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
import threading
import configparser


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
            vim_id = json.loads(response.text)
            if "id" not in vim_id:
                raise MTOException
            return vim_id
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
        ns_data = {"nsdId": nsd_id,
                   "nsName": name,
                   "nsDescription": description,
                   "vimAccountId": vim_account_id,
                   "mec": {'mec_platform_id': 'testp'}}
        response = requests.post(self.instantiate_url,
                                 headers=self.headers,
                                 verify=False,
                                 json=ns_data)
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

    def delete_ns_instance(self, nsr_id):
        inst_url = "{0}/{1}".format(self.instantiate_url,
                                    nsr_id)
        return requests.delete("{0}".format(inst_url),
                               headers=self.headers,
                               verify=False)

    def delete_vim(self, vim_id):
        return requests.delete("{0}/{1}".format(self.vim_url,
                                                vim_id),
                               headers=self.headers,
                               verify=False)

    # def worker_lcm(self, input_number):
    #     init_time = datetime.datetime.now()
    #     print("\n  ---  INPUT {0} ({1}) ---  ".format(input_number, init_time))
    #
    #     # 1) create fog05 vim
    #     vim_id = self.post_vim(name=generate_slug(),
    #                            description='MTO EVAL Tests')
    #     print("\n1) VIM ACCOUNT CREATED: {0}".format(vim_id))
    #
    #     # 2) get NSD
    #     nsds = self.get_ns_descriptors()
    #     alpine_nsd_id = [x["_id"] for x in nsds
    #                      if x["name"] == "alpine_2vnf_ns"][0]
    #     print("\n2) NSD: {0}".format(alpine_nsd_id))
    #
    #     # 3) instantiate NS
    #     ns_instance = self.post_ns_instance(nsd_id=alpine_nsd_id,
    #                                         name=generate_slug(),
    #                                         description='MTO EVAL Tests',
    #                                         vim_account_id=vim_id['id'])
    #     success = False
    #     while success is False:
    #         ns_data = self.get_ns_instance(ns_instance['id'])
    #         op_status = ns_data["operational-status"]
    #         config_status = ns_data["config-status"]
    #         print("    Operational Status = {}, Config Status = {}"
    #               .format(op_status, config_status))
    #         if op_status == "running" and config_status == "configured":
    #             success = True
    #             break
    #     print("\n3) NS INSTANCE CREATED: {0}:".format(ns_instance))
    #
    #     # 4) delete NS
    #     self.delete_ns_instance(ns_instance['id'])
    #     print("\n4) NS INSTANCE DELETED: {0}".format(ns_instance['id']))
    #
    #     # 5) delete fog05 vim
    #     self.delete_vim(vim_id=vim_id['id'])
    #     print("\n5) VIM ACCOUNT DELETED: {0}".format(vim_id))


if __name__ == "__main__":
    TIMEOUT_FOR_NS = 300     # 5 min
    NUMBER_OF_INPUTS = 20

    init_time = time.time()
    input_generator = InputGenerator()

    list_of_ns = []
    list_of_ns_tmp = []
    list_of_vim = []
    for request in range(NUMBER_OF_INPUTS):
        print("\n  ---  INPUT {0} ({1}) ---  ".format(
            request,
            datetime.datetime.now()))

        # 1) create fog05 vim
        vim_id = input_generator.post_vim(name="test_eval_mto_{0}".format(request),
                                          description='MTO EVAL Tests')
        print("\n1) VIM ACCOUNT CREATED: {0}".format(vim_id))
        list_of_vim.append(vim_id['id'])

        # 2) get NSD
        nsds = input_generator.get_ns_descriptors()
        alpine_nsd_id = [x["_id"] for x in nsds
                         if x["name"] == "alpine_2vnf_ns"][0]
        print("\n2) NSD: {0}".format(alpine_nsd_id))

        # 3) instantiate NS
        ns_instance = input_generator.post_ns_instance(nsd_id=alpine_nsd_id,
                                                       name="test_eval_mto_{0}".format(request),
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
            print("    NS TTL: {0}".format(time_to_live))
            ns_data = input_generator.get_ns_instance(list_of_ns_tmp[counter-1])
            op_status = ns_data["operational-status"]
            config_status = ns_data["config-status"]
            print("    Operational Status = {0}, Config Status = {1} -- {2}"
                  .format(op_status, config_status, list_of_ns_tmp[counter-1]))
            if op_status == "failed" or \
                    config_status == "configured" or \
                    op_status == "terminating" or \
                    time_to_live[counter-1] <= 0:
                list_of_ns_tmp.pop(counter-1)
                time_to_live.pop(counter-1)
            if counter >= len(list_of_ns_tmp):
                counter = 0

    for ns in list_of_ns:
        # 4) delete NS
        input_generator.delete_ns_instance(ns)
        print("\n4) NS INSTANCE DELETED: {0}".format(ns))

    for vim in list_of_vim:
        # 5) delete fog05 vim
        input_generator.delete_vim(vim_id=vim)
        print("\n5) VIM ACCOUNT DELETED: {0}".format(vim))

    elapse = (time.time() - init_time) / 60   # unit (min)

    os.system("python zabbixhistory2csv.py -m {0}".format(
        math.ceil(elapse)))
