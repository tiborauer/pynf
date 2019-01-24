import numpy
import scipy.optimize as opt
import matplotlib.pyplot as plt

class Converter:

    __MaxAct = 100
    __Steps = 21
    __halfPlateau = 20

    __Slope = 0
    __Distance = 0   # Distance between slopes

    def __init__(self,*args): # maxAct, step, halfPlateau
        if len(args):
            self.__MaxAct = args[0]
            self.__Steps = args[1]
            self.__halfPlateau = args[2]
        
        self.Calibrate(self.__MaxAct, self.__Steps, self.__halfPlateau)
    
    def Calibrate(self,maxAct,steps,halfPlateau):
        self.__MaxAct = maxAct
        self.__Steps = steps

        # Initial
        self.__Distance = self.__MaxAct + halfPlateau

        # Iteration
        # - ensure that fun(minimum) is rounded to minval
        sl = 0
        while self.__cost_Slope(sl): sl += 1e-4
    
        # - ensure plateau is not larger than specified
        self.__Distance = opt.fminbound(self.__cost_Distance, self.__MaxAct/2, self.__MaxAct*2, args=tuple([halfPlateau]))

    def SetPlateau(self,halfPlateau):
        self.Calibrate(self.__MaxAct, self.__Steps, halfPlateau)
        
    def Transform(self,act):
        return int(numpy.round((self.__Steps-1)/2*self.Functor(act)))

    def Functor(self,x):
        return -1/(1+numpy.exp(self.__Slope*(x-(0-self.__Distance/2))))+1/(1+numpy.exp(-self.__Slope*(x-(0+self.__Distance/2))))

    def getPlateauX(self):
        for x in range(0,self.__MaxAct+1):
            if numpy.round((self.__Steps-1)/2*self.Functor(x)) > 0: break
        return x - 1

    def Show(self):
        act = numpy.arange(-self.__MaxAct,self.__MaxAct,1)
        y1 = [self.Functor(a) for a in act]
        y2 = [self.Transform(a) for a in act]
        fig, ax = plt.subplots(2,1,sharex=True)
        ax[0].plot(act, y1, label='Functor(act)')
        ax[0].set(xlabel='activation (au.)', ylabel='feedback',
            title='MaxAct={}, Steps={}, halfPlateau={}'.format(self.__MaxAct,self.__Steps,self.__halfPlateau))
        ax[0].grid()
        ax[0].legend()

        ax[1].plot(act, y2, label='Transform(act)')
        ax[1].set(xlabel='activation (au.)', ylabel='feedback')
        ax[1].grid()
        ax[1].legend()

        plt.show()

    def __cost_Slope(self,slope):
        self.__Slope = slope
        return abs(numpy.round((self.__Steps-1)/2*self.Functor(-self.__MaxAct)) - -(self.__Steps-1)/2)

    def __cost_Distance(self,dist,halfPlateau):
        self.__Distance = dist
        return abs(self.getPlateauX() - halfPlateau)

#fb = Converter()
#fb.Show()
