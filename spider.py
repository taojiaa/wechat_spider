import os
import requests
import time
from bs4 import BeautifulSoup
from pymongo import MongoClient


class WechatSpider:
    def __init__(self, nickname):
        self.nickname = nickname

        self.token = os.getenv('TOKEN')
        self.cookie = os.getenv('COOKIE')
        self.pass_ticket = os.getenv('PASS_TICKET')
        self.appmsg_token = os.getenv('APPMSG_TOKEN')
        self.key = os.getenv('KEY')
        self.uin = os.getenv('UIN')

        self.headers = {
            "Cookie":
            self.cookie,
            "User-Agent":
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.119 Safari/537.36",
        }

        official_info = self.__get_official_info()
        self.fake_id = official_info['fakeid']
        self.alias = official_info['alias']

    def __get_official_info(self):
        search_url = "https://mp.weixin.qq.com/cgi-bin/searchbiz"
        params = {
            "query": self.nickname,
            "count": '5',
            "action": "search_biz",
            "ajax": "1",
            "begin": '0',
            "lang": "zh_CN",
            "f": "json",
            'token': self.token
        }

        try:
            official = requests.get(search_url, headers=self.headers, params=params, verify=False)
            return official.json()["list"][0]
        except Exception:
            raise Exception("The public name doesn't match.")

    def __convert_date(self, times):
        timearr = time.localtime(times)
        date = time.strftime("%Y-%m-%d %H:%M:%S", timearr)
        return date

    def __crawl_article_content(self, content_url):
        try:
            html = requests.get(content_url, verify=False).text
        except Exception:
            print(content_url)
            pass
        else:
            bs = BeautifulSoup(html, 'html.parser')
            js_content = bs.find(id='js_content')
            if js_content:
                p_list = js_content.find_all('p')
                content_list = list(map(lambda p: p.text, filter(lambda p: p.text != '', p_list)))
                content = ''.join(content_list)
                return content

    def run(self, num):
        begin, count = 0, 5
        while begin < num:
            page_info = []
            time.sleep(1)
            ls = self.get_article_list(begin, count)
            if "app_msg_list" in ls:
                for item in ls["app_msg_list"]:
                    info = self.get_article_info(item)
                    page_info.append(info)
                self.save_mongo(page_info)
            print(f"Articles of page {begin // count + 1} has been inserted to the database.")
            begin += count

    def get_article_list(self, begin, count):
        url = "https://mp.weixin.qq.com/cgi-bin/appmsg"
        params = {
            "token": self.token,
            "lang": "zh_CN",
            "f": "json",
            "ajax": "1",
            "action": "list_ex",
            "begin": str(begin),
            "count": str(count),
            "fakeid": self.fake_id,
            "type": '9',
        }
        return requests.get(url, headers=self.headers, params=params, verify=False).json()

    def get_article_info(self, item):
        url = item['link']
        appmsgstat = self.get_article_stat(url)
        info = {
            "title": item['title'],
            "readNum": appmsgstat.get('read_num', 0),
            "likeNum": appmsgstat.get('like_num', 0),
            "digest": item['digest'],
            "date": self.__convert_date(item['update_time']),
            "url": item['link'],
            'content': self.__crawl_article_content(url),
        }
        return info

    def get_article_stat(self, link):
        mid = link.split("&")[1].split("=")[1]
        idx = link.split("&")[2].split("=")[1]
        sn = link.split("&")[3].split("=")[1]
        _biz = link.split("&")[0].split("_biz=")[1]

        url = "http://mp.weixin.qq.com/mp/getappmsgext"
        headers = {
            "Cookie":
            "rewardsn=;wxtokenkey=777;wxuin=683053783;devicetype=iPhoneiOS13.5.1;version=17000e28;lang=zh_CN",
            "User-Agent":
            "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36 MicroMessenger/6.5.2.501 NetType/WIFI WindowsWechat QBCore/3.43.901.400 QQBrowser/9.0.2524.400"
        }
        data = {"is_only_read": "1", "is_temp_url": "0", "appmsg_type": "9", 'reward_uin_count': '0'}

        params = {
            "__biz": _biz,
            "mid": mid,
            "sn": sn,
            "idx": idx,
            "key": self.key,
            "pass_ticket": self.pass_ticket,
            "appmsg_token": self.appmsg_token,
            "uin": self.uin,
            "wxtoken": "777",
        }

        content = requests.post(url, headers=headers, data=data, params=params).json()
        time.sleep(1)
        try:
            return content['appmsgstat']
        except KeyError:
            print('The token has been expired.')

    def save_mongo(self, data):
        host = "127.0.0.1"
        port = 27017

        client = MongoClient(host, port)
        collection = client['wechat'][self.nickname]
        collection.insert_many(data)


def main():
    nickname = '华东理工大学'
    ws = WechatSpider(nickname)
    ws.run(15)


if __name__ == '__main__':
    main()
