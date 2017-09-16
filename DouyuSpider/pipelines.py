# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html
import MySQLdb
import MySQLdb.cursors
from twisted.enterprise import adbapi

class DouyuspiderPipeline(object):
    def process_item(self, item, spider):
        return item


class MysqlTwistedPipeline(object):

    def __init__(self,dbpool):
        self.dbpool = dbpool

    @classmethod
    def from_settings(cls,settings):
        dbparams = dict(
            host = settings['MYSQL_HOST'],
            database=settings['MYSQL_DBNAME'],
            user=settings['MYSQL_USER'],
            password=settings['MYSQL_PASSWORD'],
            charset = 'utf8',
            cursorclass = MySQLdb.cursors.DictCursor,
            use_unicode = True
        )
        dbpool = adbapi.ConnectionPool('MySQLdb',**dbparams)
        return cls(dbpool)

    # 使用twisted将mysql插入变成异步执行
    def process_item(self, item, spider):
        # 第一个参数方法,将这个方法变成异步执行
        query=self.dbpool.runInteraction(self.do_insert,item)
        query.addErrback(self.handle_error, item, spider)  # 处理异常
        return item

    # 执行具体插入操作
    def do_insert(self,cursor,item):
        #根据不同的item,构建不同的sql语句
        #技巧:将sql语句放到item的方法去构建
        insert_sql,params = item.get_insert_sql()
        # print(insert_sql)
        # print(params)
        cursor.execute(insert_sql, params)

    def handle_error(self,failure,item,spider):
        #处理异步插入异常
        print('异步插入异常:',failure)
        exit(0)