# encoding: utf-8
#@author: chaoxingyu
#@file: MySqlUtil.py
#@time: 2017/9/14 13:51
import pymysql
import time

class MySqlConnect(object):

    def __init__(self,host='localhost',port=3306,user='root',password='qweasdzxc',dbname='scrapy_douyu'):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.dbname = dbname

    def connect(self):
        try:
            log('开始创建连接')
            self.connect = pymysql.connect(host=self.host,port=self.port,user=self.user,passwd=self.password,db=self.dbname,charset="utf8")
            cursor = self.connect.cursor()
            self.cursor = cursor
            log('成功创建连接')
        except Exception as e:
            log('MySql Create Connect Error:'+str(e))

    def execute_query(self,sql):
        try:
            log('开始执行sql')
            # 执行SQL语句
            self.cursor.execute(sql)
            # 获取所有记录列表
            results = self.cursor.fetchall()
            for row in results:
                print(row)
            log('完成执行sql')
        except Exception as e:
            log('Query Sql Error:'+str(e))

    def execute_insert(self,sql,params):
        try:
            log('开始执行sql')
            self.cursor.execute(sql,params)
            self.connect.commit()
            log('sql执行完成')
        except Exception as e:
            #发生错误时,回滚操作
            log('Insert Sql Error:'+str(e))
            self.connect.rollback()
            log('发生错误,进行回滚')


    def close(self):
        try:
            log('开始关闭连接')
            self.connect.close()
            log('成功关闭连接')
        except Exception as e:
            log('MySql Connect Close Error:'+str(e))

def log(str):
    now_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
    log = now_time + '\t\t' + str
    with open('mysql_log.txt', 'a', encoding='utf-8')as f:
        f.writelines(log + '\n')
    print(log)