# -*- coding:utf-8 -*-
import jieba
import os

def write_file(): #将网页存到文件夹里，将网址和对应的文件名写入index.txt中
    index_filename = 'index.txt'    #index.txt中每行是'网址 对应的文件名'
    file=open('index.txt','r')
    folder = 'html_jieba'                 #存放网页的文件夹
    line=file.readline()
    while line:
        try:
            filename = line.split('\t')[0]
            file_2 = open(filename, 'r')
            if not os.path.exists(folder):  # 如果文件夹不存在则新建
                os.mkdir(folder)
            f = open(os.path.join(folder, filename), 'w')
            seg_list = jieba.cut(file_2.read())
            f.write(' '.join(seg_list).encode('utf8'))  # 将网页存入文件
            f.close()
            line=file.readline()
        except:
            pass
    file.close()


def main():
    write_file()

if __name__ == '__main__':
    main()
