from tkinter import *
import tkinter.messagebox
from PIL import Image, ImageTk
import socket, threading, sys, traceback, os
import time
from RtpPacket import RtpPacket

CACHE_FILE_NAME = "cache-"
CACHE_FILE_EXT = ".jpg"

class Client:
    INIT = 0
    READY = 1
    PLAYING = 2
    state = INIT
    
    SETUP = 0
    PLAY = 1
    PAUSE = 2
    TEARDOWN = 3
    SET_PARAMETER = 4
    DESCRIBE = 5
    
    # Initiation..
    def __init__(self, master, serveraddr, serverport, rtpport, filename):
        self.master = master
        self.master.protocol("WM_DELETE_WINDOW", self.handler)
        self.createWidgets()
        self.serverAddr = serveraddr
        self.serverPort = int(serverport)
        self.rtpPort = int(rtpport)
        self.fileName = filename
        self.rtspSeq = 0
        self.sessionId = 0
        self.requestSent = -1
        self.teardownAcked = 0
        self.connectToServer()
        self.frameNbr = 0
        self.maxFrameNum = 0
        self.curPosition = 0
        self.cacheNum = 0
        self.maxCacheNum = 10
        self.speed = 1.0
        self.SCFlag = 0
        self.PCFlag = 0
    
    def changeSpeed(self, speed):
        # print('change speed to: ' + speed)
        self.speed = speed
        self.SCFlag = 1
        self.sendRtspRequest(self.SET_PARAMETER)
        self.SCFlag = 0
        time.sleep(0.05)

    def changePosition(self, position):
        # print('change position to: frame' + position)
        if abs(int(position)-self.curPosition)<=5:
            self.curPosition = int(position)
        else:
            self.curPosition = int(position)
            self.PCFlag = 1
            self.sendRtspRequest(self.SET_PARAMETER)
            self.PCFlag = 0
            time.sleep(0.05)

    def createWidgets(self):
        """Build GUI."""
        # Create Setup button
        self.setup = Button(self.master, width=20, padx=3, pady=3)
        self.setup["text"] = "Setup"
        self.setup["command"] = self.setupMovie
        self.setup.grid(row=1, column=0, padx=2, pady=2)
        
        # Create Play button		
        self.start = Button(self.master, width=20, padx=3, pady=3)
        self.start["text"] = "Play"
        self.start["command"] = self.playMovie
        self.start.grid(row=1, column=1, padx=2, pady=2)
        
        # Create Pause button			
        self.pause = Button(self.master, width=20, padx=3, pady=3)
        self.pause["text"] = "Pause"
        self.pause["command"] = self.pauseMovie
        self.pause.grid(row=1, column=2, padx=2, pady=2)
        
        # Create Teardown button
        self.teardown = Button(self.master, width=20, padx=3, pady=3)
        self.teardown["text"] = "Teardown"
        self.teardown["command"] =  self.exitClient
        self.teardown.grid(row=1, column=3, padx=2, pady=2)
        
        # Create a label to display the movie
        self.label = Label(self.master, height=19)
        self.label.grid(row=0, column=0, columnspan=4, sticky=W+E+N+S, padx=5, pady=5) 

        self.scale = Scale(self.master, from_=0.5, to=1.5, orient=HORIZONTAL, length=150, showvalue=0, tickinterval=0.25, resolution=0.25, command=self.changeSpeed)
        self.scale.grid(row=2, column=0)
        self.scale.set(1)

        self.linebar = Scale(self.master, from_=0, to=1, orient=HORIZONTAL, length=300, showvalue=1, resolution=1, command=self.changePosition)
        self.linebar.grid(row=2, column=1, columnspan=3)
        self.linebar.set(0)
        

    def setupMovie(self):
        """Setup button handler."""
        if self.state == self.INIT:
            self.sendRtspRequest(self.SETUP)
            time.sleep(0.1)
            self.sendRtspRequest(self.DESCRIBE)
    
    def exitClient(self):
        """Teardown button handler."""
        self.sendRtspRequest(self.TEARDOWN)		
        self.master.destroy() # Close the gui window
        for i in range(0,10):
            os.remove(CACHE_FILE_NAME + str(self.sessionId) + str(i) + CACHE_FILE_EXT) # Delete the cache image from video

    def pauseMovie(self):
        """Pause button handler."""
        if self.state == self.PLAYING:
            self.sendRtspRequest(self.PAUSE)
    
    def playMovie(self):
        """Play button handler."""
        # print('Play button handler.')
        if self.state == self.READY:
            print('Play button handler.')
            # Create a new thread to listen for RTP packets
            threading.Thread(target=self.listenRtp).start()
            self.playEvent = threading.Event()
            self.playEvent.clear()
            self.sendRtspRequest(self.PLAY)
    
    def listenRtp(self):		
        """Listen for RTP packets."""
        while True:
            try:
                data = self.rtpSocket.recv(20480)
                if data:
                    rtpPacket = RtpPacket()
                    rtpPacket.decode(data)
                    
                    currFrameNbr = rtpPacket.seqNum()
                    # print("Current Seq Num: " + str(currFrameNbr))
                                        
                    if currFrameNbr > self.frameNbr: # Discard the late packet
                        self.frameNbr = currFrameNbr
                        self.updateMovie(self.writeFrame(rtpPacket.getPayload()))
                        
            except:
                # Stop listening upon requesting PAUSE or TEARDOWN
                if self.playEvent.isSet(): 
                    break
                
                # Upon receiving ACK for TEARDOWN request,
                # close the RTP socket
                if self.teardownAcked == 1:
                    self.rtpSocket.shutdown(socket.SHUT_RDWR)
                    self.rtpSocket.close()
                    break
                    
    def writeFrame(self, data):
        """Write the received frame to a temp image file. Return the image file."""
        self.cacheNum += 1;
        if self.cacheNum>=self.maxCacheNum: 
            self.cacheNum = 0
        cachename = CACHE_FILE_NAME + str(self.sessionId) + str(self.cacheNum) + CACHE_FILE_EXT
        file = open(cachename, "wb")
        file.write(data)
        file.close()
        
        return cachename
    
    def updateMovie(self, imageFile):
        """Update the image file as video frame in the GUI."""
        # print("update!!!")
        self.curPosition += 1
        # print("???", self.curPosition)
        tmp = self.curPosition
        self.linebar.set(tmp)
        photo = ImageTk.PhotoImage(Image.open(imageFile))
        self.label.configure(image = photo, height=288)
        self.label.image = photo
        
        
    def connectToServer(self):
        """Connect to the Server. Start a new RTSP/TCP session."""
        self.rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.rtspSocket.connect((self.serverAddr, self.serverPort))
        except:
            tkMessageBox.showwarning('Connection Failed', 'Connection to \'%s\' failed.' %self.serverAddr)
    
    def sendRtspRequest(self, requestCode):
        """Send RTSP request to the server."""
        
        # Setup request
        if requestCode == self.SETUP and self.state == self.INIT:
            threading.Thread(target=self.recvRtspReply).start()
            # Update RTSP sequence number.
            self.rtspSeq += 1
            # Write the RTSP request to be sent.
            request = 'SETUP ' + self.fileName + ' RTSP/1.0\nCSeq: ' + str(self.rtspSeq) + '\nTransport: RTP/UDP; client_port= ' + str(self.rtpPort)
            # Keep track of the sent request.
            self.requestSent = self.SETUP 
        
        # Play request
        elif requestCode == self.PLAY and self.state == self.READY:
            self.rtspSeq += 1
            request = 'PLAY ' + self.fileName + ' RTSP/1.0\nCSeq: ' + str(self.rtspSeq) + '\nSession: ' + str(self.sessionId)
            self.requestSent = self.PLAY
        
        # Pause request
        elif requestCode == self.PAUSE and self.state == self.PLAYING:
            self.rtspSeq += 1
            request = 'PAUSE ' + self.fileName + ' RTSP/1.0\nCSeq: ' + str(self.rtspSeq) + '\nSession: ' + str(self.sessionId)
            self.requestSent = self.PAUSE
            
        # Teardown request
        elif requestCode == self.TEARDOWN and not self.state == self.INIT:
            self.rtspSeq += 1
            request = 'TEARDOWN ' + self.fileName + ' RTSP/1.0\nCSeq: ' + str(self.rtspSeq) + '\nSession: ' + str(self.sessionId) 
            self.requestSent = self.TEARDOWN

        elif requestCode == self.SET_PARAMETER and not self.state == self.INIT:
            self.rtspSeq += 1
            if self.SCFlag:
                request = 'SET_PARAMETER ' + self.fileName + ' RTSP/1.0\nCSeq: ' + str(self.rtspSeq) + '\nSession: ' + str(self.sessionId)  + '\nSpeed: ' + str(self.speed)
            elif self.PCFlag:
                request = 'SET_PARAMETER ' + self.fileName + ' RTSP/1.0\nCSeq: ' + str(self.rtspSeq) + '\nSession: ' + str(self.sessionId)  + '\nPosition: ' + str(self.curPosition)
            self.requestSent = self.SET_PARAMETER

        elif requestCode == self.DESCRIBE:
            self.rtspSeq += 1
            request = 'DESCRIBE ' + self.fileName + ' RTSP/1.0\nCSeq: ' + str(self.rtspSeq) + '\nSession: ' + str(self.sessionId)
            self.requestSent = self.DESCRIBE

        else:
            return
        
        # Send the RTSP request using rtspSocket.
        self.rtspSocket.send(request.encode())
        time.sleep(0.1)
        print('\nData sent:\n' + request)
    
    def recvRtspReply(self):
        """Receive RTSP reply from the server."""
        while True:
            reply = self.rtspSocket.recv(1024)
            
            if reply: 
                self.parseRtspReply(reply.decode("utf-8"))
                print ('\nData recieve:\n' + reply.decode("utf-8"))
                
            # Close the RTSP socket upon requesting Teardown
            if self.requestSent == self.TEARDOWN:
                self.rtspSocket.shutdown(socket.SHUT_RDWR)
                self.rtspSocket.close()
                break
    
    def parseRtspReply(self, data):
        """Parse the RTSP reply from the server."""
        lines = str(data).split('\n')
        seqNum = int(lines[1].split(' ')[1])
        
        # Process only if the server reply's sequence number is the same as the request's
        if seqNum == self.rtspSeq:
            session = int(lines[2].split(' ')[1])
            # New RTSP session ID
            if self.sessionId == 0:
                self.sessionId = session
            
            # Process only if the session ID is the same
            if self.sessionId == session:
                if int(lines[0].split(' ')[1]) == 200: 
                    if self.requestSent == self.SETUP:
                        # Update RTSP state.
                        self.state = self.READY
                        # Open RTP port.
                        self.openRtpPort()
                    elif self.requestSent == self.PLAY:
                        print("curPosition: ", self.curPosition)
                        self.state = self.PLAYING
                    elif self.requestSent == self.PAUSE:
                        self.state = self.READY
                        # The play thread exits. A new thread is created on resume.
                        self.playEvent.set()
                    elif self.requestSent == self.TEARDOWN:
                        self.state = self.INIT
                        # Flag the teardownAcked to close the socket.
                        self.teardownAcked = 1 
                    #elif self.requestSent = self.SET_PARAMETER:
                        
                    elif self.requestSent == self.DESCRIBE:
                        self.maxFrameNum = int(lines[3].split(' ')[1])
                        self.linebar['to'] = self.maxFrameNum
                        # self.bar.set(50)
                        # self.bar['variable'] = self.curPosition
    
    def openRtpPort(self):
        """Open RTP socket binded to a specified port."""
        # Create a new datagram socket to receive RTP packets from the server
        self.rtpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Set the timeout value of the socket to 0.5sec
        self.rtpSocket.settimeout(0.5)
        
        try:
            # Bind the socket to the address using the RTP port given by the client user
            self.rtpSocket.bind(("", self.rtpPort))
        except:
            tkMessageBox.showwarning('Unable to Bind', 'Unable to bind PORT=%d' %self.rtpPort)

    def handler(self):
        """Handler on explicitly closing the GUI window."""
        self.pauseMovie()
        if tkMessageBox.askokcancel("Quit?", "Are you sure you want to quit?"):
            self.exitClient()
        else: # When the user presses cancel, resume playing.
            self.playMovie()

if __name__ == "__main__":
    try:
        serverAddr = sys.argv[1]
        serverPort = sys.argv[2]
        rtpPort = sys.argv[3]
        fileName = sys.argv[4]	
    except:
        print ("[Usage: ClientLauncher.py Server_name Server_port RTP_port Video_file]\n")
        sys.exit()

    root = Tk()
    app = Client(root, serverAddr, serverPort, rtpPort, fileName)
    app.master.title("RTPClient")
    root.mainloop()
    