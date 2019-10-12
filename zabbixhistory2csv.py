import sys
import csv
import time
import getpass
import datetime
import argparse

from pyzabbix import ZabbixAPI
from time import gmtime, strftime


# Define some global variables


def get_zapi(host, user, password, verify):
    """
    :param host:
    :param user:
    :param password:
    :param verify:
    :return:
    """
    zapi = ZabbixAPI(host)
    # Whether or not to verify the SSL certificate
    zapi.session.verify = verify
    zapi.login(user, password)
    return zapi


def get_history(zapi, itemid, time_from, time_till, max_days):
    """
    The zabbix api call for history.get requires that we know the item's
    data type. We can get this through a call to the zabbix api since we
    have the itemid.
    :param zapi:
    :param itemid:
    :param time_from:
    :param time_till:
    :param max_days:
    :return:
    """
    items = zapi.item.get(itemids=itemid, output=['value_type'])
    ret = []

    # The only successful outcome would be a list with one item. If we get
    # more or less, we should assume that the item doesn't exist.
    if len(items) == 1:
        value_type = items[0]['value_type']
    else:
        raise Exception('Item not found')

    max_secs = max_days * 3600

    # Make call to zabbix API for history
    while time_till > time_from:
        if time_till - time_from > max_secs:
            ret += zapi.history.get(itemids=itemid,
                                    time_from=time_from,
                                    time_till=time_from + max_secs,
                                    history=value_type,
                                    sortfield='clock',
                                    output='extend'
                                    )
            time_from += max_secs
        else:
            ret += zapi.history.get(itemids=itemid,
                                    time_from=time_from,
                                    time_till=time_till,
                                    history=value_type,
                                    sortfield='clock',
                                    output='extend'
                                    )
            break
    return ret


def write_csv(objects, output_file):
    """
    :param objects:
    :param output_file:
    :return:
    """
    # Open the output_file and instanstiate the csv.writer object
    f = csv.writer(open(output_file, "w"))

    # Write the top line of the output_file which describes the columns
    f.writerow(objects[0].keys())

    # Description for history objects:
    # https://www.zabbix.com/documentation/2.0/manual/appendix/api/history/definitions

    # For each object, write a row to the csv file.
    for o in objects:
        row = []
        for key in o.keys():
            value = o[key]
            if key == 'clock':
                time_tmp = datetime.datetime.fromtimestamp(
                    int(o[key])).strftime('%Y-%m-%d %H:%M:%S')
                value = time_tmp
            row.append(value)
        f.writerow(row)


def build_parsers():
    """
    Builds the argparser object
    :return: Configured argparse.ArgumentParser object
    """
    parser = argparse.ArgumentParser(
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            description='zabbixhistory2csv'
    )
    parser.add_argument("-V", "--verify",
                        default='True',
                        choices=['True', 'False'],
                        help="Verify SSL (True, False)")
    parser.add_argument("-H", "--host",
                        dest='host',
                        required=False,
                        help="Zabbix API host"
                             "example: https://zabbixhost.example.com/zabbix")
    parser.add_argument("-u", "--user",
                        default=getpass.getuser(),
                        help="Zabbix API user")
    parser.add_argument("-m", "--minutes-ago",
                        default='60',
                        type=int,
                        help='How many minutes worth of history should'
                             'be returned going back in time from right now')
    parser.add_argument("-o", "--output-file",
                        default='output.csv',
                        help="Output file in csv format\nDefault: output.csv")
    parser.add_argument("-i", "--itemid",
                        required=False,
                        help="The zabbix item that we will use "
                             "in our history.get api call.")
    parser.add_argument("-d", "--max-days",
                        choices=range(1, 31),
                        default=15,
                        type=int,
                        help="The max days worth of history that we will "
                             "request from zabbix per request")
    return parser


if __name__ == '__main__':
    # Load argparse and parse arguments
    parser = build_parsers()
    args = parser.parse_args(sys.argv[1:])

    # Generate parameters for get_zapi function
    seconds_ago = int(args.minutes_ago) * 60
    now = int(time.time())
    password = PASSWORD

    # Generate the zapi object so we can pass it to the get_history function
    try:
        zapi = get_zapi(ZABBIX_URL,
                        USER, password,
                        eval(args.verify))
    except Exception as e:
        if 'Login name or password is incorrect.' in str(e):
            print('Unauthorized: Please check your username and password')
        else:
            print('Error connecting to zabbixapi: {0}'.format(e))
        exit()

    # Put here metrics to be retrieved
    zabbix_itemids = {               # [CPU idle time (%), Available memory (B)]
        'edge_vim': [29060, 29077],
        'meao': [28785, 28802],
        'mto': [28937, 28954],
        'osm': [28697, 28714]
                      }

    # Define the mappings here
    zabix_mapp = {
        'cpu-idle-time': [29060, 28785, 28937, 28697],
        'available-memory': [29077, 28802, 28954, 28714]
                 }

    # Start the loop to retrieve the metrics data
    for vm_name in zabbix_itemids.keys():
        for item_id in zabbix_itemids[vm_name]:

            # generate the list of history objects returned from zabbix api.
            try:
                results = get_history(zapi, item_id,
                                      (now - seconds_ago),
                                      now, args.max_days)
            except Exception as e:
                message = ('An error has occurred.  --max-days may be set too high. '
                           'Try decreasing it value.\nError:\n{0}')
                print(message.format(e))
                exit()

            timestamp = strftime("%Y-%m-%d__%H-%M-%S", gmtime())

            # Determine name of item_id
            if item_id in zabix_mapp['cpu-idle-time']:
                item_name = 'cpu'
            else:
                item_name = 'ram'

            # Write the results to file in csv format
            write_csv(results, '{0}/{1}-{2}-{3}.csv'.format(DATA_STORE_PATH, timestamp, vm_name, item_name))
            print('\nWriting {0} minutes worth of history to {1}-{2}-{3}.csv'.format(
                    args.minutes_ago, timestamp, vm_name, item_name))
