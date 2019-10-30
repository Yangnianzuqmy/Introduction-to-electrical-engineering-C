# -*- coding:utf-8 -*-
import jieba
import os

def valid_filename(s):
    import string
    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    s = ''.join(c for c in s if c in valid_chars)
    return s

def write_file():
    file=open('imgs.txt','r')
    folder = 'lab5_html_jieba'                 #存放网页的文件夹
    line=file.readline()
    while line:
        try:
            filename = valid_filename(line.split('\t')[1])
            file_2 = open(filename, 'r')
            if not os.path.exists(folder):  # 如果文件夹不存在则新建
                os.mkdir(folder)
            f = open(os.path.join(folder, filename), 'w')
            seg_list = jieba.cut(file_2.read())
            f.write(' '.join(seg_list).encode('utf8'))  # 将网页存入文件
            f.close()
            line=file.readline()
        except Exception as e:
            line=file.readline()
            print e
            pass
    file.close()


def main():
    write_file()

if __name__ == '__main__':
    main()
