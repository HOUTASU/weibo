# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/items.html

import scrapy
from scrapy import Field


class UserItem(scrapy.Item):
    table = 'user'
    id = Field()  # 用户id
    name = Field()  # 用户昵称
    gender = Field()  # 性别
    description = Field()  # 简介
    follow = Field()  # 关注数
    fans = Field()  # 粉丝数
    verified = Field()  # 是否认证
    verified_reason = Field()  # 认证原因，未认证则无此项
    verified_type = Field()  # 认证类型，未认证则无此项
