from random import randint
import sys, traceback, threading, socket
import os, sys
from PIL import Image
import ffmpeg
import numpy
import cv2
from RtpPacket import RtpPacket
from VideoStream import VideoStream


INIT = 0
PLAYING = 2
OK = 1

# process server
class Server:
    clientInfo = {}
    state = INIT    
    def __init__(self, clientInfo):
        self.clientInfo = clientInfo
    
    def run(self):
        threading.Thread(target=self.getRtspRquest).start()

    def getRtspRquest(self):
        #Receive RTSP request from the client.
        connSoket = self.clientInfo['rtspSocket'][0]
        while True:
            data = connSoket.recv(1024).decode()
            if data:
                print ("\nRecieve data:\n" + data)
                self.processRtspRequest(data)

    def processRtspRequest(self, data): 
        #Process RTSP request from the client.
        request = data.split('\n')
        #print(request)
		
        param = request[0]
        line = param.split(' ')
        seq = request[1].split(' ')[1]
        # addr = request[2]
        # List = param.split(' ')
        # seqList = seq.split(' ')
        # addrList = addr.split(' ')
        requestType = line[0]

        if requestType == 'SETUP': 
            self.clientInfo['videoStream'] = VideoStream(line[1])
            self.vidcap = cv2.VideoCapture(line[1])
            self.clientInfo['fps'] = self.vidcap.get(5)
            self.clientInfo['maxFrameNum'] = self.vidcap.get(7)
            self.clientInfo['speed'] = 1.0
            self.clientInfo['position'] = 0
            self.clientInfo['seqNum'] = 0
            self.clientInfo['rtpPort'] = request[2].split(' ')[3]
            self.state = OK           
            self.clientInfo['session'] = randint(100000, 999999) # 随机生成session

            self.RtspResponse(seq)

        elif requestType == 'PLAY':
            if self.state == OK:                             
                self.state = PLAYING
                self.clientInfo['rtpSocket'] = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.RtspResponse(seq)
                self.clientInfo['event'] = threading.Event()
                self.clientInfo['worker'] = threading.Thread(target=self.sendRtp)
                self.clientInfo['worker'].start() #开始播放

        elif requestType == 'PAUSE':
            if self.state == PLAYING:
                self.state = OK
                self.clientInfo['event'].set() #停止播放
                self.RtspResponse(seq)

        elif requestType == 'TEARDOWN':
            self.clientInfo['event'].set()
            self.RtspResponse(seq)
            self.clientInfo['rtpSocket'].close()

        elif requestType == 'SET_PARAMETER':
            if 'Speed' == request[3].split(' ')[0][:-1]:
                # print(request[3].split(' '),"!!!!!!!",float(request[3].split(' ')[1]))
                self.clientInfo['speed'] = float(request[3].split(' ')[1])
            if 'Position' == request[3].split(' ')[0][:-1]:
                # print(request[3].split(' '),"!!!!!!!",int(request[3].split(' ')[1]))
                self.clientInfo['videoStream'].changePosition(int(request[3].split(' ')[1]))
                self.clientInfo['position'] = int(request[3].split(' ')[1])
            self.RtspResponse(seq)

        elif requestType == 'DESCRIBE':
            param = {'item': 'maxFrameNum', 'cont': int(self.clientInfo['maxFrameNum'])}
            self.RtspResponse(seq, param)


    def sendRtp(self): 
        while True:          
            self.clientInfo['event'].wait(1/self.clientInfo['fps']/self.clientInfo['speed'])
            #self.clientInfo['event'].wait(1)
            if self.clientInfo['event'].isSet():
                break
            frame = self.clientInfo['videoStream'].nextFrame()
            if frame: 
                self.clientInfo['seqNum'] += 1
                ip = self.clientInfo['rtspSocket'][1][0]
                port = int(self.clientInfo['rtpPort'])
                self.clientInfo['rtpSocket'].sendto(self.setRtp(frame, self.clientInfo['seqNum']), (ip, port))

    def setRtp(self, frame, currentFrame):
        rtpPacket = RtpPacket()
        rtpPacket.encode(2, 0, 0, 0, currentFrame, 0, 26, 0, frame)
        return rtpPacket.getPacket()
    
    def RtspResponse(self, seq, param={}):
        response = 'RTSP/1.0 200 OK\nCSeq: ' + \
                seq + \
                '\nSession: ' + \
                str(self.clientInfo['session'])
        if len(param) > 0:
            response += '\n' + param['item'] + ': ' + str(param['cont'])
        print("\nSend data:\n" + response)
        connSoket = self.clientInfo['rtspSocket'][0]
        connSoket.send(response.encode())

def main():
    try:
        serverPort = int(sys.argv[1])
    except:
        print ("[Usage: Server.py Server_port]\n")
    connSoket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    connSoket.bind(('', serverPort))
    connSoket.listen(5)
    while True: 
        clientInfo = {}
        clientInfo['rtspSocket'] = connSoket.accept()
        Server(clientInfo).run() 

if __name__ == "__main__":
    main()
