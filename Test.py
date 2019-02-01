from __future__ import unicode_literals
import multiprocessing
import socket
import time
import re
import requests
from bs4 import BeautifulSoup
import json
import threading

class Test:
    def prt(self):
        print(self)
        print(self.__class__)


class danmaku(object):
    def __init__(self):
        self.douyu_service_ip = ('117.148.167.219', 8601)
        # self.douyu_service_ip = ('117.148.167.219', 8601)
        self.type_douyutoMe = 690
        self.type_metoDouyu = 689
        self.loginMsg_head = None
        self.len = 0
        self.head_len = 0
        self.roomid = '528353'  #xdd

    def login(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(self.douyu_service_ip)
        print('Socket Connected to douyu_Danmaku')
        content = 'type@=loginreq/username@=visitor4858/password@=12345678901/roomid@=' + self.roomid + '/\x00'
        self.send_loginMSG(content)
        try:
            data = self.sock.recv(1024)
        except socket.error:
            print('login recv error')
        print('recv data : ', data)
        q = re.search(br'type@=(\w+)/', data)
        print(q.group(1))
        if q.group(1) == b'loginres':
            print('登录成功')
        content = 'type@=joingroup/rid@=' + self.roomid + '/gid@=-9999/\x00'
        self.join_group(content)
        print('建立弹幕链接')
        while True:
            # content = str(self.sock.recv(1024))
            content = self.sock.recv(1024)
            print(content)
            content = content.decode('utf-8', 'ignore')
            print(content)
            # print(type(content))
            if self.judge_chatmsg(content):
                nickname = self.nick_name(content)
                chatmsg = self.chat_msg(content)
                print(content)
                print('%s : %s' % (nickname, chatmsg))
            else:
                pass
        threading.Thread(target=danmaku.keep_live, args=(self,)).start()
        print('心跳机制启动')

    def nick_name(self,content):
        '''
        弹幕消息：
        type@=chatmsg/rid@=301712/gid@=-9999/uid@=123456/nn@=test /txt@=666/level@=1/
        判断type，弹幕消息为chatmsg，txt为弹幕内容，nn为用户昵称
        '''
        pattern = re.compile(r'nn@=(.*)/txt@')
        nickname = pattern.findall(content)[0]
        return nickname

    def chat_msg(self,content):
        '''
        弹幕消息：
        type@=chatmsg/rid@=301712/gid@=-9999/uid@=123456/nn@=test /txt@=666/level@=1/
        判断type，弹幕消息为chatmsg，txt为弹幕内容，nn为用户昵称
        '''
        pattern = re.compile(r'txt@=(.*)/cid@')
        chatmsg = pattern.findall(content)[0]
        return chatmsg

    def judge_chatmsg(self,content):
        '''
        判断是否为弹幕消息
        '''
        if(content.strip()==''):
            return False
        pattern = re.compile(r'type@=(.*)/rid@')
        data_type = pattern.findall(content)
        try:
            if data_type[0] == 'chatmsg':
                return True
            else:
                return False
        except Exception:
            return False

    def send_loginMSG(self, content):
        content = content.encode('utf-8')
        self.len = len(content) + 8
        self.head_len = self.len
        msg = self.len.to_bytes(4, byteorder='little') + self.head_len.to_bytes(4, byteorder='little') + self.type_metoDouyu.to_bytes(4, byteorder='little') + content
        print('send login msg : ', msg)
        try:
            a = self.sock.sendall(msg)
            if a is None:
                print('send login msg success')
        except socket.error:
            print('field sen login msg : ', msg)
            print('send fild')
            exit(0)

    def join_group(self, content):
        content = content.encode('utf-8')
        self.len = len(content) + 8
        self.head_len = self.len
        msg = self.len.to_bytes(4, byteorder='little') + self.head_len.to_bytes(4, byteorder='little') + self.type_metoDouyu.to_bytes(4, byteorder='little') + content
        try:
            print('join group msg : ', msg)
            self.sock.sendall(msg)
            print('send join group msg success')
        except socket.error:
            print(msg)
            print('join fild')
            exit(0)

    def keep_live(self):
        while True:
            content = 'type@=keeplive/tick@=' + str(int(time.time())) + '/\x00'
            content = content.encode('utf-8')
            self.len = len(content) + 8
            self.head_len = self.len
            msg = self.len.to_bytes(4, byteorder='little') + self.head_len.to_bytes(4, byteorder='little') + self.type_douyutoMe.to_bytes(4, byteorder='little') + content
            self.sock.sendall(msg)
            print('心跳包发送成功')
            time.sleep(40)
