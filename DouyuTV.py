# encoding: utf-8
#@author: chaoxingyu
#@file: DouyuTV.py
#@time: 2017/9/1 14:08

import multiprocessing
import socket
import time
import re
import requests
import json
from bs4 import BeautifulSoup
from collections import deque
from threading import Thread
from MySqlUtil import MySqlConnect

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
host = socket.gethostbyname("openbarrage.douyutv.com")
port = 12601
client.connect((host, port))

#弹幕放置容器
d=deque()
#type 类型
type_set = set()

'''
type类型
chatmsg 弹幕
onlinegift 在线领取鱼丸暴击
dgb 赠送礼物
uenter 用户进入房间通知
bc_buy_deserve 赠送酬勤
\033[显示方式;前景色;背景色m
显示方式:0（默认值）、1（高亮）、22（非粗体）、4（下划线）、24（非下划线）、 5（闪烁）、25（非闪烁）、7（反显）、27（非反显）
前景色:30（黑色）、31（红色）、32（绿色）、 33（黄色）、34（蓝色）、35（洋 红）、36（青色）、37（白色）
背景色:40（黑色）、41（红色）、42（绿色）、 43（黄色）、44（蓝色）、45（洋 红）、46（青色）、47（白色）
'''

def sendmsg(msgstr):
    msg = msgstr.encode('utf-8')
    data_length = len(msg) + 8
    msgHead = int.to_bytes(data_length, 4, 'little') + int.to_bytes(data_length, 4, 'little') + int.to_bytes(
    689, 4, 'little')
    client.send(msgHead)
    client.sendall(msg)

def log(str):
    # str = str.encode()
    now_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
    log = now_time + '\t\t' + str
    with open('log.txt', 'a', encoding='utf-8')as f:
        f.writelines(log + '\n')
    print(log)

def start(room_id):
    log("连接弹幕服务器..." + host + ':' + str(port))
    log("连接成功,发送登录请求...")
    msg = 'type@=loginreq/username@=rieuse/password@=douyu/roomid@=' + str(room_id) + '/\x00'
    sendmsg(msg)
    data = client.recv(1024)
    log('Received from login\t\t' + repr(data))
    a = re.search(b'type@=(\w*)', data)
    if a.group(1) != b'loginres':
        log("登录失败,程序退出...")
        exit(0)
    log("登录成功")
    msg = 'type@=joingroup/rid@=' + str(room_id) + '/gid@=-9999/\x00'
    sendmsg(msg)
    log("进入弹幕服务器...")
    Thread(target=keeplive,args=()).start()
    log("心跳包机制启动...")
    print('-----------------欢迎来到{}的直播间-----------------'.format(get_name(room_id)))
    while True:
        response_info = client.recv(1024)
        try:
            parse_data(response_info)
            pass
        except:
            print('\033[1;31m[错误] 啊哦,出现了未知错误...\033[0m')
            continue


def keeplive():
    while True:
        log('发送心跳包')
        msg = 'type@=keeplive/tick@=' + str(int(time.time())) + '/\x00'
        sendmsg(msg)
        time.sleep(10)

# 根据房间号,获取主播名称
def get_name(room_id):
    r = requests.get("http://www.douyu.com/" + room_id)
    soup = BeautifulSoup(r.text, 'lxml')
    return soup.find('a', {'class', 'zb-name'}).string

def insert_danmu():
    connect = MySqlConnect()
    connect.connect()
    while True:
        if len(d) > 0:
            data = d.popleft()
            if data['type'] == 'chatmsg':
                sql = '''
                        INSERT INTO douyu_danmu(danmu_type,danmu_type_name,room_id,sender_id,sender_name
                        ,danmu_content,danmu_id,sender_level,create_time)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,now())
                    '''
            elif data['type'] == 'dgb':
                sql = '''
                        INSERT INTO douyu_danmu(danmu_type,danmu_type_name,room_id,gift_id,gift_style,sender_id
                        ,sender_name,sender_level,create_time)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,now())
                    '''
            elif data['type'] == 'uenter':
                sql = '''
                        INSERT INTO douyu_danmu(danmu_type,danmu_type_name,room_id,sender_id,sender_name
                        ,sender_level,create_time)
                        VALUES (%s,%s,%s,%s,%s,%s,now())
                    '''
            elif data['type'] == 'spbc':
                print(data['params'])
                sql = '''
                        INSERT INTO douyu_danmu(danmu_type,danmu_type_name,room_id,zhubo_name,sender_name
                        ,gift_count,redirect_room_id,gift_name,gift_id,guangbo_style
                        ,guangbo_style_name,create_time)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now())
                    '''
            elif data['type'] == 'ssd':
                sql = '''
                        INSERT INTO douyu_danmu(danmu_type,danmu_type_name,room_id,danmu_id,redirect_room_id
                        ,danmu_content,create_time)
                        VALUES (%s,%s,%s,%s,%s,%s,now())
                    '''
            else:
                continue
            connect.execute_insert(sql, data['params'])

def parse_data(response_info):
    try:
        content_list = re.findall(b'(type@=.*?)\x00', response_info)
        for content in content_list:
            content = json.loads('{"'+content.replace(b'@=', b'":"').replace(b'/', b'","').decode('utf8', 'ignore')[:-2]+ '}')
            if content['type'] == 'chatmsg':
                try:
                    type = content['type']
                    rid = content['rid']
                    uid = content['uid']
                    nickname=content['nn']
                    txt = content['txt']
                    cid = content['cid']
                    level = content['level']
                    d.append({'type':type,'params':[type,'弹幕',rid,uid,nickname,txt,cid,level]})
                    print(
                    '\033[1;34m[弹幕]\033[0m \033[1;32m[LV %s]\033[0m \033[1;33m%s:\033[0m \033[1;36m%s\033[0m' % (
                        content['level'], content['nn'], content['txt']))
                except Exception as e:
                    print('\033[1;31m[错误] 啊哦,弹幕信息解析错误\033[0m', e)
            elif content['type'] == 'dgb':
                try:
                    type = content['type']
                    rid = content['rid']
                    gfid = content['gfid']
                    gift_style = content['gs']
                    uid = content['uid']
                    nickname = content['nn']
                    level = content['level']
                    dw = content['dw']
                    try:
                        hits = content['hits']
                        d.append({'type': type, 'params': [type, '礼物',rid,gfid,gift_style,uid, nickname,level]})
                        print('\033[1;36m[礼物]\033[0m \033[1m用户\033[0m \033[1;32m[LV %s]\033[0m \033[1;33m%s\033[0m \033[1m送给主播1个赞:%s,\033[0m \033[1;31m%s连击\033[0m' % (
                                level, nickname,gfid, hits))
                    except Exception as e:
                        print(
                            '\033[1;36m[礼物]\033[0m \033[1m用户\033[0m \033[1;32m[LV %s]\033[0m \033[1;33m%s\033[0m \033[1m送给主播1个赞:%s \033[0m ' % (
                                level, nickname,gfid))
                except Exception as e:
                    print('\033[1;31m[错误] 啊哦,礼物弹幕信息解析错误\033[0m',e)
                pass
            elif content['type'] == 'uenter':
                try:
                    #{'type': 'uenter', 'rid': '321358', 'uid': '11557045', 'nn': '颜值最高的背包客丶', 'level': '34', 'ic': 'avanew@Sface@S201706@S13@S20@S722f99dc1de0ebd8a4f608a8142312ed', 'nl': '1', 'rni': '0', 'el': '', 'sahf': '0', 'wgei': '0'}
                    type = content['type']
                    rid = content['rid']
                    uid = content['uid']
                    nickname = content['nn']
                    level = content['level']
                    d.append({'type': type, 'params': [type, '用户提示',rid,uid, nickname, level]})
                    print(
                        '\033[1;36m[信息]\033[0m \033[1m用户\033[0m \033[1;32m[LV %s]\033[0m \033[1;33m%s\033[0m \033[1m进入房间\033[0m' % (
                            level, nickname))
                except Exception as e:
                    print('\033[1;31m[错误] 啊哦,用户进入房间弹幕信息解析错误\033[0m', e)
            elif content['type'] == 'spbc':
                try:
                    type = content['type']
                    rid = content['rid']
                    receive_gift_name = content['dn']
                    send_gift_name = content['sn']
                    gift_number = content['gc']
                    gift_room_id = content['drid']
                    gift_name = content['gn']
                    gs = content['gs']
                    gfid = content['gfid']
                    es = content['es']
                    if es == 1:
                        d.append({'type': type, 'params': [type, '广播礼物', rid, receive_gift_name, send_gift_name,
                                                           gift_number, gift_room_id, gift_name, gfid, es, '火箭']})
                    else:
                        d.append({'type': type, 'params': [type, '广播礼物',rid, receive_gift_name, send_gift_name, gift_number,gift_room_id,gift_name,gfid,es,'飞机']})
                    print(
                        '\033[1;36m[广播礼物]\033[0m \033[1;32m土豪\033[0m %s \033[1m送给主播\033[0m \033[1;33m%s\033[0m \033[1m%s个\033[0m\033[1;31m%s\033[0m 房间号:\033[1;35m%s \033[0m'  % (
                            send_gift_name, receive_gift_name, gift_number, gift_name,gift_room_id))
                except Exception as e:
                    print('\033[1;31m[错误] 啊哦,礼物广播提示弹幕信息解析错误\033[0m', e)
            elif content['type'] == 'ssd':
                try:
                    type = content['type']
                    room_id = content['rid']
                    super_danmu_id = content['sdid']
                    transport_room_id = content['trid']
                    super_danmu_content = content['content']
                    d.append({'type': type, 'params': [type,'超级弹幕',room_id,super_danmu_id,transport_room_id,super_danmu_content]})
                    print(
                        '\033[1;34m[超级弹幕]\033[0m \033[1;32m[LV %s]\033[0m \033[1;33m%s:\033[0m \033[1;35m%s\033[0m' % (
                            super_danmu_id, transport_room_id, super_danmu_content))
                except Exception as e:
                    print('\033[1;31m[错误] 啊哦,超级弹幕信息解析错误\033[0m', e)
                    pass
            elif content['type'] == 'bc_buy_deserve':
                type = content['type']
                room_id = content['rid']
                level = content['level']
                number = content['cnt']
                chouqin_level = content['lev']
                user_info = content['sui']
                try:
                    hits=content['hits']
                    # d.append({'type': type, 'params': [type,'酬勤',room_id,level,number,chouqin_level,user_info]})
                    print(
                        '\033[1;36m[酬勤]\033[0m \033[1m用户\033[0m \033[1;32m[LV %s]\033[0m \033[1;33m%s\033[0m \033[1m送给主播%s个\033[0m\033[1;31m%s酬勤 ,\033[0m \033[1;31m%s连击\033[0m' % (
                            level, nickname, number,chouqin_level,hits))
                except Exception as  e:
                    print(
                        '\033[1;36m[酬勤]\033[0m \033[1m用户\033[0m \033[1;32m[LV %s]\033[0m \033[1;33m%s\033[0m \033[1m送给主播%s个\033[0m\033[1;31m%s酬勤 \033[0m' % (
                            level, nickname, number,chouqin_level))
            elif content['type'] == 'ggbb':
                try:
                    type = content['type']
                    room_id = content['rid']
                    number = content['sl']
                    producer_id = content['sid']
                    producer_name = content['snk']
                    receiver_id = content['did']
                    receiver_name = content['dnk']
                    gift_type = content['rpt']
                    # d.append({'type': type, 'params': [type,'礼包',room_id, number, producer_id,producer_name,receiver_id,receiver_name]})
                    print('\033[1;36m[礼包]\033[0m \033[1m用户%s\033[0m抢到了来自\033[1;33m%s\033[0m的礼包,获取了\033[1;0m%s\033[0m个\033[1;34m%s \033[0m' % (
                        receiver_name,receiver_name,number,gift_type))
                except Exception as e:
                    print('\033[1;31m[错误] 啊哦,礼包信息解析错误\033[0m', e)
                    pass
            elif content['type'] == 'onlinegift':
                try:
                    type = content['type']
                    room_id = content['rid']
                    user_id = content['uid']
                    number = content['sil']
                    yuwan_level = content['if']
                    client_type = content['ct']
                    nickname = content['nn']
                    # d.append({'type': type, 'params': [type,room_id,user_id,number,yuwan_level,client_type,nickname]})
                    print('\033[1;31[暴击] \033[0m 用户\033[1;36m%s \033[0m获取了\033[1;33m%s \033[0m个鱼丸' %
                          (nickname,number))
                    pass
                except Exception as e:
                    print('\033[1;31m[错误] 啊哦,暴击信息解析错误\033[0m', e)

    except Exception as e:
        print('\033[1;31m[错误] 啊哦,出现了未知错误...\033[0m',e)


if __name__ == '__main__':
    room_id = input('请输入房间ID： ')
    Thread(target=start, args=(room_id,)).start()
    Thread(target=insert_danmu, args=()).start()
