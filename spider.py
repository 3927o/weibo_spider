import time

import requests
import re
from lxml import etree
from json.decoder import JSONDecodeError
from pymongo import MongoClient

from logfile import logger
from utils import get_redis_conn, get_proxy
from settings import MONGO_HOST, MONGO_PORT


class UserTweetSpider:
    def __init__(self, uid, start_page=1):
        self.uid = uid
        self.blog_list_url_format = "https://weibo.com/ajax/statuses/mymblog?uid={}&page={}"
        self.blog_detail_url_format = "https://weibo.com/ajax/statuses/show?id={}"
        self.headers = {
            "cookie": r'SINAGLOBAL=7897790998927.175.1621517097341; __gads=ID=341af79fd8aff5e5:T=1630505768:S=ALNI_MbC38scgB7G1UPz-iCiOllmtuvCnA; _ga=GA1.2.1921815252.1630505811; login_sid_t=c5b007a653cc16ac5e99c4c8be3613b3; cross_origin_proto=SSL; _s_tentry=-; Apache=8898375541886.855.1630505819004; ULV=1630505819009:2:1:1:8898375541886.855.1630505819004:1621517097345; XSRF-TOKEN=ldMYZ0bGVDGwD8evaBjbaOtD; WBtopGlobal_register_version=2021091101; SSOLoginState=1631293331; ALF=1662950419; WBPSESS=RYZ_qd4WKsNGIqKMW2iHoPpk6Aq3xKrXjBXrbnhq5IU_bgKT73clZ5nHpxZVFnARiAADEgQbuKCAerKw_gTApfbcZ4XqRwdJ6AqPzhtfmu14icFd6LI25zAqK6xNqm-P; SUBP=0033WrSXqPxfM725Ws9jqgMF55529P9D9WhqzMmrDmn_cJfLk2IqPHDz5JpX5K-hUgL.FoME1KefSo5ceKz2dJLoIp7LxKML1KBLBKnLxKqL1hnLBoMNeo.0SKq7So2E; SCF=AkjTF3Qclgqrmqy3qTwtGkPxdRarxJsruDKqly7EOyWCTKzTHD3_YK3ncVb0qXICURffZeScsPfWPUpkQg8zN7o.; SUB=_2A25MORo0DeRhGeFM4lEU9i7Kyj6IHXVvTwz8rDV8PUJbmtANLWfwkW9NQI-ho3A5m21HqAsRb3MJmUz__ggRgmh6',
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36"
        }
        self.count = dict()
        self.mongo_cli = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
        self.db = self.mongo_cli.get_database("weibo")
        self.collection = self.db.get_collection("Tweet")
        self.start_page = start_page
        self.empty_cnt = 0
        self.js_error = 0
        self.pre_is_js_error = False
        self.proxy = get_proxy()
        # self.proxy = {}
        logger.info(f"proxy is {self.proxy}")

    def request_for_info(self, url_format, *args):
        url = url_format.format(*args)
        resp = requests.get(url, headers=self.headers)
        if "application/json" not in resp.headers["content-type"]:
            self.handle_js_error(url)
            return {}

        try:
            resp = resp.json()
        except JSONDecodeError:
            self.handle_js_error(url)
            return {}

        # todo js error 过多时休息一会儿, ok
        # todo 连续爬取多个用户
        # todo 自动更新cookie
        self.pre_is_js_error = False
        return resp

    def crawl(self):
        page = self.start_page
        is_final_page = False
        while not is_final_page:
            try:
                is_final_page = self.crawl_one_page(page)
            except KeyError as e:
                logger.error(f"meet KeyError while crawl {self.uid}, page {page}", exc_info=e)
                is_final_page = False
            except Exception as e:
                logger.error(f"meet some unknown error while crawl {self.uid}, page {page}", exc_info=e)
                is_final_page = False
            page += 1
        logger.info(f"crawl {self.uid} success, blog cnt is {self.count[self.uid]}")

    def crawl_one_page(self, page: int) -> bool:
        logger.info(f"crawling user {self.uid}, page {page}")
        resp = self.request_for_info(self.blog_list_url_format, self.uid, page)
        if not resp:
            return False
        blogs = resp["data"]["list"]

        for blog in blogs:
            self.crawl_one_blog(blog["mblogid"])

        # judge if is final page
        if len(resp["data"]["list"]) == 0:
            self.empty_cnt += 1
        is_final_page = self.empty_cnt >= 10
        if is_final_page:
            logger.info(f"final page is {resp}")
        return is_final_page  # is final page

    def get_blog_data(self, blog_id: str):
        blog_info = self.request_for_info(self.blog_detail_url_format, blog_id)
        if not blog_info:
            return {}
        blog_data = self.parse_blog(blog_info)

        return blog_data

    def crawl_one_blog(self, blog_id: str):
        try:
            blog_data = self.get_blog_data(blog_id)
        except KeyError as e:
            logger.error(f"meet KeyError while parse blog {blog_id}", exc_info=e)
            return

        self.storage_data(blog_data)

    def parse_blog(self, blog_info: dict) -> dict:
        data = {
            "uid": self.uid,
            "id": blog_info["mblogid"],
            "id_num": blog_info["idstr"],
            "text": blog_info["text_raw"],
            "device": blog_info["source"],
            "date": blog_info["created_at"],
            "like_count": blog_info["attitudes_count"],
            "comment_count": blog_info["comments_count"],
            "repost_count": blog_info["reposts_count"],
            "position": self.get_location(etree.HTML(blog_info["text"])),
            "topics": [topic["topic_title"] for topic in blog_info.get("topic_struct", [])],
            "pics": [pic_info["original"]["url"] for pic_info in blog_info.get("pic_infos", {}).values()],
            "is_original": True,
            "video": blog_info["page_info"]["media_info"]["mp4_hd_url"] if blog_info.get("page_info", {}).get("object_type", '') == "video" else "",
            "at_info": re.findall("@(.*) ", blog_info["text_raw"])
        }
        if blog_info.get("retweeted_status"):
            data["is_original"] = False
            retweet_blog_id = blog_info["retweeted_status"]["mblogid"]
            data["retweeted_blog"] = self.get_blog_data(retweet_blog_id)
        return data

    def storage_data(self, blog_data):
        logger.info(f"inserting {blog_data}")
        self.collection.insert_one(blog_data)
        self.count[self.uid] = self.count.get(self.uid, 0) + 1

    @staticmethod
    def get_location(selector):
        """获取微博发布位置"""
        location_icon = 'timeline_card_small_location_default.png'
        span_list = selector.xpath('//span')
        location = ''
        for i, span in enumerate(span_list):
            if span.xpath('img/@src'):
                if location_icon in span.xpath('img/@src')[0]:
                    location = span_list[i + 1].xpath('string(.)')
                    break
        return location

    def handle_js_error(self, url):
        logger.error(f"get not json data while request for {url}")
        r = get_redis_conn()
        r.sadd("weibo:spider:url:failed", url)

        if self.pre_is_js_error:
            self.js_error += 1
        else:
            self.js_error = 1

        self.pre_is_js_error = True
        if self.js_error >= 10:
            logger.info("too many js error, prepare to sleep")
            time.sleep(600)
            self.js_error = 0


if __name__ == '__main__':
    # spider = UserTweetSpider("1937187173", 1)
    spider = UserTweetSpider("1937187173", 10)
    spider.crawl()
