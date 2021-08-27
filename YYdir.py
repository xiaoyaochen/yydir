#! /usr/bin/python
# -*- coding:utf-8 -*-

import asyncio
import argparse
from aiohttp import ClientSession,TCPConnector
from bs4 import BeautifulSoup
from datetime import datetime
import csv
from tqdm import tqdm
import hashlib

class YYdir():
    def __init__(self, urls, scanDict, scanOutput,coroutineNum,method):
        print('* YYdir ready to start.')
        self.urls = set([url if url.find('://') != -1 else 'http://{}'.format(urls) for url in urls])
        # print('* Current target:',self.urls)
        self.scanDict = scanDict
        self.q =  self.loadDict(self.scanDict)
        self.scanOutput = scanOutput
        self.coroutineNum = coroutineNum
        self.payload = self.make_payload()
        self.loop = asyncio.get_event_loop()  # 创建一个事件循环
        self.sema = asyncio.Semaphore(self.coroutineNum)
        self.tasks = []
        self.method = method

    def loadDict(self, dict_list):
        q = []
        with open(dict_list,encoding='utf-8') as f:
            for line in f:
                q.append(line.strip().lstrip('/'))
        q = set(q)
        self.data = len(q)
        if self.data > 0:
            print('* Total Dictionary:',self.data)
        else:
            print('* NO default.txt')
            quit()
        return q

    def writeOutput(self, result):
        with open(self.scanOutput, 'a',newline='') as f:
            writer = csv.writer(f)
            writer.writerow(result)
            
    async def head_scan(self, url):
        headers = {
                'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/603.3.8 (KHTML, like Gecko) Version/10.1.2 Safari/603.3.8',
                'Referer':'https://www.baidu.com',
                'Accept-Encoding':'gzip, deflate',
                'Connection':'keep-alive',
            }
        try:
            async with self.sema:
                async with ClientSession() as session:
                    async with session.head(url, headers=headers,timeout=10) as resp:
                        code = resp.status
                        if code == 200 or code == 301 or code == 403:
                            print('[ %i ] %s' % (code, url))
                            self.writeOutput([url,code])
                        self.bar.update(1)
        except Exception as e:
            print(url,e)
            self.bar.update(1)
            pass
    async def get_title(self,content):
        try:
            soup = BeautifulSoup(content, 'lxml')
            t = soup.title.string.strip()
        except Exception as e:
            t = None
        return t

    async def get_scan(self, url):
        headers = {
                # 'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/603.3.8 (KHTML, like Gecko) Version/10.1.2 Safari/603.3.8',
                'Referer':url,
                # 'Accept-Encoding':'gzip, deflate',
                # 'Connection':'keep-alive',
            }
        try:
            async with self.sema:
                async with ClientSession(connector=TCPConnector(ssl=False)) as session:
                    async with session.get(url, headers=headers,timeout=10) as resp:
                        code = resp.status
                        content = await resp.text()
                        length = len(content)
                        title =  await self.get_title(content)
                        md5hash = hashlib.md5(content.encode("utf8"))
                        md5 = md5hash.hexdigest()
                        if code == 200 or code == 301 or code == 403:
                            print('[ {} ] {} {} {}'.format(code,url,length,title))
                            self.writeOutput([url,code,title,length,md5])
                        self.bar.update(1)
        except Exception as e:
            self.bar.update(1)
            print(url,e)
            pass
    
    def make_payload(self):
        payload = []
        for url in self.urls:
            for p in self.q:
                payload.append(url + p)
        self.bar = tqdm(total=len(payload))
        return payload

    def run(self):
        for url in self.payload:
            if self.method == 'head':
                future = asyncio.ensure_future(self.head_scan(url)) 
            else:
                future = asyncio.ensure_future(self.get_scan(url))
            self.tasks.append(future) # 创建多个协程任务的列表，然后将这些协程注册到事件循环中。
        try:
            header = ['url','code','title','length','md5']
            self.writeOutput(header)
            self.loop.run_until_complete(asyncio.wait(self.tasks))   # 将协程注册到事件循环，并启动事件循环
            # self.loop.close()
        except asyncio.CancelledError as e:
            print('* Warning:CancelledError.')

if __name__ == '__main__':
    # main()
    banner = '''\
     YY  YY     YY  YY
       YY         YY
       YY         YY     dir
    '''
    print(banner)
    parser = argparse.ArgumentParser(description="This script uses the aiohttp to determine the status word.")
    # 可选参数
    parser.add_argument('-u', '--url', dest="url", help="The Single url that needs to be scanned", type=str)
    parser.add_argument('-f', '--file', dest="file", help="The urls of file that needs to be scanned", type=str)
    parser.add_argument('-d', '--dict', dest="scanDict", help="Dictionary for scanning", type=str, default="dict/default.txt")
    parser.add_argument('-o', '--output', dest="scanOutput", help="Results saved files", type=str, default='./result/{}.csv'.format(datetime.now().strftime('%Y%m%d%H%M%S')))
    parser.add_argument('-t', '--thread', dest="coroutineNum", help="Number of coroutine running the program", type=int, default=100)
    parser.add_argument('-a', '--action', dest="method",help="Method to request",type=str,default='get')
    args = parser.parse_args()
    if args.url:
        args.url = args.url.strip().strip('/')+'/'
        scan = YYdir([args.url], args.scanDict, args.scanOutput, args.coroutineNum, args.method)
        scan.run()
    elif args.file:
        with open(args.file,'r',encoding='utf-8') as urls:
            url_list = []
            for url in urls.readlines():
                url_list.append(url.strip().strip('/')+'/')
            scan = YYdir(url_list, args.scanDict, args.scanOutput, args.coroutineNum,args.method)
            scan.run()
    # print 'Scan Start!!!'
    else:
        print('No urls!!!')
        quit()
    print("* End of scan!------->{}".format(scan.scanOutput))