# coding=utf-8
#!/usr/bin/env python

INDEX_DIR = "IndexFiles.index"

import time
import numpy as np
import sys, os, lucene
reload(sys)
sys.setdefaultencoding("utf-8")
import My_process
import pymysql as mysql
from java.io import File
from org.apache.lucene.analysis.standard import StandardAnalyzer
from org.apache.lucene.index import DirectoryReader
from org.apache.lucene.queryparser.classic import QueryParser
from org.apache.lucene.store import SimpleFSDirectory
from org.apache.lucene.search import IndexSearcher
from org.apache.lucene.util import Version
from org.apache.lucene.analysis.core import KeywordAnalyzer


"""
This script is loosely based on the Lucene (java implementation) demo class 
org.apache.lucene.demo.SearchFiles.  It will prompt for a search query, then it
will search the Lucene index in the current directory called 'index' for the
search query entered against the 'contents' field.  It will then display the
'path' and 'name' fields for each of the hits it finds in the index.  Note that
search.close() is currently commented out because it causes a stack overflow in
some cases.
"""

#传入一个string类型的fp，三个int用空格相连为string，返回在倒排索引中找到的所有couple(list包含tuple)
def run(searcher, analyzer, fp):
    fp = unicode(fp, 'UTF-8')
    query = QueryParser(Version.LUCENE_CURRENT, "fp", analyzer).parse(fp)
    scoreDocs = searcher.search(query, 10000).scoreDocs

    result=[]

    for i, scoreDoc in enumerate(scoreDocs):
        doc = searcher.doc(scoreDoc.doc)
        result.append((doc.get("time_loc"), doc.get("song_id")))
        # print 'explain:', searcher.explain(query, scoreDoc.doc)
    return result

class SearchFiles():
    #创建对象时自动连接服务器并准备好索引搜索的条件（searcher和analyzer）
    def __init__(self, host, user, passwd, name):
        self.conn = mysql.connect(host, user, passwd, name, charset='utf8')
        self.cursor = self.conn.cursor()
        STORE_DIR = "fp_index"
        lucene.initVM(vmargs=['-Djava.awt.headless=true'])
        print 'lucene', lucene.VERSION
        # base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        directory = SimpleFSDirectory(File(STORE_DIR))
        self.searcher = IndexSearcher(DirectoryReader.open(directory))
        self.analyzer = KeywordAnalyzer()

    #手动调用end函数关闭连接
    def end(self):
        self.cursor.close()
        self.conn.close()

    #最终的匹配结果通过这个函数转换成真实的歌曲ID
    def get_oldid(self, newid):
        sql="""SELECT OLD FROM ID_TRANS WHERE NEW ='%s' """%(newid)
        self.cursor.execute(sql)
        result=self.cursor.fetchone()
        oldid=result[0]
        return oldid

    def get_newid(self,oldid):
        sql = """SELECT NEW FROM ID_TRANS WHERE OLD ='%s' """ % (oldid)
        self.cursor.execute(sql)
        result = self.cursor.fetchall()
        newid = result[0]
        return newid

    def get_info(self, id):
        sql="""SELECT name, singers FROM song WHERE id='%s' """%(id)
        self.cursor.execute(sql)
        result=self.cursor.fetchone()
        return result

    #输入录音的文件名，返回匹配结果
    def search(self, filename):
        start=time.time()
        v = My_process.voice()
        v.load(filename)
        v.fp()
        end=time.time()
        print '提取记录指纹：', end-start

        # 创建好双层哈希表
        hashtable = [[[] for j in range(6000)] for k in range(
            50)]  # 哈希表从外向内：1.hashtable[0]--3000个[],每一个[]代表一首歌； 2.hashtable[0][0]--300000个[],每一个[]代表一个歌中的时间点； 3.hashtable[0][0][0]--N个int，每一个int代表检索出这对couple（歌+时间点）的record音频指纹所在record音频中的时间点
        # song_flag:至少出现过一个time_loc的歌曲标1，否则0
        song_flag = np.array([0 for i in range(50)])
        # 储存每个歌曲指纹和相应的记录指纹比较后出现的最多的delta_time的次数
        max_delta_time = [0 for i in range(50)]
        end =time.time()
        for i in v.fps:
            #注意：i包含了在录音中的指纹绝对位置，而从表格中下来的指纹不包含在音乐中的绝对位置,内容都是string
            #将指纹（除去绝对时间位置）连成字符串，从FP_IN_DEX找到另一张表格中的位置
            fp = "-".join(list(i[1:4]))
            #从索引中找到couple
            couples=run(self.searcher, self.analyzer,fp)
            #print len(couples)
            for couple in couples:
                hashtable[int(couple[1])][int(couple[0])].append(int(i[0]))
                song_flag[int(couple[1])]=1
        end2 = time.time()
        print '索引检索：', end2-end
        # 第一次筛选哈希表:time_loc列表中包含元素少于5的清空
        # 第二次筛选哈希表：song_id列表中包含非空time_loc列表少于阈值的删掉这首歌；阈值初步定为记录阈值的50%
        # 第三次筛选：前两次筛选成功晋级后，统计出现最多的时间差
        threshold = int(len(v.fps)//5*0.9)
        for m in range(50):
            if song_flag[m]==0:         #这首歌没有出现任何与记录匹配的锚点
                continue
            else:
                flag = 0  # flag遍历一个歌曲的所有time_loc，记录遍历后还没被清空的time_loc数，然后用于替代song_flag中的1（有可能遍历后没有剩余，那么1变成0）
                for n in range(6000):
                    if len(hashtable[m][n]) > 0:
                        if len(hashtable[m][n]) < 5:  # 不满足一次哈希筛选
                            hashtable[m][n][:]=[]
                        else:
                            flag += 1
                if flag < threshold:  # 不满足二次哈希筛选
                    song_flag[m] = 0
                else:
                    song_flag[m] = flag
                    delta_times = []  # 储存所有出现过的时间差
                    for n in range(6000):
                        if len(hashtable[m][n]) > 0:
                            # 满足条件的歌曲：再次对所有非空time_loc遍历，对每一个非空time_loc，减去对应指纹在记录中的时间地址作为一个delta_time,存入一个列表。遍历完成后，统计列表中出现次数最多的时间差
                            for k in hashtable[m][n]:
                                delta_times.append(n - k)
                        else:
                            pass
                    most_time = np.unique(np.array(delta_times), return_counts=True)[0][0]
                    max_delta_time[m] = most_time
        result = []
        max_delta_time = np.array(max_delta_time)
        end3 = time.time()
        print '筛选：', end3-end2
        for i in range(3):
            id = np.argmax(max_delta_time)
            old_id = self.get_oldid(id)
            max_delta_time = np.delete(max_delta_time, id)
            info=self.get_info(old_id)
            print '搜索结果',i+1,': ',info[0],'————————',info[1][:-1]


if __name__ == '__main__':
    player = My_process.voice()
    zzh = SearchFiles('119.23.74.39', 'qzy', 'qzy111-+', 'wangyiyun')
    result=zzh.search('65538test.wav')

