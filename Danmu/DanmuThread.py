import threading
import time
import logging
import re
import datetime
from .color_printer import ColorPrinter
import pymysql

class Danmu(object):

    def __init__(self,room_id,danmu_content,zhubo_name,user_id,user_name,user_level,client_type):
        self.room_id = room_id
        self.danmu_content = danmu_content
        self.zhubo_name = zhubo_name
        self.user_id = user_id
        self.user_name = user_name
        self.user_level = user_level
        self.client_type = client_type

class BatchInsertThread(threading.Thread):
    def __init__(self,threadID, name, counter,batch_insert_q):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.counter = counter
        self.db = pymysql.connect("localhost", "root", "qweasdzxc", "scrapy_douyu")
        self.cursor = self.db.cursor()
        self.batch_insert_q = batch_insert_q
        pass
    def run(self):
        while True:
            if(self.batch_insert_q.qsize ==0):
                time.sleep(2)
            else:
                sql = "insert into douyu_danmu (room_id,danmu_content,zhubo_name,user_id,user_name,user_level,client_type,create_time) values (%s,%s,%s,%s,%s,%s,%s,now())"
                danmu = self.batch_insert_q.get()
                if(danmu is not None):
                    self.cursor.execute(sql,(getattr(danmu,'room_id'),getattr(danmu,'danmu_content'),getattr(danmu,'zhubo_name'),getattr(danmu,'user_id'),getattr(danmu,'user_name'),getattr(danmu,'user_level'),getattr(danmu,'client_type')))
                    self.db.commit()
        pass


class ParseMsgThread(threading.Thread):
    def __init__(self, threadID, name, counter,socket,fetched_msg_q,zhubo_name,batch_insert_q):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.counter = counter
        self.type_douyutoMe = 690
        self.socket = socket
        self.fetched_msg_q = fetched_msg_q
        self.logger = logging.getLogger('danmu.fm')
        self.zhubo_name = zhubo_name
        self.batch_insert_q = batch_insert_q

    def run(self):
        try:
            while True:
                #接收响应弹幕，并解析
                if(self.fetched_msg_q.qsize()==0):
                    time.sleep(5)
                content = self.fetched_msg_q.get()
                danmu = self.parse_msg(content)
                self.batch_insert_q.put(danmu)
        except ConnectionResetError:
            #socket被斗鱼关闭，重新执行
            print("socket 被关闭请重新开启爬虫")
            pass

    def parse_msg(self,content):
        if (content.strip() == ''):
            return
        msg_content = content.replace("@=", ":")
        try:
            msg_type = re.search('type:(.+?)\/', msg_content).group(1)
            # self.get_all_type(msg_type)
            if msg_type == "chatmsg":
                msg_type_zh = "弹幕消息"
                rid = re.search('\/rid:(.+?)\/', msg_content).group(1) if 'rid:' in msg_content else "unknown"
                uid = re.search('\/uid:(.+?)\/', msg_content).group(1) if 'uid:' in msg_content else "unknown"
                nickname = re.search('\/nn:(.+?)\/', msg_content).group(1) if 'nn:' in msg_content else "unknown"
                content = re.search('\/txt:(.+?)\/', msg_content).group(1) if 'txt:' in msg_content else "unknown"
                level = re.search('\/level:(.+?)\/', msg_content).group(1) if 'level:' in msg_content else "unknown"
                client_type = re.search('\/ct:(.+?)\/', msg_content).group(
                    1) if 'ct:' in msg_content else "unknown"  # ct 默认值 0 web
                if client_type == '1':
                    client_type_str = '苹果'
                elif client_type == '2':
                    client_type_str = '安卓'
                else:
                    client_type_str = '浏览器'
                time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ColorPrinter.green(
                    "|" + msg_type_zh + "| " + self.align_left_str(nickname, 20, " ") + self.align_left_str(
                        "<Lv:" + level + ">", 8, " ") + self.align_left_str("(" + uid + ")", 13,
                                                                            " ") + self.align_left_str(
                        "[" + client_type_str + "]", 10, " ") + "@ " + time + ": " + content + " ")
                danmu = Danmu(rid,content,self.zhubo_name,uid,nickname,level,client_type_str)
                return danmu

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
            self.logger.error("弹幕内容解析错误:" + msg_content)

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

class KeepliveThread(threading.Thread):
    def __init__(self, threadID, name, counter,socket):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.counter = counter
        self.type_douyutoMe = 690
        self.socket = socket
        pass
    def run(self):
        print("心跳机制启动")
        while True:
            content = 'type@=keeplive/tick@=' + str(int(time.time())) + '/\x00'
            content = content.encode('utf-8')
            self.len = len(content) + 8
            self.head_len = self.len
            msg = self.len.to_bytes(4, byteorder='little') + self.head_len.to_bytes(4, byteorder='little') + self.type_douyutoMe.to_bytes(4, byteorder='little') + content
            self.socket.sendall(msg)
            print('心跳包发送成功')
            time.sleep(40)

class ReceiveMsgThread(threading.Thread):
    def __init__(self, threadID, name, counter,socket,fetched_msg_q):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.counter = counter
        self.type_douyutoMe = 690
        self.socket = socket
        self.fetched_msg_q = fetched_msg_q

    def run(self):
        try:
            while True:
                #接收响应弹幕，并解析
                self.get_danmu()
        except ConnectionResetError:
            #socket被斗鱼关闭，重新执行
            print("socket 被关闭请重新开启爬虫")
            pass

    def get_danmu(self):
        recv_msg = self.danmu_recv()
        if(recv_msg.strip()!=''):
            self.fetched_msg_q.put(recv_msg)

    def danmu_recv(self):
        buffer = b''
        while True:
            recv_data = self.socket.recv(1024)
            # print(recv_data)
            buffer += recv_data
            if recv_data.endswith(b'\x00'):
                break
        return self.parse_content(buffer)

    def parse_content(self, msg):
        content = msg[12:-1].decode('utf-8', 'ignore')
        return content