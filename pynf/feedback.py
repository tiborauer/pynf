import numpy, json
import scipy.optimize as opt
import matplotlib.pyplot as plt
from pyniexp import connection

class Receiver(connection.Udp):

    def __init__(self,IP='127.0.0.1',port=1234,encoding='UTF-8',controlChar='#',**args):
        super().__init__()
        self.ConnectForReceiving()
        self.sendTimeStamp = True
    
    def Signal(self):
        if self.isOpen and self.ReadytoReceive(): return self.ReceiveData(n=1,dtype='float')
        else: return None, None


class Converter:

    MaxAct = 100
    Steps = 21
    __halfPlateau = 20

    @property
    def halfPlateau(self):
        return self.__halfPlateau

    @halfPlateau.setter
    def halfPlateau(self,val):
        self.__halfPlateau = val
        self.Calibrate()

    __Slope = 0
    __Distance = 0   # Distance between slopes

    def __init__(self,maxAct=100,steps=21,halfPlateau=20,**args):
        self.MaxAct = maxAct
        self.Steps = steps
        self.halfPlateau = halfPlateau
        
    def Calibrate(self):
        # Initial
        self.__Distance = self.MaxAct + self.halfPlateau

        # Iteration
        # - ensure that fun(minimum) is rounded to minval
        sl = 0
        while self.__cost_Slope(sl): sl += 1e-4
    
        # - ensure plateau is not larger than specified
        self.__Distance = opt.fminbound(self.__cost_Distance, self.MaxAct/2, self.MaxAct*2, args=tuple([self.halfPlateau]))

    def Transform(self,act):
        return int(numpy.round((self.Steps-1)/2*self.Functor(act)))

    def Functor(self,x):
        return -1/(1+numpy.exp(self.__Slope*(x-(0-self.__Distance/2))))+1/(1+numpy.exp(-self.__Slope*(x-(0+self.__Distance/2))))

    def getPlateauX(self):
        for x in range(0,self.MaxAct+1):
            if numpy.round((self.Steps-1)/2*self.Functor(x)) > 0: break
        return x - 1

    def Show(self):
        act = numpy.arange(-self.MaxAct,self.MaxAct,1)
        y1 = [self.Functor(a) for a in act]
        y2 = [self.Transform(a) for a in act]
        fig, ax = plt.subplots(2,1,sharex=True)
        ax[0].plot(act, y1, label='Functor(act)')
        ax[0].set(xlabel='activation (au.)', ylabel='feedback',
            title='MaxAct={}, Steps={}, halfPlateau={}'.format(self.MaxAct,self.Steps,self.halfPlateau))
        ax[0].grid()
        ax[0].legend()

        ax[1].plot(act, y2, label='Transform(act)')
        ax[1].set(xlabel='activation (au.)', ylabel='feedback')
        ax[1].grid()
        ax[1].legend()

        plt.show()

    def __cost_Slope(self,slope):
        self.__Slope = slope
        return abs(numpy.round((self.Steps-1)/2*self.Functor(-self.MaxAct)) - -(self.Steps-1)/2)

    def __cost_Distance(self,dist,halfPlateau):
        self.__Distance = dist
        return abs(self.getPlateauX() - halfPlateau)
    
    
class Feedback(Converter,Receiver):
    Simulate = True
    Shaping = True
    dThreshold = 0
    __halfPlateau0 = 0

    def __init__(self,config):
        if type(config) == str:
            with open(config) as configfid:
                config = json.load(configfid)['FEEDBACK']
        
        self.__halfPlateau0 = config['halfPlateau']
        self.Simulate = config['Simulate'] == True
        self.Shaping = config['Shaping'] == True

        Converter.__init__(self,**config)
        if not(self.Simulate): Receiver.__init__(self,**config)

    def Value(self,act=None):
        t = None; val = None

        if not(self.Simulate): t, act = self.Signal()
        if not(act is None):
            val = self.Transform(act-self.dThreshold/2)
        
        if self.Shaping:
            if val > 0:
                self.dThreshold = act
                self.halfPlateau = self.__halfPlateau0 + self.dThreshold/2
            elif val < 0:
                self.dThreshold = 0
                if self.halfPlateau != self.__halfPlateau0: self.halfPlateau = self.__halfPlateau0
        
        return t, act, val

#fb = Converter()
#fb.Show()
