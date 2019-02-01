import logging
import socket
import time
import re
import threading
import datetime
from queue import Queue
from .color_printer import ColorPrinter
from .DanmuThread import *
import requests

logger = logging.getLogger('danmu.fm')
fetched_msg_q = Queue()
batch_insert_q = Queue()


class Danmu(object):

    def __init__(self,room_id):
        self.room_id = room_id

    def start(self):
        print("环境检查完毕,正在开启斗鱼客户端(请等待15s~30s)")
        # 判断主播是否开播
        resp = requests.get("http://open.douyucdn.cn/api/RoomApi/room/%s" % self.room_id)
        if not resp.json()['error'] == 0:
            print("连接服务器失败，请重试")
            return
        if resp.json()['data']['room_status'] == "2":
            print("主播未在直播")
            return  # 关播则退出

        # 更新roomid为数字id
        zhubo_name = resp.json()['data']['owner_name']

        print("开始抓取弹幕,房间号:%s 主播名称:%s" % (self.room_id,zhubo_name))
        manager = DouyuDanmuManager(self.room_id,zhubo_name)
        manager.start()


class DouyuDanmuManager(object):

    def __init__(self,room_id,zhubo_name):
        self.room_id = str(room_id)
        # self.douyu_service_ip = ('danmu.douyutv.com', 8602)
        self.douyu_service_ip = ('117.148.167.219', 8601)
        self.type_douyutoMe = 690
        self.type_metoDouyu = 689
        self.loginMsg_head = None
        self.len = 0
        self.head_len = 0
        self.danmu_type = set()
        self.danmy_type_count = len(self.danmu_type)
        self.zhubo_name = zhubo_name


    def start(self):
        #登录
        self.do_login()

    def do_login(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.keeplive = KeepliveThread("001", "keeplive", 1, self.socket)
        self.batch_insert_thread = BatchInsertThread("004", "batch_insert", 1, batch_insert_q)
        self.parse_thread = ParseMsgThread("003", "parse", 1, self.socket, fetched_msg_q, self.zhubo_name,
                                           batch_insert_q)
        self.receive_thread = ReceiveMsgThread("002", "recevie", 1, self.socket, fetched_msg_q)
        self.socket.connect(self.douyu_service_ip)
        print('==========创建与斗鱼TV的SOCKET连接==========')
        #构造请求字符串
        content = 'type@=loginreq/username@=visitor4858/password@=12345678901/roomid@=' + self.room_id + '/\x00'
        #发送登录请求
        self.send_loginMSG(content)
        #加入弹幕组
        content = 'type@=joingroup/rid@=' + self.room_id + '/gid@=-9999/\x00'
        self.join_group(content)
        #建立弹幕长链接，并启动心跳检测，每45秒进行心跳检测，维持长链接
        print('建立弹幕链接')
        #创建4个线程
        #keeplive心跳线程
        #接收弹幕线程
        #解析弹幕线程
        #持久化弹幕线程
        # 开启心跳检测
        while True:
            if(self.receive_thread.is_alive()):
                time.sleep(1)
                pass
            else:
                self.start_keeplive()
                self.start_recevie_msg()
                self.start_parse_msg()
                self.start_batch_insert()


    def start_batch_insert(self):
        self.batch_insert_thread = BatchInsertThread("004", "batch_insert", 1, batch_insert_q)
        self.batch_insert_thread.start()

    def start_parse_msg(self):
        self.parse_thread = ParseMsgThread("003", "parse", 1, self.socket, fetched_msg_q,self.zhubo_name,batch_insert_q)
        self.parse_thread.start()

    def start_recevie_msg(self):
        self.receive_thread = ReceiveMsgThread("002", "recevie", 1, self.socket, fetched_msg_q)
        self.receive_thread.start()

    def handler_connect(self):
        try:
            while True:
                #接收响应弹幕，并解析
                content = self.get_danmu()
                self.parse_recv_msg(content)
        except ConnectionResetError:
            #socket被斗鱼关闭，重新执行
            print("socket 被关闭 重新开启爬虫")
            self.start()
            pass



    def get_danmu(self):
        recv_msg = self.danmu_recv()
        if(recv_msg.strip()!=''):
            fetched_msg_q.put(recv_msg)
        return recv_msg

    def danmu_recv(self):
        buffer = b''
        while True:
            recv_data = self.socket.recv(1024)
            buffer += recv_data
            if recv_data.endswith(b'\x00'):
                break
        return self.parse_content(buffer)

    def parse_content(self, msg):
        content = msg[12:-1].decode('utf-8', 'ignore')
        return content

    def parse_recv_msg(self,content):
        if(content.strip() == ''):
            return
        msg_content = content.replace("@=", ":")
        try:
            msg_type = re.search('type:(.+?)\/', msg_content).group(1)
            #self.get_all_type(msg_type)
            if msg_type == "chatmsg":
                msg_type_zh = "弹幕消息"
                sender_id = re.search('\/uid:(.+?)\/', msg_content).group(1) if 'uid:' in msg_content else "unknown"
                nickname = re.search('\/nn:(.+?)\/', msg_content).group(1) if 'nn:' in msg_content else "unknown"
                content = re.search('\/txt:(.+?)\/', msg_content).group(1) if 'txt:' in msg_content else "unknown"
                level = re.search('\/level:(.+?)\/', msg_content).group(1) if 'level:' in msg_content else "unknown"
                client_type = re.search('\/ct:(.+?)\/', msg_content).group(1) if 'ct:' in msg_content else "unknown"  # ct 默认值 0 web
                if client_type == '1':
                    client_type_str = '苹果'
                elif client_type == '2':
                    client_type_str = '安卓'
                else:
                    client_type_str = '浏览器'
                time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ColorPrinter.green(
                    "|" + msg_type_zh + "| " + self.align_left_str(nickname, 20, " ") + self.align_left_str(
                        "<Lv:" + level + ">", 8, " ") + self.align_left_str("(" + sender_id + ")", 13,
                                                                            " ") + self.align_left_str(
                        "[" + client_type_str + "]", 10, " ") + "@ " + time + ": " + content + " ")

            elif msg_type == "uenter":
                pass
                # msg_type_zh = "入房消息"
                # user_id = re.search('\/uid:(.+?)\/', msg_content).group(1) if 'uid:' in msg_content else "unknown"
                # nickname = re.search('\/nn:(.+?)\/', msg_content).group(1) if 'nn:' in msg_content else "unknown"
                # strength = re.search('\/str:(.+?)\/', msg_content).group(1) if 'str:' in msg_content else "unknown"
                # level = re.search('\/level:(.+?)\/', msg_content).group(1) if 'level:' in msg_content else "unknown"
                # time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                # ColorPrinter.red(
                #     "|" + msg_type_zh + "| " + self.align_left_str(nickname, 20, " ") + self.align_left_str(
                #         "<Lv:" + level + ">", 8, " ") + self.align_left_str("(" + user_id + ")", 13,
                #                                                             " ") +  "@ " + time)
            elif msg_type == "dgb":
                # print(msg_content)
                msg_type_zh = "礼物赠送"
                # level = re.search('\/level:(\d+?)\/', msg_content).group(
                #     1) if 'level:' in msg_content else "unknown"
                # user_id = re.search('\/uid:(.+?)\/', msg_content).group(1) if 'uid:' in msg_content else "unknown"
                # nickname = re.search('\/nn:(.+?)\/', msg_content).group(1) if 'nn:' in msg_content else "unknown"
                # strength = re.search('\/str:(.+?)\/', msg_content).group(1) if 'str:' in msg_content else "unknown"
                # dw = re.search('\/dw:(.+?)\/', msg_content).group(1) if 'dw:' in msg_content else "unknown"
                # gs = re.search('\/gs:(.+?)\/', msg_content).group(1) if 'gs:' in msg_content else "unknown"
                # hits = re.search('\/hits:(.+?)\/', msg_content).group(1) if 'hits:' in msg_content else "unknown"
                # time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                # ColorPrinter.yellow(
                #     "|" + msg_type_zh + "| " + self.align_left_str(nickname, 20, " ") + self.align_left_str(
                #         "<Lv:" + level + ">", 8, " ") + self.align_left_str("(" + user_id + ")", 13,
                #                                                             " ") + self.align_left_str(
                #         "[" + dw + "]", 10, " ") + self.align_left_str("[" + gs + "]", 10,
                #                                                        " ") + self.align_left_str(
                #         "[" + strength + "]", 10, " ") + "@ " + time + ": " + hits + " hits ")
            elif msg_type == 'spbc':
                # print("spbc: "+msg_content)
                pass
        except Exception as e:
            print(e)
            logger.error("弹幕内容解析错误:"+msg_content)


    def get_all_type(self,msg_type):
        pass
        # self.danmu_type.add(msg_type)
        # if(self.danmy_type_count != len(self.danmu_type)):
        #     with open('type.txt','w') as f:
        #         for i in self.danmu_type:
        #             f.write(i+" ")
        #         self.danmy_type_count = len(self.danmu_type)

    def keep_live(self):
        while True:
            content = 'type@=keeplive/tick@=' + str(int(time.time())) + '/\x00'
            content = content.encode('utf-8')
            self.len = len(content) + 8
            self.head_len = self.len
            msg = self.len.to_bytes(4, byteorder='little') + self.head_len.to_bytes(4, byteorder='little') + self.type_douyutoMe.to_bytes(4, byteorder='little') + content
            self.socket.sendall(msg)
            print('心跳包发送成功')
            time.sleep(40)

    def start_keeplive(self):
        # self.keeplive = threading.Thread(target=self.keep_live).start()
        self.keeplive = KeepliveThread("001","keeplive",1,self.socket)
        self.keeplive.start()
        return self.keeplive

    def join_group(self, content):
        content = content.encode('utf-8')
        self.len = len(content) + 8
        self.head_len = self.len
        msg = self.len.to_bytes(4, byteorder='little') + self.head_len.to_bytes(4, byteorder='little') + self.type_metoDouyu.to_bytes(4, byteorder='little') + content
        try:
            print('加入弹幕组 : ', msg)
            a = self.socket.sendall(msg)
            if a is None:
                print('加入弹幕组成功')
            else:
                print('加入弹幕组失败')
        except socket.error:
            print(msg)
            exit(0)

    def send_loginMSG(self,content):
        #构造二进制请求串
        content = content.encode('utf-8')
        self.len = len(content) + 8
        self.head_len = self.len
        msg = self.len.to_bytes(4, byteorder='little') + self.head_len.to_bytes(4,byteorder='little') + self.type_metoDouyu.to_bytes(4, byteorder='little') + content
        print('登录请求参数{}',msg)
        try:
            a = self.socket.sendall(msg)
            if a is None:
                print('发送登录请求成功')
        except socket.error:
            print('发送登录请求失败 : ', msg)
            exit(0)
        try:
            data = self.socket.recv(1024)
        except socket.error:
            print('接收登录响应失败')
        print('recv data : ', data)
        q = re.search(br'type@=(\w+)/', data)
        print(q.group(1))
        if q.group(1) == b'loginres':
            print('登录成功')

    def align_left_str(self, raw_str, max_length, filled_chr):
        my_length = 0
        for i in range(0, len(raw_str)):
            if ord(raw_str[i]) > 127 or ord(raw_str[i]) <= 0:
                my_length += 1

            my_length += 1

        if (max_length - my_length) > 0:
            return raw_str + filled_chr * (max_length - my_length)
        else:
            return raw_str

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
        pattern = re.compile(r'type@=(.*)/rid@')
        data_type = pattern.findall(content)
        try:
            if data_type[0] == 'chatmsg':
                return True
            else:
                return False
        except Exception:
            return False
