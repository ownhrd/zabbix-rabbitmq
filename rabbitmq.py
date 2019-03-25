#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "Igor Sidorenko"
__email__ = "ownhrd@gmail.com"
__status__ = "Production"

import yaml
import config_rabbitmq
from pyzabbix import ZabbixAPI

config = config_rabbitmq

cfg = yaml.load(open(config.file))
vars = {i['name']: i for i in cfg}
zapi = ZabbixAPI(config.url, user=config.user, password=config.password)


def get_hostid():
    host_id = zapi.host.get(output="hostid",
                            filter={"name": config.zbx_host})[0]['hostid']
    return host_id


def get_interfaceid():
    interface_id = zapi.hostinterface.get(output="extend",
                                          filter={"hostid": get_hostid()})[0]['interfaceid']
    return interface_id


def get_itemid(key):
    itemid = zapi.item.get(selectSteps="extend",
                           host=config.zbx_host,
                           filter={"key_": key})[0]['itemid']
    return itemid


def get_triggerid(priority, item_id):
    trigger_id = zapi.trigger.get(selectSteps="extend",
                                  itemids=item_id,
                                  filter={"priority": priority})[0]['triggerid']
    return trigger_id


def update_trigger(priority, vhost, queue, comments, item, severity, env, owner, project, item_id):
    zapi.trigger.update(
        triggerid=get_triggerid(priority, item_id),
        description="Length of queue more than "+str(severity)+" {} -> {}".format(vhost, queue),
        priority=priority,
        comments=comments,
        expression="{%s:%s.last()}>=%s" % (config.zbx_host, item, severity),
        tags=[
            {"tag": "env", "value": env},
            {"tag": "owner", "value": owner},
            {"tag": "project", "value": project},
            {"tag": "app", "value": "rabbitmq"}])


def create_trigger(priority, vhost, queue, comments, item, severity, env, owner, project):
    zapi.trigger.create(
        description="Length of queue more than "+str(severity)+" {} -> {}".format(vhost, queue),
        priority=priority,
        manual_close="1",
        comments=comments,
        expression="{%s:%s.last()}>=%s" % (config.zbx_host, item, severity),
        tags=[
            {"tag": "env", "value": env},
            {"tag": "owner", "value": owner},
            {"tag": "project", "value": project},
            {"tag": "app", "value": "rabbitmq"}])


def add_dependencies(triggerid, dependsontriggerid):
    zapi.trigger.adddependencies(
        triggerid=triggerid,
        dependsOnTriggerid=dependsontriggerid)


def delete_items():
    z_items = []
    for check in zapi.item.get(selectSteps="extend",
                               hostids=get_hostid()):
        item = check.get('name')
        z_items.append(item)
        if item not in vars.keys():
            # Delete item, if it exists in Zabbix, but doesn't exist in file
            item_id = zapi.item.get(selectSteps="extend",
                                    hostids=get_hostid(),
                                    filter={"name": item})[0]['itemid']
            zapi.item.delete(item_id)
            print("{} is deleted.".format(item))


def main():
    z_names = []
    for check in zapi.item.get(selectSteps="extend", hostids=get_hostid()):
        name = check.get('name')
        z_names.append(name)

    already = True

    for name in vars:
        d_triggers = {'warning': '2',
                      'average': '3',
                      'high': '4',
                      'disaster': '5'}
        d_owners = {'example_owner': '@example_owner',
                   'example_owner2': '@example_owner2'}
        d = {}
        d.clear()
        vhost = vars.get(name).get('vhost')
        queue = vars.get(name).get('queue')
        env = vars.get(name).get('env')
        project = vars.get(name).get('project')
        item = "rabbitqu.py[%s,%s,%s,%s]" % (config.ip, config.port, vhost, queue)
        comments = "Очередь: {ITEM.VALUE}"

        if name in z_names:
            info = zapi.item.get(selectSteps="extend",
                                 hostids=get_hostid(),
                                 filter={"name": name})
            # Update item from file
            print("Updated already added item: {}".format(name))
            zapi.item.update(itemid=info[0]['itemid'],
                             key_=item)

            # Update triggers
            for trigger in d_triggers:
                if trigger in vars.get(name):
                    severity = vars.get(name).get(trigger)
                    for owner in d_owners:
                        if owner in vars.get(name).get('owner'):
                            update_trigger(d_triggers[trigger], vhost, queue, comments, item, severity, env, d_owners[owner], project, get_itemid(item))

        else:
            already = False
            print("Add item: {}".format(name))

            # Create item
            zapi.item.create(hostid=get_hostid(),
                             name=name,
                             key_=item,
                             history="1w",
                             delay="60",
                             type="10",
                             value_type="3",
                             interfaceid=get_interfaceid())

            # Create triggers
            for trigger in d_triggers:
                if trigger in vars.get(name):
                    severity = vars.get(name).get(trigger)
                    for owner in d_owners:
                        if owner in vars.get(name).get('owner'):
                            create_trigger(d_triggers[trigger], vhost, queue, comments, item, severity, env, d_owners[owner], project)
                            d.update({trigger: get_triggerid(d_triggers[trigger], get_itemid(item))})

            # Add triggers dependencies
            # Warning
            if vars.get(name).get('warning'):
                if vars.get(name).get('average'):
                    add_dependencies(d['warning'], d['average'])

                if vars.get(name).get('high'):
                    add_dependencies(d['warning'], d['high'])

                if vars.get(name).get('disaster'):
                    add_dependencies(d['warning'], d['disaster'])

            # Average
            if vars.get(name).get('average'):
                if vars.get(name).get('high'):
                    add_dependencies(d['average'], d['high'])

                if vars.get(name).get('disaster'):
                    add_dependencies(d['average'], d['disaster'])

            # High
            if vars.get(name).get('high'):
                if vars.get(name).get('disaster'):
                    add_dependencies(d['high'], d['disaster'])

        if already:
            print("Done")


if __name__ == '__main__':
    delete_items()
    main()