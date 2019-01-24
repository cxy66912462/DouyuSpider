# -*- coding: utf-8 -*-
import scrapy
import json
from scrapy.http import Request
from DouyuSpider.items import DouyuItemLoader,DouyuCategoryItem,DouyuRoomItem
from DouyuSpider.pipelines import MysqlTwistedPipeline
from urllib import parse

class DouyuSpider(scrapy.Spider):
    name = 'douyu'
    allowed_domains = ['douyutv.com']
    start_urls = ['http://open.douyucdn.cn/api/RoomApi/game']
    room_list_url = 'http://open.douyucdn.cn/api/RoomApi/live/'
    room_detail_url = 'http://open.douyucdn.cn/api/RoomApi/room/'
    cate_offset = dict()

    def parse(self, response):
        data = json.loads(response.text, encoding='utf-8')
        if data['error'] == 0:
            cate_list = data['data']
            for cate_info in cate_list:
                item_loader = DouyuItemLoader(item=DouyuCategoryItem(), response=response)
                item_loader.add_value('cate_id', cate_info['cate_id'])
                item_loader.add_value('game_name', cate_info['game_name'])
                item_loader.add_value('short_name', cate_info['short_name'])
                item_loader.add_value('game_url', cate_info['game_url'])
                item_loader.add_value('game_src', cate_info['game_src'])
                item_loader.add_value('game_icon', cate_info['game_icon'])
                cate_item = item_loader.load_item()
                # 字典记录分类offset
                self.cate_offset[cate_info['cate_id']] = 0
               # yield cate_item
                cate_url = parse.urljoin(self.room_list_url, str(cate_info['cate_id']))
                yield Request(url=cate_url, meta={'cate_id':cate_info['cate_id']},callback=self.parse_room_list,dont_filter = True)
            pass
        else:
            print('获取所有游戏分类信息失败,原因:',data['data'])
            pass

    def parse_room_info(self,response):
        json_data = json.loads(response.text, encoding='utf-8')
        room_info = json_data['data']
        if json_data['error'] == 0 :
            item_loader = DouyuItemLoader(item=DouyuRoomItem(), response=response)
            item_loader.add_value('room_id', room_info['room_id'])
            item_loader.add_value('room_thumb', room_info['room_thumb'])
            item_loader.add_value('cate_id', room_info['cate_id'])
            item_loader.add_value('cate_name', room_info['cate_name'])
            item_loader.add_value('room_name', room_info['room_name'])
            item_loader.add_value('room_status', room_info['room_status'])
            item_loader.add_value('start_time', room_info['start_time'])
            item_loader.add_value('owner_name', room_info['owner_name'])
            item_loader.add_value('avatar', room_info['avatar'])
            item_loader.add_value('online', room_info['online'])
            item_loader.add_value('owner_weight', room_info['owner_weight'])
            item_loader.add_value('fans_num', room_info['fans_num'])
            room_item = item_loader.load_item()
            yield room_item
        else:
            print('获取房间信息失败', json_data['data'])


    def parse_room_list(self,response):
        json_data = json.loads(response.text,encoding='utf-8')
        room_info_list = json_data['data']
        cate_id = response.meta.get('cate_id')
        print(self.cate_offset[cate_id])
        if json_data['error'] == 0 and len(json_data['data'])>0:
            for room_info in room_info_list:
                # print(parse.urljoin(self.room_detail_url,room_info['room_id']))
                yield Request(url=parse.urljoin(self.room_detail_url,str(room_info['room_id'])),callback=self.parse_room_info,dont_filter=True)
            if len(json_data['data'])>=30:
                self.cate_offset[cate_id] = self.cate_offset[cate_id]+30
                offset = self.cate_offset[cate_id]
                cate_url = parse.urljoin(self.room_list_url, str(cate_id)) +'?offset='+str(offset)
                yield Request(url=cate_url, meta={'cate_id': cate_id}, callback=self.parse_room_list,
                              dont_filter=True)
        else:
            print('获取房间列表失败',json_data['data'])