import time, json, os, glob, numpy, random
from PIL import Image
from psychopy import core, visual, monitors, event, sound

from .. import feedback

parameters = {
    'Gravity': 0,
    'Speed': 0,
    'frameNo': 0,
    'FPS': None,
    'condition': '',
    'nTubesPassed': 0
}

fbInfo = {
    'fbTime': None,
    'Activation': 0,
    'fbVal': 0
}

class Engine:

    ## Private
    # Default parameters
    __DISPLAY = 'fullscreen'
    __DAYTIME = [8, 19] # Daylight between 8 and 19:59
    __STAGE = { # sizes in proportion
        'Gravity': 1e-5,
        'Floor_Height': 0.1,
        'Floor_Cycle': 24, # length of pattern to repeat
        'nTubes': 2,
        'Threshold_Size': [0.05, 0.1],
        'Text_Size': 0.05
    }
    __T_BIRDtoTUBE = 15 # sec
    __FEEDBACK = {}
    
    # Game variables
    __BestScore = 0

    # Objects
    __Tubes = []
    __Bird = None
    __Feedback = None
    __Mouse = None
    __Log = None
    
    # Low level variables
    __SETTINGS = {
        'FileName': '',
        'Initial': []
    }
    __Window = None
    __Resolution = None
    __Textures = {}
    __ExperimentStart = numpy.inf
    __BirdStart = [0, 0]  # frame, clock
    __FrameDuration = None
    
    def __init__(self,*args):
        if len(args):
            self.__SETTINGS['FileName'] = args[0]
            self.__LoadConfig()

        parameters['Gravity'] = self.__STAGE['Gravity']
        parameters['FPS'] = self.FPS

    def InitWindow(self):
        posX = 0; posY = 0
        dispScr, dispInd, dispRes = self.__DISPLAY.split(':')
        if dispScr == '': dispScr = None
        ind = int(dispInd)
        scr = monitors.Monitor(dispScr)
        ScreenSize = scr.getSizePix()

        if dispRes == 'fullscreen':
            doFullscreen = True
            self.__Resolution = ScreenSize
            posX = 0
            posY = 0
        else:
            doFullscreen = False
            self.__Resolution = [int(i) for i in dispRes.split('x')]
            posX = (ScreenSize[0]-self.__Resolution[0])/2
            posY = (ScreenSize[1]-self.__Resolution[1])/2

        if ind > 0:
            posX = posX + ScreenSize[0]*(ind-1)

        self.__Window = visual.Window(size=self.__Resolution,pos=(posX,posY),units='pix',monitor=scr,fullscr=doFullscreen,winType='pyglet')

        #glob.glob(os.path.join(os.path.dirname(os.path.realpath(__file__)),'sprites','*.png'))
        # Stage
        t = time.localtime()
        im = Image.open(os.path.join(os.path.dirname(os.path.realpath(__file__)),'sprites','Background' + str((t.tm_hour < self.__DAYTIME[0] or t.tm_hour > self.__DAYTIME[1])+1) + '.png'))
        mag = self.__Resolution[1]/im.size[1]
        im = im.resize((int(mag*im.size[0]), int(mag*im.size[1])),Image.BICUBIC)
        CData = numpy.tile(numpy.array(im)/255*2-1,(1,int(numpy.ceil(self.__Resolution[0]/im.size[0])),1))
        self.__Textures['Background'] = visual.ImageStim(self.__Window,image=CData,flipVert=True,size=self.__Resolution,units='pix')


        im = Image.open(os.path.join(os.path.dirname(os.path.realpath(__file__)),'sprites','Floor.png'))
        self.__STAGE['Floor_Height'] = numpy.ceil(self.__Resolution[1]*self.__STAGE['Floor_Height'])
        mag = numpy.round(self.__STAGE['Floor_Height']/im.size[1])
        im = im.resize((int(mag*im.size[0]), int(mag*im.size[1])),Image.BICUBIC)
        CData = numpy.tile(numpy.array(im)/255*2-1,(1,int(numpy.ceil(self.__Resolution[0]/im.size[0]))+1,1)) # leave room for offset
        self.__STAGE['Floor_Cycle'] *= mag
        self.__Textures['Floor'] = visual.ImageStim(self.__Window,image=CData,flipVert=True,size=[CData.shape[1],CData.shape[0]],pos=[0,self.__STAGE['Floor_Height']/2-self.__Resolution[1]/2],units='pix')

        self.__STAGE['Text_Size'] *= self.__Resolution[1]
        self.__Textures['Info'] = visual.TextStim(self.__Window,text='',font='Calibri',height=self.__STAGE['Text_Size'],wrapWidth=self.__Resolution[0],bold=True,color=(-1,-1,-1),pos=[0,self.__STAGE['Text_Size']/2-self.__Resolution[1]/2],units='pix')

        # Bird
        self.__Bird = BirdClass(self.__Window,glob.glob(os.path.join(os.path.dirname(os.path.realpath(__file__)),'sprites','Bird*.png')))

        # Tubes
        for t in range(0,self.__STAGE['nTubes']):
            tX = t*numpy.round(self.__Resolution[0]/self.__STAGE['nTubes'])
            self.__Tubes.append(TubeClass(self.__Window,glob.glob(os.path.join(os.path.dirname(os.path.realpath(__file__)),'sprites','Tube*.png')),
                int(numpy.round(4*(self.__Bird.Size[1]+ self.__Resolution[1]*(self.__Bird.Jump_Duration/2+1)*parameters['Gravity']))),
                tX, self.__STAGE['Floor_Height']))

        # Feedback
        self.__FEEDBACK['maxAct'] = int(self.__Resolution[1]/2)
        self.__Feedback = feedback.Feedback(self.__FEEDBACK)
        # QC: feedback conversion
        # self.__Feedback.Show()
        self.__STAGE['Threshold_Size'] = [numpy.round(self.__STAGE['Threshold_Size'][0]*self.__Resolution[0]),
            2*self.__Feedback.getPlateauX()]

        if self.__FEEDBACK['Simulate']:
            self.__Mouse = event.Mouse(win=self.__Window,visible=True)
            self.__Mouse.setPos([self.__STAGE['Threshold_Size'][0]/2-self.__Resolution[0]/2,0])
        else:
            self.__Mouse = event.Mouse(visible=False)

    def CloseWindow(self):
        self.__Window.close()
        self.__SaveConfig()

        print('[INFO] Score: {:2.3f}'.format(self.Score()))
        print('[INFO] FPS: {:2.3f}'.format(self.FPS()))

    def Update(self):

        if not(parameters['frameNo']): self.__ExperimentStart = time.time()
        tFrame = self.Clock()
        parameters['frameNo'] += 1

        # Background
        self.__Textures['Background'].draw()


        # Feedback
        dat = self.__Feedback.Value(self.__Mouse.getPos()[1])
        if type(dat[1]) == str: parameters['condition'] = dat[1]
        if not(dat[2] is None): fbInfo['fbTime'], fbInfo['Activation'], fbInfo['fbVal'] = dat

        if fbInfo['fbVal'] > 0:
            if not(parameters['Speed']):
                # Ensure T_BIRDtoTUBE adjust FPS if needed
                parameters['Speed'] = int(numpy.ceil(self.__Resolution[0]/(2*self.__T_BIRDtoTUBE*self.FPS())))
                self.__FrameDuration = self.__T_BIRDtoTUBE/(self.__Resolution[0]/(2*parameters['Speed']))
                self.__BirdStart = [tFrame, parameters['frameNo']]

        # if not(numpy.mod(parameters.frameNo,120)): self.__Bird.JumpOnset = None # New Jump in every 2 second if above Threshold       
        self.__Bird.Update(fbInfo['fbVal'])

        # Tubes
        for t in range(0,self.__STAGE['nTubes']):
            self.__Tubes[t].Update()
            # QC: Gap
            # rect = visual.Rect(win=self.__Window,lineColor='red',lineWidth=3,
            #     pos=self.__Tubes[t].XY,width=self.__Tubes[t].Size[0],height=int(numpy.diff(self.__Tubes[t].GapRange)))
            # rect.draw()

        # Threshold
        rect = visual.Rect(win=self.__Window,lineColor='grey',fillColor='grey',
            pos=[self.__STAGE['Threshold_Size'][0]/2-self.__Resolution[0]/2, 
                self.__Feedback.getPlateauX()-self.__STAGE['Threshold_Size'][1]/2],
                width=self.__STAGE['Threshold_Size'][0],height=self.__Feedback.getPlateauX()*2)
        rect.draw()

        # Activation
        rect = visual.Rect(win=self.__Window,lineColor='red',fillColor='red',
            pos=[self.__STAGE['Threshold_Size'][0]/2-self.__Resolution[0]/2, fbInfo['Activation']],width=self.__STAGE['Threshold_Size'][0],height=self.__Resolution[1]/100)
        rect.draw()
        
        # Floor
        self.__Textures['Floor'].pos = [-numpy.mod(parameters['frameNo']*parameters['Speed'], self.__STAGE['Floor_Cycle']), self.__Textures['Floor'].pos[1]]
        self.__Textures['Floor'].draw()

        # Info
        self.__Textures['Info'].text = '{}: {:3.1f} -> {:d} | {:d}'.format(parameters['condition'],fbInfo['Activation'],fbInfo['fbVal'],self.Score())
        self.__Textures['Info'].draw()

        self.__Window.flip()
        # Adjust FPS
        if self.__FrameDuration: 
            while self.Clock()-self.__BirdStart[0] < (parameters['frameNo']-self.__BirdStart[1])*self.__FrameDuration:
                pass

    def Over(self):
        val = False

        # Collision
        tubesInProximity = [self.__Bird.XY[0]+self.__Bird.Size[0]/2 >= tube.XY[0]-tube.Size[0]/2 and self.__Bird.XY[0]-self.__Bird.Size[0]/2 <=  tube.XY[0]+tube.Size[0]/2 for tube in self.__Tubes]
        if any(tubesInProximity):
            t = [t for t in range(0,self.__STAGE['nTubes']) if tubesInProximity[t]][0]
            val = (self.__Bird.XY[1]+self.__Bird.Size[1]/2 >= self.__Tubes[t].GapRange[0]) or (self.__Bird.XY[1]-self.__Bird.Size[1]/2 <= self.__Tubes[t].GapRange[1])
            # QC: print('{}-{}: {}-{}'.format(self.__Bird.XY[1],self.__Bird.Size[1]/2,self.__Tubes[t].GapRange[0],self.__Tubes[t].GapRange[1]))
        
        # Fall
        val = val or (self.__Bird.XY[1] - self.__Bird.Size[1]/2 <= self.__STAGE['Floor_Height']-self.__Resolution[1]/2) 
        
        # Fly over
        val = val or (self.__Bird.XY[1] + self.__Bird.Size[1]/2 >= self.__Resolution[1]/2)

        return val

    def Score(self):
        return numpy.sum([t.XY[0]+t.Size[0] < self.__Bird.XY[0] for t in self.__Tubes]) + parameters['nTubesPassed']

    def Clock(self):
        return time.time() - self.__ExperimentStart
    
    def FPS(self):
        return parameters['frameNo']/self.Clock()

    # Private
    def __LoadConfig(self):
        with open(self.__SETTINGS['FileName']) as config:
            self.__SETTINGS['Initial'] = json.load(config)
            for f in self.__SETTINGS['Initial'].keys():
                setattr(self, '_' + self.__class__.__name__ + '__' + f, self.__SETTINGS['Initial'][f])

    def __SaveConfig(self,*args):
        if len(args): 
            doUpdate = args[0]
        else:
            doUpdate = False

        if not(doUpdate): self.__LoadConfig()
        
        self.__SETTINGS['Initial']['BestScore'] = max(self.__BestScore, self.Score())

        with open(self.__SETTINGS['FileName'],'w') as config:
            json.dump(self.__SETTINGS['Initial'],config,indent=4)


class TexClass:
    # Public
    XY = [0, 0]
    Size = [0, 0]

    # Protected
    _Window = None
    _Resolution = None

    _Textures = []
    _iFrame = 0

    def __init__(self,w):
        self._Window = w
        self._Resolution = w.size


class BirdClass(TexClass):
    
    Size = [0.05]
    JumpOnset = None
    Jump_Duration = 2 # no further jump or fall is possible within (sec)

    __dY = 0

    __FlapSpeed = 0.1
        
    __Oscil_Resolution = 45
    __Oscil_Amplitude = 0.02
    __Oscil_toFlapRatio = 8
    
    __Angle_toSpeed = 30

    def __init__(self,w,pngs):
        super().__init__(w)

        birdS = numpy.ceil(self._Resolution[1]*self.Size[0])
        im = [Image.open(f) for f in pngs]
        mag = numpy.round(birdS/im[0].size[1])
        self.Size = [int(mag*im[0].size[0]),int(mag*im[0].size[1])]
        self._Textures = [visual.ImageStim(self._Window,
            image=i.resize(tuple(self.Size),Image.BICUBIC),
            size=self.Size,pos=[0,0],units='pix')
            for i in im]

    def Update(self,fb):
        
        oY = 0
        angle = 0

        self._iFrame = numpy.mod(int(numpy.ceil(parameters['frameNo']*(parameters['Speed']+0.5)*self.__FlapSpeed))-1,len(self._Textures))
        if not(fb) and not(self.isJumping()): # Oscillate
            oY = numpy.sin(numpy.linspace(0, 2*numpy.pi, self.__Oscil_Resolution))* self._Resolution[1]*self.__Oscil_Amplitude
            oY = oY[int(numpy.mod(numpy.ceil(parameters['frameNo']*0.5*self.__FlapSpeed*self.__Oscil_toFlapRatio)-1,len(oY)))]
            self.__dY = 0
            self.JumpOnset = None
        else:
            if fb > 0: # Jump
                if not(self.isJumping()):
                    self.JumpOnset = parameters['frameNo']
                    self.__dY = self._Resolution[1]*(self.Jump_Duration*parameters['FPS']()+1)*parameters['Gravity'] # self._Resolution[1]*(self.Jump_Duration*parameters['FPS']()/2+1)*parameters['Gravity'] 
            elif fb < 0:
                self.JumpOnset = None

            self.__dY -= self._Resolution[1]*parameters['Gravity']
            self.XY[1] += self.__dY
            angle = min(-self.__dY*self.__Angle_toSpeed, 90)
        
        self._Textures[self._iFrame].pos = [self.XY[0],self.XY[1]+oY]
        self._Textures[self._iFrame].ori = angle
        self._Textures[self._iFrame].draw()
    
    def isJumping(self):
        return not(self.JumpOnset is None) and (parameters['frameNo'] <= (self.JumpOnset+self.Jump_Duration*parameters['FPS']()))


class TubeClass(TexClass):

    Size = [0.1]
    GapRange = [0, 0]

    __Gap = [0, 0]
    __Max_VOffset = 1 # relative to gap, also a jitter between re-occurences of tubes
    
    def __init__(self,w,pngs,gap,posX,floorY):
        super().__init__(w)

        self.__Gap = gap
        self.__Max_VOffset = self.__Max_VOffset*self.__Gap

        tubeW = int(numpy.ceil(self._Resolution[0]*self.Size[0]))
        im = [Image.open(f) for f in pngs]
        mag = tubeW/im[0].size[0]
        im = [i.resize((int(mag*im[0].size[0]), int(mag*im[0].size[1])),Image.BICUBIC) for i in im]
        
        # create scaled tube
        ext = int(numpy.ceil(self._Resolution[1] - floorY + self.__Max_VOffset - (im[0].size[1]*2+self.__Gap)/2))
        tubeH = int(numpy.ceil(im[0].size[1]*2+self.__Gap+ext*2))

        CData = Image.new('RGBA', (tubeW, tubeH))
        
        imExt = im[0].crop((0,0,im[0].size[0],1))
        for i in range(0,ext):
            CData.paste(imExt,(0,i))
            CData.paste(imExt,(0,tubeH-1-i))
        
        CData.paste(im[0],(0,ext))
        CData.paste(im[1],(0,ext+im[0].size[1]+self.__Gap))

        self.Size = list(CData.size)
        self.XY = [self._Resolution[0]/2+self.Size[0]/2,random.randint(0,self.__Max_VOffset)]
        self._Textures = visual.ImageStim(self._Window,CData,size=self.Size,pos=self.XY,units='pix')
        self.GapRange = [self.XY[1]+self.__Gap/2, self.XY[1]-self.__Gap/2]
    
    def Update(self):
        self.XY[0] -= parameters['Speed']
        if self.XY[0] < -(self._Resolution[0]+self.Size[0])/2:
            self.XY[0] = self._Resolution[0]/2+self.Size[0]/2 + random.randint(0,self.__Max_VOffset)    # shift back to the beginning + jitter
            self.XY[1] = random.randint(0,self.__Max_VOffset)                                           # recalculate VOffset
            self.GapRange = [self.XY[1]+self.__Gap/2, self.XY[1]-self.__Gap/2]
            parameters['nTubesPassed'] += 1                                                             # correct for tubes passed by bird
        
        self._Textures.pos = self.XY
        self._Textures.draw()

