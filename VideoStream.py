class VideoStream:
    cur = 0
    
    def __init__(self, path):
        self.path = path
        try:
            self.file = open(path + '0.jpg', 'rb')
        except:
            raise IOError
        print ("path: " + self.path)
        self.frameNum = 0
        
    def nextFrame(self):
        self.cur += 1
        fileName = self.path + str(self.cur) + '.jpg'
        try:
            self.file = open(fileName, 'rb')
        except:
            self.cur = 0
            fileName = self.path + '0.jpg'
            self.file = open(fileName, 'rb')
        
        print(fileName)
        data = self.file.read()
        self.frameNum += 1
        
        return data