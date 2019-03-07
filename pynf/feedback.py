import numpy, json
import scipy.optimize as opt
import matplotlib.pyplot as plt
from pyniexp import connection

class Receiver(connection.Udp):

    def __init__(self,IP='127.0.0.1',port=1234,encoding='UTF-8',controlChar='#',**args):
        super().__init__()
        self.connect_for_receiving()
        self.sending_time_stamp = True
    
    def signal(self):
        if self.is_open and self.ready_to_receive(): return self.receive_data(n=1,dtype='float')
        else: return None, None


class Converter:

    max_act = 100
    steps = 21
    __half_plateau = 20

    @property
    def half_plateau(self):
        return self.__half_plateau

    @half_plateau.setter
    def half_plateau(self,val):
        self.__half_plateau = val
        self.calibrate()

    __slope = 0
    __distance = 0   # distance between slopes

    def __init__(self,max_act=100,steps=21,half_plateau=20,**args):
        self.max_act = max_act
        self.steps = steps
        self.half_plateau = half_plateau
        
    def calibrate(self):
        # Initial
        self.__distance = self.max_act + self.half_plateau

        # Iteration
        # - ensure that fun(minimum) is rounded to minval
        sl = 0
        while self.__cost_slope(sl): sl += 1e-4
    
        # - ensure plateau is not larger than specified
        self.__distance = opt.fminbound(self.__cost_distance, self.max_act/2, self.max_act*2, args=tuple([self.half_plateau]))

    def transform(self,act):
        return int(numpy.round((self.steps-1)/2*self.functor(act)))

    def functor(self,x):
        return -1/(1+numpy.exp(self.__slope*(x-(0-self.__distance/2))))+1/(1+numpy.exp(-self.__slope*(x-(0+self.__distance/2))))

    def get_plateau_X(self):
        for x in range(0,self.max_act+1):
            if numpy.round((self.steps-1)/2*self.functor(x)) > 0: break
        return x - 1

    def show(self):
        act = numpy.arange(-self.max_act,self.max_act,1)
        y1 = [self.functor(a) for a in act]
        y2 = [self.transform(a) for a in act]
        fig, ax = plt.subplots(2,1,sharex=True)
        ax[0].plot(act, y1, label='Functor(act)')
        ax[0].set(xlabel='activation (au.)', ylabel='feedback',
            title='max_act={}, steps={}, half_plateau={}'.format(self.max_act,self.steps,self.half_plateau))
        ax[0].grid()
        ax[0].legend()

        ax[1].plot(act, y2, label='Transform(act)')
        ax[1].set(xlabel='activation (au.)', ylabel='feedback')
        ax[1].grid()
        ax[1].legend()

        plt.show()

    def __cost_slope(self,slope):
        self.__slope = slope
        return abs(numpy.round((self.steps-1)/2*self.functor(-self.max_act)) - -(self.steps-1)/2)

    def __cost_distance(self,dist,half_plateau):
        self.__distance = dist
        return abs(self.get_plateau_X() - half_plateau)
    
    
class Feedback(Converter,Receiver):
    simulate = True
    shaping = True
    d_threshold = 0
    __half_plateau0 = 0

    def __init__(self,config):
        if type(config) == str:
            with open(config) as configfid:
                config = json.load(configfid)['FEEDBACK']
        
        self.__half_plateau0 = config['half_plateau']
        self.simulate = config['simulate'] == True
        self.shaping = config['shaping'] == True

        Converter.__init__(self,**config)
        if not(self.simulate): Receiver.__init__(self,**config)

    def value(self,act=None):
        t = None; val = None

        if not(self.simulate): t, act = self.signal()
        if type(act) == float:
            val = self.transform(act-self.d_threshold/2)
        
            if self.shaping:
                if val > 0:
                    self.d_threshold = act
                    self.half_plateau = self.__half_plateau0 + self.d_threshold/2
                elif val < 0:
                    self.d_threshold = 0
                    if self.half_plateau != self.__half_plateau0: self.half_plateau = self.__half_plateau0
        
        return t, act, val

#fb = Converter()
#fb.show()
