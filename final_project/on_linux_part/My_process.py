# coding=utf8
import os
import re
import wave

import numpy as np
import pyaudio
import time


#plt.xlim(6000,6030)
#plt.ylim(0,500)
#注：时间以窗口位置表示（转移到真实时间单位ms需要除每秒窗口数windows_density），频率就是真实频率
#加入了汉明窗，分辨率20，全局阈值，不合并声道


class voice():
    def load(self, filepath):
        '''

        :param filepath: 文件路径，为wav文件
        :return: 如果无异常则返回True，如果有异常退出并返回False
        self.wave_data内储存着多通道的音频数据，其中self.wave_data[0]代表第一通道
        具体有几通道，看self.nchannels
        '''
        f = wave.open(filepath)
        params = f.getparams()
        self.nchannels, self.sampwidth, self.framerate, self.nframes = params[:4] #nchannels：通道数（2）/samplewidth：采样大小（2字节，即16bit)/framerate:采样频率（48000：一秒采样几次，采样一次一帧，一帧数据大小为采样大小*通道数）
        #print(filepath,'音频文件属性————通道：',self.nchannels,'采样大小:',self.sampwidth,'采样频率:',self.framerate,'帧数:',self.nframes)
        str_data = f.readframes(self.nframes)                                     #nframes: 总共的帧数（采样次数）
        self.wave_data = np.fromstring(str_data, dtype=np.short)                  #wave中readframes以bytes类型(与str类似)读出音频中所有帧，用numpy转换成int型一维向量----wave_data(此时向量是[LRLRLR...])
        self.wave_data.shape = -1, self.nchannels                                 #调整矩阵长宽,使一行包含这一帧的L通道和R通道分量如[[LR][LR]...]，-1表示行数根据列数自动适应----理论上行数就是帧数。
        self.wave_data = self.wave_data.T                                         #将向量转置,使第一行包含所有帧的L通道分量，第二行...,最终的wave_data变成[[LLL...][RRR...]]
        #下面两行合并声道（删除不合并）
        f.close()
        self.name = os.path.basename(filepath)  # 记录下文件名
        return True

    #计算歌的指纹--------四分钟用时大约1.5秒
    #输入：windows_density每秒窗口数，denoise是否需要降噪（用于录音音频）
    def fp(self, windows_density=20, denoise=False):
        windows_size=self.framerate//windows_density     #windows_size:每个窗口的帧数
        hamming_window = np.hamming(windows_size)
        if denoise:
            noise_fft=self.denoise(2, windows_size)
            self.landmarks = []  # 用landmarks储存landmark，landmark是一个tuple：（时间，频率），并根据先时间后频率对landmark在list中从前到后排序
            #!!!
            time = []
            frequency = []

            # 每次的fft先暂时储存起来！等找出最大的aver_max再秋后算账（处理处landmark）
            ffts = []
            max_aver_max = 0
            for i in range(0, self.nframes - windows_size, windows_size):
                window = self.wave_data[0][i:i + windows_size]  # window即一个窗口（离散的时域函数）
                fft = np.abs(np.fft.fft(window))  # fft即对这个窗口进行傅里叶转换得到的离散频域函数
                #对噪声反向补偿
                fft = fft-noise_fft
                # 滤波并保留landmark----（出现的时间，频率）
                max1 = np.max(fft[:10])
                max2 = np.max(fft[10:20])
                max3 = np.max(fft[20:40])
                max4 = np.max(fft[40:80])
                max5 = np.max(fft[80:160])
                max6 = np.max(fft[160:511])
                aver_max = (max1 + max2 + max3 + max4 + max5 + max6) / 6
                if aver_max > max_aver_max:
                    max_aver_max = aver_max
                ffts.append(fft[:windows_size // 2])
            max_aver_max *= 0.8
            for i in range(len(ffts)):
                for j in range(windows_size // 2):  # 只有前一般的频谱是不重复的，所以统计landmark只统计前一半
                    if ffts[i][j] > max_aver_max:
                        self.landmarks.append((int((i)), int(j * windows_density)))
                        #!!!
                        time.append(int(i))
                        frequency.append(int(j * windows_density))

            # 计算锚(取targetzone为紧跟在锚点后面的5个点),储存在fps中，每个锚就是一个指纹，用一个tuple表示:（锚点绝对时间位置，锚点频率，目标点频率，时间差）-------全部转换成string！
            self.fps = []
            for i in range(0, len(self.landmarks) - 5):
                for j in range(i+1, i + 6):
                    self.fps.append((str(self.landmarks[i][0]), str(self.landmarks[i][1]), str(self.landmarks[j][1]),
                                     str(self.landmarks[j][0] - self.landmarks[i][0])))
            #!!!
            plt.scatter(time, frequency)
            plt.show()
            print(len(self.landmarks))



        else:
            self.landmarks = []  # 用landmarks储存landmark，landmark是一个tuple：（时间，频率），并根据先时间后频率对landmark在list中从前到后排序
            '''
            time = []
            frequency = []
            '''
            #每次的fft先暂时储存起来！等找出最大的aver_max再秋后算账（处理处landmark）
            ffts=[]
            max_aver_max=0
            for i in range(0, self.nframes - windows_size, windows_size):
                window = self.wave_data[0][i:i + windows_size]  # window即一个窗口（离散的时域函数）
                #下面两行用汉明窗（删除即默认矩形窗）
                tailored_window = np.array(window) * np.array(hamming_window)  # 用haming窗口剪裁
                fft = np.abs(np.fft.fft(tailored_window))  # fft即对这个窗口进行傅里叶转换得到的离散频域函数
                # 滤波并保留landmark----（出现的时间，频率）
                max1 = np.max(fft[:10])
                max2 = np.max(fft[10:20])
                max3 = np.max(fft[20:40])
                max4 = np.max(fft[40:80])
                max5 = np.max(fft[80:160])
                max6 = np.max(fft[160:511])
                aver_max = (max1 + max2 + max3 + max4 + max5 + max6) / 6
                if aver_max>max_aver_max:
                    max_aver_max=aver_max
                ffts.append(fft[:windows_size//2])
            max_aver_max *= 0.8
            for i in range(len(ffts)):
                for j in range(windows_size // 2):  # 只有前一般的频谱是不重复的，所以统计landmark只统计前一半
                    if ffts[i][j] > max_aver_max:
                        self.landmarks.append((int((i)), int(j * windows_density)))
                        '''
                        time.append(int(i))
                        frequency.append(int(j * windows_density))
                        '''
            # 计算锚(取targetzone为紧跟在锚点后面的5个点),储存在fps中，每个锚就是一个指纹，用一个tuple表示:（锚点绝对时间位置，锚点频率，目标点频率，时间差）-------全部转换成string！
            self.fps = []
            for i in range(0, len(self.landmarks) - 5):
                for j in range(i+1, i+6):
                    self.fps.append((str(self.landmarks[i][0]), str(self.landmarks[i][1]), str(self.landmarks[j][1]), str(self.landmarks[j][0] - self.landmarks[i][0])) )
            '''
            plt.scatter(time, frequency)
            plt.show()
            print(len(self.landmarks))
            '''

    #设等待时长是2s，所用时间大概0.26秒
    #输入:wait_time开始录音前的等待时间，windows_size窗口大小; 输出噪声的频谱
    def denoise(self, wait_time, windows_size):
        windows_num=wait_time*self.framerate//windows_size       #根据（等待时间内）总的帧数与窗口大小确定一共几个窗口，各个窗口分别计算频谱后取平均
        ffts=[]
        for i in range(0, wait_time*self.framerate, windows_size):
            window=self.wave_data[0][i:i+windows_size]
            fft=np.abs(np.fft.fft(window))
            ffts.append(fft)
        average_fft=np.array([0 for i in range(windows_size)])
        for i in range(windows_num):
            for j in range(windows_size):
                average_fft[j]+=ffts[i][j]
        for j in range(windows_size):
            average_fft[j]/=windows_num
        return average_fft




    def play(self, filepath):
        '''
        音频播放方法
        :param filepath:文件路径
        :return:
        '''
        chunk = 1024                        #一次读取1024字节数据
        wf = wave.open(filepath, 'rb')
        p = pyaudio.PyAudio()
        # 打开声音输出流
        stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                        channels=wf.getnchannels(),
                        rate=wf.getframerate(),
                        output=True)
        # 写声音输出流进行播放
        while True:
            data = wf.readframes(chunk)
            if data == "": break
            stream.write(data)
        stream.close()
        p.terminate()


if __name__ == '__main__':
    p=voice()
    p.play('65538test.wav')
