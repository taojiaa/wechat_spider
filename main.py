from src.api import WechatSpider

nickname = '腾讯创业'

ws = WechatSpider(nickname)
ws.crawl_latest_posts(begin=6, end=11, count=3)

