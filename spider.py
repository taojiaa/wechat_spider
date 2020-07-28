import requests
import urllib3
import re
from bs4 import BeautifulSoup
from utils import convert_date

urllib3.disable_warnings()


class ArticleSpider:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def get_article_info(self, item):
        url = item['link']
        info_stats = self._get_article_stats(url)
        info_contents = self._get_article_contents(url)
        info_comments = self._get_article_comments(url)
        info = {
            "article_id": item['aid'],
            "type": 'video' if item['item_show_type'] == 5 else "article",
            "title": item['title'],
            "digest": item['digest'],
            "date": convert_date(item['update_time']),
            "url": item['link'],
        }
        info.update(info_stats)
        info.update(info_contents)
        info.update(info_comments)
        return info

    def _get_article_contents(self, article_url):
        info_content = {}
        try:
            html = requests.get(article_url, verify=False).text
        except Exception:
            print('Cannot get the article contents.')
        else:
            bs = BeautifulSoup(html, 'html.parser')
            js_content = bs.find(id='js_content')
            if js_content:
                p_list = js_content.find_all('p')
                content_list = list(map(lambda p: p.text, filter(lambda p: p.text != '', p_list)))
                info_content['content'] = ''.join(content_list)

                if js_content.find(attrs={'class': 'video_iframe rich_pages'}):
                    info_content['builtin_video'] = True
                else:
                    info_content['builtin_video'] = False
        return info_content

    def _get_article_stats(self, article_url):
        mid = article_url.split("&")[1].split("=")[1]
        idx = article_url.split("&")[2].split("=")[1]
        sn = article_url.split("&")[3].split("=")[1]
        _biz = article_url.split("&")[0].split("_biz=")[1]

        api = "http://mp.weixin.qq.com/mp/getappmsgext"
        # headers = {
        # "Cookie":
        # "rewardsn=;wxtokenkey=777;wxuin=683053783;devicetype=iPhoneiOS13.5.1;version=17000e28;lang=zh_CN",
        # "User-Agent":
        # "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 \
        # Safari/537.36 MicroMessenger/6.5.2.501 NetType/WIFI WindowsWechat QBCore/3.43.901.400 QQBrowser/9.0.2524.400"
        # }
        data = {"is_only_read": "1", "is_temp_url": "0", "appmsg_type": "9", 'reward_uin_count': '0'}

        params = {
            "__biz": _biz,
            "mid": mid,
            "sn": sn,
            "idx": idx,
            "key": self.kwargs['key'],
            "pass_ticket": self.kwargs['pass_ticket'],
            "appmsg_token": self.kwargs['appmsg_token'],
            "uin": self.kwargs['uin'],
            "wxtoken": "777",
        }
        info_stats = {}
        resp = requests.post(api, headers=self.kwargs['headers'], data=data, params=params).json()
        try:
            resp_stat = resp['appmsgstat']
            info_stats['read_num'] = resp_stat['read_num']
            info_stats['like_num'] = resp_stat['like_num']
            return info_stats
        except KeyError:
            print('The appmsg_token, key, or pass ticket is incorrect.')

    def _get_article_comments(self, article_url):
        info_comments = {}
        try:
            resp = requests.get(article_url, headers=self.kwargs['headers'], verify=False)
        except Exception:
            print('Cannot get comments.')
        else:
            html = resp.text
            str_comment = re.search(r'var comment_id = "(.*)" \|\| "(.*)" \* 1;', html)
            str_msg = re.search(r'var appmsgid = (.*?);', html)

            if str_comment and str_msg:
                comment_id = str_comment.group(1)
                app_msg_id = re.search(r"\d+", str_msg.group(1)).group(0)

                if app_msg_id and comment_id:
                    info_comments['comments'] = self.__crawl_comments(app_msg_id, comment_id)
        return info_comments

    def __crawl_comments(self, app_msg_id, comment_id):
        params = {
            'action': 'getcomment',
            'appmsgid': app_msg_id,
            'comment_id': comment_id,
            'offset': '0',
            'limit': '100',
            'uin': self.kwargs['uin'],
            'key': self.kwargs['key'],
            'pass_ticket': self.kwargs['pass_ticket'],
            'wxtoken': '777',
            '__biz': self.kwargs['fake_id'],
            'appmsg_token': self.kwargs['appmsg_token'],
            'x5': '0',
            'f': 'json',
            'scene': '0'
        }

        api = 'https://mp.weixin.qq.com/mp/appmsg_comment'

        try:
            resp = requests.get(api, headers=self.kwargs['headers'], params=params, verify=False).json()
        except Exception:
            pass
        else:
            comments = []
            ret, status = resp['base_resp']['ret'], resp['base_resp']['errmsg']
            if ret == 0 or status == 'ok':
                elected_comment = resp['elected_comment']
                for comment in elected_comment:
                    nick_name = comment.get('nick_name')
                    comment_time = convert_date(comment.get('create_time'))
                    content = comment.get('content')
                    content_id = comment.get('content_id')
                    like_num = comment.get('like_num')
                    comments.append({
                        'content_id': content_id,
                        'nickname': nick_name,
                        'comment_time': comment_time,
                        'content': content,
                        'like_num': like_num
                    })
            return comments
