import os
import requests
import time
from pymongo import MongoClient, errors
from src.spider import ArticleSpider


class WechatSpider:
    def __init__(self, nickname, token, cookie, pass_ticket, appmsg_token, key, uin):
        self.nickname = nickname

        self.token = token
        self.cookie = cookie
        self.pass_ticket = pass_ticket
        self.appmsg_token = appmsg_token
        self.key = key
        self.uin = uin

        self.headers = {
            "Cookie":
            self.cookie,
            "User-Agent":
            "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0Chrome/57.0.2987.132 MQQBrowser/6.2 Mobile",
        }

        official_info = self._get_official_info()
        self.fake_id = official_info.get('fakeid')

        self.spider = ArticleSpider(fake_id=self.fake_id,
                                    token=self.token,
                                    cookie=self.cookie,
                                    pass_ticket=self.pass_ticket,
                                    appmsg_token=self.appmsg_token,
                                    key=self.key,
                                    uin=self.uin,
                                    headers=self.headers)
        self.connect_db()

    def connect_db(self):
        try:
            self.client = MongoClient(os.getenv('MONGO_URL'))
            self.client.server_info()
            self.db_status = 'ok'
        except Exception:
            self.db_status = 'error'

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
            print("The public name doesn't match or the personal info has been expired.")
            return {}

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
        cnt = 0
        for info in data:
            if info['article_id'] not in inserted_articles:
                collection.insert_one(info)
                cnt += 1
        return cnt

    def crawl_latest_posts(self, begin, end, count):
        while begin < end:
            page_info = []
            resp = self._get_article_list(begin, count)
            if resp['base_resp']['err_msg'] == 'ok' and resp['base_resp']['ret'] == 0 and "app_msg_list" in resp:
                for item in resp["app_msg_list"]:
                    info = self.spider.get_article_info(item)
                    if info:
                        page_info.append(info)
                    time.sleep(0.5)
                if self.db_status == 'ok':
                    cnt = self._save_mongo(page_info)
                    print(f"Page {begin} to {begin + count}: {cnt} new articles have been inserted to the database.")
                else:
                    print('Cannot connect to your local mongo database.')
                    break
            else:
                print('The token has been expired.')
                break
            begin += count
