from src.api import WechatSpider

nickname = '华东理工大学'

ws = WechatSpider(nickname)
ws.crawl_latest_posts(num=12, begin=0, count=5)
