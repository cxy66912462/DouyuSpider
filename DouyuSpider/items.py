# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy
from scrapy.loader import ItemLoader
from scrapy.loader.processors import Join, MapCompose, TakeFirst
import re

class DouyuspiderItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    pass

class DouyuItemLoader(ItemLoader):
    #自定义Loader设置默认list取第一个
    default_output_processor = TakeFirst()

class DouyuRoomItem(scrapy.Item):
    room_id = scrapy.Field()
    room_thumb= scrapy.Field()
    cate_id= scrapy.Field()
    cate_name= scrapy.Field()
    room_name= scrapy.Field()
    room_status= scrapy.Field()
    start_time= scrapy.Field()
    owner_name= scrapy.Field()
    avatar= scrapy.Field()
    online= scrapy.Field()
    hn= scrapy.Field()
    owner_weight= scrapy.Field()
    fans_num= scrapy.Field()

    def get_insert_sql(self):
        insert_sql = '''
            INSERT INTO douyu_room (room_id,room_thumb,cate_id,cate_name,room_name,room_status,start_time,
            owner_name,avatar,online,owner_weight,fans_num,create_time,weight_type,hn)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW(),%s,%s)
            ON DUPLICATE KEY UPDATE room_thumb=VALUES(room_thumb),cate_id=VALUES(cate_id)
            ,cate_name=VALUES(cate_name),room_name=VALUES(room_name),room_status=VALUES(room_status)
            ,start_time=VALUES(start_time),owner_name=VALUES(owner_name),avatar=VALUES(avatar)
            ,online=VALUES(online),owner_weight=VALUES(owner_weight),fans_num=VALUES(fans_num)
            ,weight_type=VALUES(weight_type),max_hn=VALUES(GREATEST(max_hn,hn))
        '''
        #(^[1-9]\d*\.\d*|0\.\d*[1-9]\d*$)|(^[1-9]\d*|0$)
        owner_weight = self["owner_weight"]
        try:
            owner_weight = re.search('(^[1-9]\d*\.\d*|0\.\d*[1-9]\d*$)',self["owner_weight"])
            if owner_weight:
                owner_weight = owner_weight.group(1)
            else:
                owner_weight = re.search('(^[0-9]\d*|0$)', self["owner_weight"]).group(1)
        except Exception as e:
            print(owner_weight)
            print(e)
            pass
        if 't' in self['owner_weight']:
            weight_type = 2
        else:
            weight_type = 1
        online = int(self['online'])
        fans_num = int(self['fans_num'])
        params = (
            self['room_id'], self["room_thumb"], self["cate_id"],
            self["cate_name"], self["room_name"], self["room_status"],
            self["start_time"], self["owner_name"], self["avatar"],
            online, owner_weight, fans_num,weight_type
        )
        return insert_sql, params


# 分类信息
class DouyuCategoryItem(scrapy.Item):
    cate_id = scrapy.Field()
    game_name = scrapy.Field()
    short_name = scrapy.Field()
    game_url = scrapy.Field()
    game_src = scrapy.Field()
    game_icon = scrapy.Field()

    def get_insert_sql(self):
        insert_sql = '''
            INSERT INTO douyu_cate (cate_id,game_name,short_name,game_url,game_src,game_icon,create_time )
            VALUES (%s,%s,%s,%s,%s,%s,NOW())
            ON DUPLICATE KEY UPDATE game_name=VALUES(game_name), short_name=VALUES(short_name),game_url=VALUES(game_url)
            , game_src=VALUES(game_src),game_icon = VALUES(game_icon)
        '''
        params = (
            self['cate_id'],self["game_name"], self["short_name"],
            self["game_url"],self["game_src"], self["game_icon"]
        )
        return insert_sql, params
