#!/usr/bin/env python
# encoding: utf-8
INDEX_DIR = "IndexFiles.index"
import re
from urlparse import urlparse

import sys, os, lucene, threading, time
from datetime import datetime
reload(sys)
sys.setdefaultencoding('utf8')
from java.io import File
from org.apache.lucene.analysis.miscellaneous import LimitTokenCountAnalyzer
from org.apache.lucene.analysis.standard import StandardAnalyzer
from org.apache.lucene.document import Document, Field, FieldType
from org.apache.lucene.index import FieldInfo, IndexWriter, IndexWriterConfig
from org.apache.lucene.store import SimpleFSDirectory
from org.apache.lucene.util import Version

from org.apache.lucene.analysis.core import WhitespaceAnalyzer




"""
This class is loosely based on the Lucene (java implementation) demo class 
org.apache.lucene.demo.IndexFiles.  It will take a directory as an argument
and will index all of the files in that directory and downward recursively.
It will index on the file path, the file name and the file contents.  The
resulting Lucene index will be placed in the current directory and called
'index'.
"""

topHostPostfix = (    '.com','.la','.io','.co','.info','.net','.org','.me','.mobi',
                      '.us','.biz','.xxx','.ca','.co.jp','.com.cn','.net.cn',
                      '.org.cn','.mx','.tv','.ws','.ag','.com.ag','.net.ag',
                      '.org.ag','.am','.asia','.at','.be','.com.br','.net.br',
                      '.bz','.com.bz','.net.bz','.cc','.com.co','.net.co',
                      '.nom.co','.de','.es','.com.es','.nom.es','.org.es',
                      '.eu','.fm','.fr','.gs','.in','.co.in','.firm.in','.gen.in',
                      '.ind.in','.net.in','.org.in','.it','.jobs','.jp','.ms',
                      '.com.mx','.nl','.nu','.co.nz','.net.nz','.org.nz',
                      '.se','.tc','.tk','.tw','.com.tw','.idv.tw','.org.tw',
                      '.hk','.co.uk','.me.uk','.org.uk','.vg', ".com.hk")

def get_top_host(url):
    parts = urlparse(url)
    host = parts.netloc
    extractPattern = r'[^\.]+('+'|'.join([h.replace('.',r'\.') for h in topHostPostfix])+')$'
    pattern = re.compile(extractPattern,re.IGNORECASE)
    m = pattern.search(host)
    return m.group() if m else host

class Ticker(object):

    def __init__(self):
        self.tick = True

    def run(self):
        while self.tick:
            sys.stdout.write('.')
            sys.stdout.flush()
            time.sleep(1.0)


class IndexFiles(object):
    """Usage: python IndexFiles <doc_directory>"""

    def __init__(self, root, storeDir):

        if not os.path.exists(storeDir):
            os.mkdir(storeDir)

        store = SimpleFSDirectory(File(storeDir))  # 索引位置存放的文件
        analyzer = WhitespaceAnalyzer(Version.LUCENE_CURRENT)
        analyzer = LimitTokenCountAnalyzer(analyzer, 1048576)  # analyzer是用来对文档进行词法分析和语言处理的
        config = IndexWriterConfig(Version.LUCENE_CURRENT, analyzer)
        config.setOpenMode(IndexWriterConfig.OpenMode.CREATE)
        writer = IndexWriter(store, config)  # 创建一个Indexwriter用来写索引文件

        self.indexDocs(root, writer)
        ticker = Ticker()
        print 'commit index',
        threading.Thread(target=ticker.run).start()
        writer.commit()
        writer.close()
        ticker.tick = False
        print 'done'

    def indexDocs(self, root, writer):

        t1 = FieldType()
        t1.setIndexed(True)
        t1.setStored(True)
        t1.setTokenized(False)

        t2 = FieldType()
        t2.setIndexed(True)
        t2.setStored(False)
        t2.setTokenized(True)
        t2.setIndexOptions(FieldInfo.IndexOptions.DOCS_AND_FREQS_AND_POSITIONS)

        file = open('index.txt', 'r')
        filename_list = []
        title_list = []
        url_list = []
        line = file.readline()
        while line:
            try:
                tmp = line.split('\t')
                filename_list.append(tmp[0])
                title_list.append(tmp[1])
                url_list.append(tmp[2])
                line = file.readline()
            except:
                line = file.readline()
                pass
        file.close()

        print root

        for root, dirnames, filenames in os.walk(root):  # 遍历testfolder下的文件
            for i in range(len(filename_list)):
                print "adding", filename_list[i]
                try:
                    path = os.path.join(root, filename_list[i])
                    file = open(path)
                    contents = unicode(file.read(), 'utf8')  # 将文件转为unicode再处理，假设原doc编码为GBK，并将内容存放在contents中
                    file.close()
                    doc = Document()
                    doc.add(Field("name", filename_list[i], t1))
                    doc.add(Field("path", path, t1))
                    doc.add(Field("title", title_list[i], t1))
                    doc.add(Field("url", url_list[i], t1))
                    doc.add(Field("site",get_top_host(url_list[i]),t1))
                    if len(contents) > 0:
                        doc.add(Field("contents", contents, t2))
                    else:
                        print "warning: no content in %s" % filename_list[i]
                    writer.addDocument(doc)
                except Exception, e:
                    print "Failed in indexDocs:", e


if __name__ == '__main__':
    lucene.initVM(vmargs=['-Djava.awt.headless=true'])  # 初始化Java虚拟机
    print 'lucene', lucene.VERSION
    start = datetime.now()

    IndexFiles('html_jieba', "index")
    end = datetime.now()
    print end - start
