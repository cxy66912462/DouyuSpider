# encoding: utf-8
#@author: chaoxingyu
#@file: main.py
#@time: 2017/9/1 14:01

from scrapy.cmdline import execute
import sys
import os
import re
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
execute(['scrapy','crawl','douyu'])

# arg = int(1).__str__()
# if arg and isinstance(arg, str) != True:
#     raise TypeError("Cannot mix str and non-str arguments")