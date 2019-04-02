# -*- coding: utf-8 -*-
import scrapy
import re
import json
from weibo.items import UserItem
from scrapy_redis.spiders import RedisSpider
from weibo.kit.db import get_redis_client
from urllib.parse import parse_qs


class UserSpider(RedisSpider):
    name = 'user'
    allowed_domains = ['weibo.com']
    start_urls = ['http://weibo.com/']
    redis_key = 'start_url:weibo_id'
    user_index = 'https://m.weibo.cn/api/container/getIndex?containerid=100505{}'
    fans_url = 'https://m.weibo.cn/api/container/getIndex?containerid=231051_-_fans_-_{}&since_id={}'
    followers = 'https://m.weibo.cn/api/container/getIndex?containerid=231051_-_followers_-_{}&page={}'
    re_sid = re.compile(r'since_id=(\d+)')
    re_page = re.compile(r'page=(\d+)')
    redis_connect = get_redis_client()

    def make_requests_from_url(self, user_id):
        """
        从redis中获取初始用户id,并构造初始链接
        """
        url = self.user_index.format(user_id)
        return scrapy.Request(url=url, callback=self.parse_user_info, dont_filter=True)

    def parse_user_info(self, response):
        info = json.loads(response.text)['data']['userInfo']
        user_id = info['id']
        item = UserItem()
        item['id'] = user_id
        item['name'] = info['screen_name']
        item['follow'] = info['follow_count']
        item['fans'] = info['followers_count']
        item['gender'] = info['gender']
        item['description'] = info['description']
        item['verified'] = info['verified']
        # FIXME:  json中的true和python中的True是否是同一对象？
        if info['verified'] is True:
            item['verified_reason'] = info['verified_reason']
            item['verified_type'] = info['verified_type']

        self.add_crawled(user_id)  # 将该用户加入redis已爬取队列
        yield item

        # 获取粉丝
        fans_url = self.fans_url.format(user_id, 1)
        meta = {
            'user_id': user_id,
            'follow': info['follow_count'],
            'fans': info['followers_count']
        }
        yield scrapy.Request(url=fans_url, meta=meta, callback=self.parse_fans, dont_filter=True)
        # 获取关注者
        followers_urls = self.followers.format(user_id, 1)
        yield scrapy.Request(url=followers_urls, meta=meta, callback=self.parse_followers,
                             dont_filter=True)

    def parse_fans(self, response):
        meta = response.meta
        info = json.loads(response.text)['data']
        item = UserItem()
        cards = info['cards']
        if len(cards) == 0:  # 判断card是否为空，若为空，则表示当前用户所有粉丝已获取
            return
        for fan in cards[-1]['card_group']:  # cards[-1]表示该用户的全部粉丝
            user_id = fan['user']['id']
            if self.is_crawled(user_id):  # 判断该ID是否已爬取
                continue
            verified = fan['user']['verified']
            if verified is True:
                # 根据verified判断用户是否已认证，若已认证，加入起始队列。若未认证，将该id加入redis已爬取队列。
                # card中有两个描述字段，第一个如果认证则是认证原因，如果没有认证则是个人简介，都没有则为空。第二个是粉丝数
                # 所有user字段中的description都为空，所以对于认证的用户需要单独获取简介。
                self.redis_connect.lpush('start_url:weibo_id', user_id)
            else:
                # 若未认证也未爬取，直接获取用户信息，将id加入已爬取队列
                item['id'] = user_id
                item['name'] = fan['user']['screen_name']
                item['follow'] = fan['user']['follow_count']
                item['fans'] = fan['user']['followers_count']
                item['gender'] = ''
                item['description'] = fan['desc1']
                item['verified'] = False
                item['verified_reason'] = ''
                item['verified_type'] = -1

                self.add_crawled(user_id)  # 将该用户加入redis已爬取队列
                yield item

        sid = int(self.re_sid.search(response.url).group(1))
        if sid < 20 and sid < meta['fans'] / 20:  # 最多只能显示250页, 每页只显示20个粉丝
            sid += 1
            url = self.fans_url.format(response.meta['user_id'], sid)
            yield scrapy.Request(url=url, meta=meta, callback=self.parse_fans, dont_filter=True)

    def parse_followers(self, response):
        meta = response.meta
        info = json.loads(response.text)['data']
        item = UserItem()
        cards = info['cards']
        if len(cards) == 0:  # 判断card是否为空，若为空，则表示当前用户所有关注已获取
            return
        for follow in cards[-1]['card_group']:  # cards[-1]表示该用户的全部关注
            user_id = follow['user']['id']
            if self.is_crawled(user_id):  # 判断该ID是否已爬取
                continue
            verified = follow['user']['verified']
            if verified is True:
                # 根据verified判断用户是否已认证，若已认证，加入起始队列。若未认证，将该id加入redis已爬取队列。
                # card中有两个描述字段，第一个如果认证则是认证原因，如果没有认证则是个人简介，都没有则为空。第二个是粉丝数
                # 所有user字段中的description都为空，所以对于认证的用户需要单独获取简介。
                self.redis_connect.lpush('start_url:weibo_id', user_id)
            else:
                # 若未认证也未爬取，直接获取用户信息，将id加入已爬取队列
                item['id'] = user_id
                item['name'] = follow['user']['screen_name']
                item['follow'] = follow['user']['follow_count']
                item['fans'] = follow['user']['followers_count']
                item['gender'] = ''
                item['description'] = follow['desc1']
                item['verified'] = False
                item['verified_reason'] = ''
                item['verified_type'] = -1

                self.add_crawled(user_id)  # 将该用户加入redis已爬取队列
                yield item

        page = int(self.re_page.search(response.url).group(1))
        if page < 20 and page < meta['follow'] / 20:  # 最多只能显示250页, 每页只显示20个关注
            page += 1
            url = self.followers.format(response.meta['user_id'], page)
            yield scrapy.Request(url=url, meta=meta, callback=self.parse_followers, dont_filter=True)

    def is_crawled(self, user_id):
        """
        查询redis已爬取集合，判断是否重复
        @:param user_id: 需要查重的id
        :return: 重复返回True
        """
        return self.redis_connect.sismember('weibo:dupe', user_id)

    def add_crawled(self, user_id):
        """
        将该id加入到redis已爬取队列
        :param user_id:
        :return:  插入结果
        """
        return self.redis_connect.sadd('weibo:dupe', user_id)
