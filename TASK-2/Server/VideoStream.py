import cv2
from PIL import Image
import numpy as np

class VideoStream:
    cur = -1
    
    def __init__(self, path):
        self.path = path
        self.frameNum = 0
        self.vidcap = cv2.VideoCapture(path)
        self.maxFrameNum = self.vidcap.get(7)
        self.speed = self.vidcap.get(5)

    def nextFrame(self):
        self.cur += 1
        if self.cur>=self.maxFrameNum:
            self.cur = 0
        # print('frame:' + str(self.cur))
        self.vidcap.set(cv2.CAP_PROP_POS_FRAMES, self.cur)
        success, image = self.vidcap.read()
        
        size = image.shape
        tempimg = cv2.resize(image, (int(size[1]/3),int(size[0]/3)),cv2.INTER_LINEAR)
        # cv2.imwrite("video" + "_%d.jpg" % self.cur, tempimg) 

        ret,buf = cv2.imencode(".jpg", tempimg)
        img_bin = Image.fromarray(np.uint8(buf)).tobytes()

        return img_bin

    def changePosition(self, position):
        self.cur = position