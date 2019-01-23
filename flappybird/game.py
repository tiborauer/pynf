import time, json, os, glob, numpy
from PIL import Image
from psychopy import core, visual, monitors

parameters = {
    'Gravity': 0,
    'Speed': 0,
    'frameNo': 0,
    'FPS': None,
    'nTubesPassed': 0
}

class engine:

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
        'Text_Size': 0.1
    }
    __SIMULATE = True # Use mouse
    __T_BIRDtoTUBE = 15 # sec
    __SHAPING = False
    
    # Game variables
    __dThreshold = 0
    __BestScore = 0

    # Objects
    __Tubes = None
    __Bird = None
    __Feedback = None
    __Log = None
    
    # Low level variables
    __SETTINGS = {
        'FileName': '',
        'Initial': []
    }
    __Window = None
    __Resolution = None
    __Textures = {}
    __ExperimentStart = None
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

        self.__Window = visual.Window(size=self.__Resolution,pos=(posX,posY),monitor=scr,fullscr=doFullscreen,winType='pyglet')

        #glob.glob(os.path.join(os.path.dirname(os.path.realpath(__file__)),'sprites','*.png'))
        # Stage
        t = time.localtime()
        im = Image.open(os.path.join(os.path.dirname(os.path.realpath(__file__)),'sprites','Background' + str((t.tm_hour < self.__DAYTIME[0] or t.tm_hour > self.__DAYTIME[1])+1) + '.png'))
        mag = self.__Resolution[1]/im.size[1]
        im = im.resize((int(mag*im.size[0]), int(mag*im.size[1])),Image.BICUBIC)
        CData = numpy.tile(numpy.array(im),(1,1,int(numpy.ceil(self.__Resolution[0]/im.size[0]))))
        self.__Textures['Background'] = visual.ImageStim(self.__Window,image=CData,size=self.__Resolution)

    def CloseWindow(self):
        self.__Window.close()
        self.__SaveConfig()

    def Update(self):

        self.__Textures['Background'].draw()

        self.__Window.flip()
        core.wait(5)

    def Over(self):
        return True

    def Score(self):
        return 0

    def Clock(self):
        return time.time() - self.__ExperimentStart
    
    def FPS(self):
        return 0

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
        
        self.__SETTINGS['Initial']['BestScore'] = max(self.__BestScore, self.Score())

        if doUpdate:
            for f in ['DISPLAY','DAYTIME','STAGE','SIMULATE','SHAPING','BestScore']:
                self.__SETTINGS['Initial'][f] = getattr(self, f)
        
        with open(self.__SETTINGS['FileName'],'w') as config:
            json.dump(self.__SETTINGS['Initial'],config)
