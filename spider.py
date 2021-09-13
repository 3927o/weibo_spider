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
    def __init__(self, users: dict):
        self.uid = None
        self.users = users
        self.blog_list_url_format = "https://weibo.com/ajax/statuses/mymblog?uid={}&page={}"
        self.blog_detail_url_format = "https://weibo.com/ajax/statuses/show?id={}"
        self.headers = {
            "cookie": r'SINAGLOBAL=7897790998927.175.1621517097341; __gads=ID=341af79fd8aff5e5:T=1630505768:S=ALNI_MbC38scgB7G1UPz-iCiOllmtuvCnA; _ga=GA1.2.1921815252.1630505811; login_sid_t=c5b007a653cc16ac5e99c4c8be3613b3; cross_origin_proto=SSL; _s_tentry=-; Apache=8898375541886.855.1630505819004; ULV=1630505819009:2:1:1:8898375541886.855.1630505819004:1621517097345; XSRF-TOKEN=ldMYZ0bGVDGwD8evaBjbaOtD; WBtopGlobal_register_version=2021091101; SSOLoginState=1631293331; SCF=AkjTF3Qclgqrmqy3qTwtGkPxdRarxJsruDKqly7EOyWCTKzTHD3_YK3ncVb0qXICURffZeScsPfWPUpkQg8zN7o.; ALF=1634046157; SUB=_2A25MOnOdDeRhGeFM4lEU9i7Kyj6IHXVvxR3VrDV8PUJbkNB-LXj-kW1NQI-ho1K1BIxYNMsy2TMNrUqmwEm7q1Cd; SUBP=0033WrSXqPxfM725Ws9jqgMF55529P9D9WhqzMmrDmn_cJfLk2IqPHDz5JpX5oz75NHD95QNeo.0SKq7So2EWs4DqcjMi--NiK.Xi-2Ri--ciKnRi-zNS0z4e0-cehqpentt',
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36"
        }
        self.count = dict()
        self.mongo_cli = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
        self.db = self.mongo_cli.get_database("weibo")
        self.collection = self.db.get_collection("Tweet")
        self.start_page = 1
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

        # todo 自动更新cookie
        self.pre_is_js_error = False
        return resp

    def crawl(self):
        self.empty_cnt = 0
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

    def start(self):
        for uid in self.users.keys():
            self.uid = uid
            self.start_page = self.users[uid]
            self.crawl()

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
    # spider = UserTweetSpider({"3229450293": 522, "2784361770": 1, "3687019147": 1, "5537781788": 1,
    #                           "2270636837": 1, "2782520515": 1, "2993099575": 1, "2726922721": 1, "3097688767": 1,
    #                           "2489610225": 1, "2620622835": 1, "2541592687": 1, "1662558237": 1, "5131766197": 1,
    #                           "1988438334": 1})
    spider = UserTweetSpider({"1751714412": 1, "1703371307": 1, "1698857957": 1, "1706406001": 1, "1644489953": 1,
                              "1899950161": 1, "1960601312": 1, "1962117985": 1, "1738004582": 1, "1734530730": 1,
                              "1898885525": 1, "1720962692": 1, "1700087532": 1, "1735221154": 1, "1653603955": 1,
                              "1735937570": 1, "1801817195": 1, "1844967414": 1, "1882632930": 1, "1975154821": 1,
                              "2011075080": 1, "1232121710": 1, "1915671961": 1, "1314608344": 1, "3203137375": 1,
                              "1960785875": 1, "1931775031": 1, "1904947977": 1, "1699258907": 1, "1700720163": 1})
    spider.start()
