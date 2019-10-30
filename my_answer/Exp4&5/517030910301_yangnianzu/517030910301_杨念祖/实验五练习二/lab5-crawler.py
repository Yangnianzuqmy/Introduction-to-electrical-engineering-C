# encoding: utf-8
from BeautifulSoup import BeautifulSoup
from bs4 import BeautifulSoup
import urllib2
import re
import urlparse
import os
import urllib
import sys

reload(sys)
sys.setdefaultencoding('utf8')


def valid_filename(s):
    import string
    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    s = ''.join(c for c in s if c in valid_chars)
    return s


def get_page(page):
    content = ''
    try:
        content = urllib2.urlopen(page, timeout=10.0).read()
    except:
        urllib2.URLError
    return content

def get_title(content):
    try:
        soup = BeautifulSoup(content)
        title = soup.head.title.string
        return title.strip()
    except Exception as e:
        return 'NONE'

def get_keywords(content):
    content1=BeautifulSoup(content)
    try:
        for i in content1.findAll('meta',{'name':re.compile('^keywords|^/')}):
            return i.get('content','NONE')
    except:
            return 'NONE'


def get_all_links(content, page):
    links = []
    content1=BeautifulSoup(content)
    for i in content1.findAll('a',{'href':re.compile('^http|^/')}):
        if i['href'][0] == '/':
            links.append(urlparse.urljoin(page,i['href']))
        else:
            links.append(i['href'])
    return links

def get_all_imgs_info(content, page):
    imgs= []
    imgs.append(page)
    content1 = BeautifulSoup(content)
    try:
        for i in content1.findAll('img'):
            if i['src'][0] == '/':
                if i.get('alt')=="":
                    imgs.append(['NONE',urlparse.urljoin(page, i['src'])])
                else:
                    imgs.append([i.get('alt','NONE'),urlparse.urljoin(page, i['src'])])
            else:
                if i.get('alt')=="":
                    imgs.append(['NONE', i.get('src', 'NONE')])
                else:
                    imgs.append([i.get('alt', 'NONE'), i.get('src', 'NONE')])
    except:
        pass
    return imgs


def union_dfs(a, b):
    for e in b:
        if e not in a:
            a.append(e)


def union_bfs(a, b):
    for e in b:
        if e not in a:
            a.insert(0, e)


def add_page_to_folder(page, content):  # 将网页存到文件夹里，将网址和对应的文件名写入index.txt中
    index_filename = 'imgs.txt'  # index.txt中每行是'网址 对应的文件名'
    folder = 'lab5_html'  # 存放网页的文件夹
    title = get_title(content)
    img_list=get_all_imgs_info(content,page)
    keywords=get_keywords(content)
    for i in range(1,len(img_list)):
        try:
            if len(img_list[i][1])<255:
                index = open(index_filename, 'a')
                index.write(img_list[i][0]+ '\t' + img_list[i][1] + '\t' +keywords+'\t'+ title+'\t'+page.encode('ascii', 'ignore') + '\n')
                index.close()
                if not os.path.exists(folder):  # 如果文件夹不存在则新建
                    os.mkdir(folder)
                filename=valid_filename(img_list[i][1])
                f = open(os.path.join(folder, filename+'.txt'), 'w')
                f.write(img_list[i][0]+'\n'+keywords+'\n'+title)
                f.close()
        except:
            pass


def crawl(seed, method, max_page):
    tocrawl = [seed]
    crawled = []
    graph = {}
    count = 0
    pages = []

    while tocrawl:
        page = tocrawl.pop()
        if page not in crawled and count < max_page and page not in pages:
            count += 1
            print page
            pages.append(page)
            content = get_page(page)
            add_page_to_folder(page, content)
            outlinks = get_all_links(content, page)
            globals()['union_%s' % method](tocrawl, outlinks)
            crawled.append(page)
            graph[page] = outlinks
    return graph, crawled, pages


def write_outputs(urls, filename):
    with open(filename, 'w') as f:
        for url in urls:
            f.write(str(url))
            f.write('\n')


if __name__ == '__main__':
    seed = 'http://www.taobao.com'
    graph, crawled, pages = crawl(seed, 'bfs', 60000)
