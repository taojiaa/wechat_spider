import os
import requests
import time
from pymongo import MongoClient
from src.spider import ArticleSpider


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
            "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0Chrome/57.0.2987.132 MQQBrowser/6.2 Mobile",
        }

        official_info = self._get_official_info()
        self.fake_id = official_info['fakeid']

        self.spider = ArticleSpider(fake_id=self.fake_id,
                                    token=self.token,
                                    cookie=self.cookie,
                                    pass_ticket=self.pass_ticket,
                                    appmsg_token=self.appmsg_token,
                                    key=self.key,
                                    uin=self.uin,
                                    headers=self.headers)

        self.client = MongoClient(os.getenv('MONGO_URL'))

    def _get_official_info(self):
        api = "https://mp.weixin.qq.com/cgi-bin/searchbiz"
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
            official = requests.get(api, headers=self.headers, params=params, verify=False)
            return official.json()["list"][0]
        except Exception:
            raise Exception("The public name doesn't match.")

    def _get_article_list(self, begin, count):
        api = "https://mp.weixin.qq.com/cgi-bin/appmsg"
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
        return requests.get(api, headers=self.headers, params=params, verify=False).json()

    def _save_mongo(self, data):
        collection = self.client['wechat'][self.nickname]
        inserted_articles = set(item['article_id'] for item in collection.find({}, {'_id': 0, 'article_id': 1}))
        for info in data:
            if info['article_id'] not in inserted_articles:
                collection.insert_one(info)

    def crawl_latest_posts(self, num, begin=0, count=5):
        while begin < num:
            page_info = []
            time.sleep(0.2)
            resp = self._get_article_list(begin, count)
            if resp['base_resp']['err_msg'] == 'ok' and resp['base_resp']['ret'] == 0 and "app_msg_list" in resp:
                for item in resp["app_msg_list"]:
                    info = self.spider.get_article_info(item)
                    page_info.append(info)
                self._save_mongo(page_info)
                print(f"{count} articles in page {begin // count + 1} have been inserted to the database.")
            begin += count
