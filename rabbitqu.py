#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "Igor Sidorenko"
__email__ = "ownhrd@gmail.com"
__status__ = "Production"

import sys
import requests

if __name__ == '__main__':
    if len(sys.argv) <= 4:
        print 'Too few params (need 4)'
        sys.exit(1)

    url = 'http://' + sys.argv[1] + ':' + sys.argv[2] + '/api/queues/' + \
        sys.argv[3] + '/' + sys.argv[4]
    r = requests.get(url, auth=('user', 'password'))

    if r.status_code == 200:
        print r.json()['messages']
        sys.exit(0)
    else:
        print 'Error ' + str(r.status_code)
        sys.exit(1)