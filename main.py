from src.api import WechatSpider

nickname = '华东理工大学'

ws = WechatSpider(nickname)
ws.crawl_latest_posts(10, count=10)