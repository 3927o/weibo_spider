import requests
import logging


topic_url_formats = [
    "https://weibo.com/ajax/search/all?containerid=100103type%3D1%26q%3D%23%E7%94%B7%E5%AD%90%E9%97%AF%E5%85%A5%E6%B8%B8%E6%B3%B3%E9%A6%86%E5%A5%B3%E6%9B%B4%E8%A1%A3%E5%AE%A4%E7%A7%B0%E4%B8%8D%E8%AF%86%E5%AD%97%23%26t%3D3&page={}&count=20",
    "https://weibo.com/ajax/search/all?containerid=100103type%3D1%26q%3D%23%E5%A6%82%E4%BD%95%E7%9C%8B%E5%BE%85%E6%80%80%E5%AD%95%E6%9C%9F%E9%97%B4%E7%94%B7%E6%96%B9%E5%87%BA%E8%BD%A8%23%26t%3D3&page=3&count=20",
    "https://weibo.com/ajax/search/all?containerid=100103type%3D1%26q%3D%23%E9%83%A8%E5%88%86%E7%94%B5%E7%AB%9E%E8%B5%9B%E4%BA%8B%E5%AE%A3%E5%B8%83%E9%99%90%E5%88%B6%E5%8F%82%E8%B5%9B%E9%80%89%E6%89%8B%E5%B9%B4%E9%BE%84%23%26t%3D3&page=3&count=20",
    "https://weibo.com/ajax/search/all?containerid=100103type%3D1%26q%3D%23%E5%9D%9A%E5%86%B3%E9%98%B2%E6%AD%A2%E6%9C%AA%E6%88%90%E5%B9%B4%E4%BA%BA%E6%B2%89%E8%BF%B7%E7%BD%91%E7%BB%9C%E6%B8%B8%E6%88%8F%23%26t%3D3&page=3&count=20"
    "https://weibo.com/ajax/search/all?containerid=100103type%3D1%26q%3D%23%E4%B8%BA%E4%BB%80%E4%B9%88%E6%84%9F%E8%A7%89%E6%9C%88%E8%96%AA%E8%BF%87%E4%B8%87%E5%BE%88%E6%99%AE%E9%81%8D%23%26t%3D3&page=3&count=20",
    "https://weibo.com/ajax/search/all?containerid=100103type%3D1%26q%3D%23%E9%95%BF%E6%9C%9F%E6%B2%89%E8%BF%B7%E7%BD%91%E6%B8%B8%E6%9C%89%E4%BB%80%E4%B9%88%E5%8D%B1%E5%AE%B3%23%26t%3D3&page=3&count=20",
    "https://weibo.com/ajax/search/all?containerid=100103type%3D1%26q%3D%23%E8%85%BE%E8%AE%AF%E8%A7%86%E9%A2%91%E4%BC%98%E5%8C%96%E8%B6%85%E5%89%8D%E7%82%B9%E6%92%AD%23%26t%3D3&page=3&count=20"
    ]
blog_url_first_format = "https://weibo.com/ajax/statuses/buildComments?is_reload=1&id={}&is_show_bulletin=2&is_mix=0&count=20&uid={}"
blog_url_next_format = "https://weibo.com/ajax/statuses/buildComments?flow=0&is_reload=1&id={}&is_show_bulletin=2&is_mix=0&max_id={}&count=20&uid={}"
headers = {
    "cookie": r'SINAGLOBAL=7897790998927.175.1621517097341; __gads=ID=341af79fd8aff5e5:T=1630505768:S=ALNI_MbC38scgB7G1UPz-iCiOllmtuvCnA; _ga=GA1.2.1921815252.1630505811; login_sid_t=c5b007a653cc16ac5e99c4c8be3613b3; cross_origin_proto=SSL; _s_tentry=-; Apache=8898375541886.855.1630505819004; ULV=1630505819009:2:1:1:8898375541886.855.1630505819004:1621517097345; SSOLoginState=1630505903; XSRF-TOKEN=ldMYZ0bGVDGwD8evaBjbaOtD; SUBP=0033WrSXqPxfM725Ws9jqgMF55529P9D9WhqzMmrDmn_cJfLk2IqPHDz5JpX5KMhUgL.FoME1KefSo5ceKz2dJLoIp7LxKML1KBLBKnLxKqL1hnLBoMNeo.0SKq7So2E; ALF=1662191289; SCF=AkjTF3Qclgqrmqy3qTwtGkPxdRarxJsruDKqly7EOyWCSoD6B706t4HJyrvuKbTCZGNr2lrLQ48LEIukYjCuJCc.; SUB=_2A25MNaNqDeRhGeFM4lEU9i7Kyj6IHXVvQpOirDV8PUNbmtAKLUH9kW9NQI-ho4TrCzpHQMFKYUcUfvBjUvuA49b1; WBPSESS=RYZ_qd4WKsNGIqKMW2iHoPpk6Aq3xKrXjBXrbnhq5IWFJumPm07Yu6ybSSz-9KRHS4QFX18kP4ll6lyH6RH6r_ms-_ywc7NmoLvMS1EPDvO-KKmF5_glVcCOmGDaxzrB'
}

f = open("text.txt", "w", encoding="utf-8")
logging.basicConfig()


def store_text(text):
    f.write(text+"\n")


def crawl_one_blog(idstr, uid):
    first_page_resp = requests.get(blog_url_first_format.format(idstr, uid), headers=headers)
    first_page = first_page_resp.json()
    first_page_resp.close()
    del first_page_resp
    data = first_page["data"]
    for i in data:
        store_text(i["text_raw"])
        comments = i["comments"]
        for comment in comments:
            store_text(comment["text_raw"])

    max_id = first_page["max_id"]
    while int(max_id) != 0:
        print(f"max id is {max_id}")
        next_page_resp = requests.get(blog_url_next_format.format(idstr, max_id, uid), headers=headers)
        next_page = next_page_resp.json()
        next_page_resp.close()
        del next_page_resp
        data = next_page["data"]
        for i in data:
            store_text(i["text_raw"])
            comments = i["comments"]
            for comment in comments:
                store_text(comment["text_raw"])
        max_id = next_page["max_id"]


for topic_url_format in topic_url_formats:
    print(f"crawling {topic_url_format}")
    topic_page = 1
    while True:
        print(f"crawling page {topic_page}")
        try:
            resp_data = requests.get(topic_url_format.format(topic_page), headers=headers)
            resp = resp_data.json()
            resp_data.close()
            del resp_data
            cards = resp["data"]["cards"]
        except Exception as e:
            print(e, e.args)
            logging.info("some error occurred:", exc_info=e)
            continue

        for card in cards:
            if card["card_type"] != 9:
                continue

            idstr = card["mblog"]["idstr"]
            mblogid = card["mblog"]["mblogid"]
            uid = card["mblog"]["user"]["idstr"]

            try:
                print(f"crawling blog {mblogid}, {uid}")
                crawl_one_blog(idstr, uid)
            except Exception as e:
                print(e, e.args)
                logging.info("some error occurred:", exc_info=e)

        if len(cards) < 20:
            break
        topic_page += 1
