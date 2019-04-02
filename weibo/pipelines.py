# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html
import pymysql
from collections import defaultdict


class WeiboPipeline(object):
    def process_item(self, item, spider):
        return item


class MysqlPipeline(object):
    def __init__(self, mysql_config):

        self.mysql_config = mysql_config
        self.item_list = []

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            mysql_config=crawler.settings.get('MYSQL_CONFIG')
        )

    def open_spider(self, spider):
        self.dbpool = pymysql.connect(**self.mysql_config)
        self.cursor = self.dbpool.cursor()

    def close_spider(self, spider):
        # 结束时item_list中可能还有item没有插入数据库
        if len(self.item_list) > 0:
            for x in self.item_list:
                try:
                    sql = "insert into weibo_user values %s;" % str(x)
                    self.cursor.execute(sql)
                    self.dbpool.commit()
                except Exception:
                    pass
            self.item_list.clear()
        self.dbpool.close()

    def process_item(self, item, spider):
        user = dict(item)
        if len(self.item_list) < 100:
            self.item_list.append((
                user['id'], user['name'], user['follow'], user['fans'], user['gender'], user['description'],
                user['verified'], user['verified_reason'], user['verified_type']))
        else:
            try:
                sql = "insert into weibo_user values %s;" % str(self.item_list)[1:-1]
                self.cursor.execute(sql)
                self.dbpool.commit()
                self.item_list.clear()
            # 异常处理，如果遇到重复插入，则重新对这一批次的每条数据进行插入
            # 对于重复的行直接忽略
            except Exception:
                for x in self.item_list:
                    try:
                        sql = "insert into weibo_user values %s;" % str(x)
                        self.cursor.execute(sql)
                        self.dbpool.commit()
                    except Exception as e:
                        print(e)
                self.item_list.clear()
        return item

# (1366, "Incorrect string value: '\\xF0\\x9F\\x97\\x9E u...' for column 'description' at row 1")
