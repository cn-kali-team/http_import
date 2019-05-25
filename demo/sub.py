# -*- coding:utf-8 -*-

import requests
import json


def getDomain(domain):
    url = "http://ce.baidu.com/index/getRelatedSites?site_address={0}".format(
        domain)
    urlReq = requests.get(url)
    return urlReq.text


def main(p):
    urlRes = getDomain(p)
    allData = json.loads(urlRes)['data']
    for i in allData:
        print(i['domain'])

