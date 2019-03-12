from pyniexp.connection import Tcp
from pyniexp import utils
from re import search, match
from datetime import date
import os, numpy, pydicom
from scipy.linalg import null_space
from numpy.linalg import det

class Header:

    def __init__(self):
        self.AcquisitionMatrix = None
        self.NumberOfImagesInMosaic = None
        self.PixelSpacing = None
        self.SpacingBetweenSlices = None
        self.ImagePositionPatient = None
        self.ImageOrientationPatient = None
        self.Columns = None
        self.Rows = None
        self.SliceNormalVector = None
    
    @property
    def is_ready_for_parsing(self):
        return all([not(v is None) for v in list(self.__dict__.values())])
    
    def update(self,hdr):
        for f in list(self.__dict__.keys()):
            if (getattr(self,f) is None) and hasattr(hdr,f):
                setattr(self,f,getattr(hdr,f))

    def parse(self):
    #   Based on spm_dicom_convert Id 6190 2014-09-23 16:10:50Z guillaume $
    #       by John Ashburner & Jesper Andersson
    #       Part of SPM by Wellcome Trust Centre for Neuroimaging

        # Resolution
        self.Dimensions = self.AcquisitionMatrix + [self.NumberOfImagesInMosaic]
        self.PixelDimensions = self.PixelSpacing + [self.SpacingBetweenSlices]

        # Transformation matrix
        analyze_to_dicom = numpy.matmul(numpy.concatenate((numpy.concatenate((numpy.diag([1, -1, 1]), numpy.array([0,self.AcquisitionMatrix[1]-1,0]).reshape(-1,1)),axis=1),numpy.array([0, 0, 0, 1]).reshape(1,-1)),axis=0),
            numpy.concatenate((numpy.eye(4,3), numpy.array([-1, -1, -1, 1]).reshape(-1,1)),axis=1))
        
        vox = self.PixelDimensions
        pos = numpy.array(self.ImagePositionPatient).reshape(-1,1)
        orient = numpy.array(self.ImageOrientationPatient).reshape(2,3).transpose()
        orient = numpy.concatenate((orient, null_space(orient.transpose())), axis=1)
        if det(orient)<0: orient[:,2] = -orient[:,2]
        dicom_to_patient = numpy.concatenate((numpy.concatenate((numpy.matmul(orient,numpy.diag(vox)),pos),axis=1),numpy.array([0,0,0,1]).reshape(1,-1)),axis=0)
        truepos = numpy.matmul(dicom_to_patient,numpy.concatenate(((numpy.array([self.Columns,self.Rows])-numpy.array(self.AcquisitionMatrix))/2,numpy.array([0,1]))).reshape(-1,1))
        dicom_to_patient = numpy.concatenate((numpy.concatenate((numpy.matmul(orient,numpy.diag(vox)),truepos[0:3]),axis=1),numpy.array([0,0,0,1]).reshape(1,-1)),axis=0)

        patient_to_tal = numpy.diag([-1, -1, 1,1])

        mat = numpy.matmul(patient_to_tal, dicom_to_patient, analyze_to_dicom)

        if det(numpy.concatenate((numpy.array(self.ImageOrientationPatient).reshape(2,3).transpose(), numpy.array(self.SliceNormalVector).reshape(-1,1)), axis=1))<0:
            mat = numpy.matmul(mat,numpy.concatenate((numpy.concatenate((numpy.eye(3),numpy.array([0,0,-(self.Dimensions[2]-1)]).reshape(-1,1)),axis=1),numpy.array([0,0,0,1]).reshape(1,-1)),axis=0))

        self.mat = mat

class TcpDicom(Tcp):
    
    def __init__(self,port=5677,control_signal=[0,0]):
        super().__init__(port=port,control_signal=control_signal,encoding='latin-1') 
        
        self.header = Header()
        self.watch_dir = ''

    def set_header_from_Dicom(self,data):
        self.watch_dir = data['watch']
        self.Dicom_last_name = data['LastName']
        self.Dicom_ID = data['ID']

    def receive_initial(self,hdr=None):
        if hdr is None:
            data = self.receive_data(n=2,dtype='uint')
            hdr = self.receive_data(n=data[0],dtype='str').split('\n')
        
        t = get_header_data(hdr,'ParamLong."NImageLins"') + get_header_data(hdr,'ParamLong."NImageCols"')
        t = [int(i) for i in t if not(i is None)]
        if len(t) == 2: self.header.AcquisitionMatrix = t

        t = get_header_data(hdr,'ParamDouble."RoFOV"') + get_header_data(hdr,'ParamDouble."PeFOV"')
        t = [int(i) for i in t if not(i is None)]
        if len(t) == 2: self.header.PixelSpacing = [t[i]/self.header.AcquisitionMatrix[i] for i in range(0,2)]

    def receive_scan(self,hdr=None,img=None):
        # Acquire
        if hdr is None or img is None:
            data = self.receive_data(n=2,dtype='uint')
            hdr = self.receive_data(n=data[0],dtype='str').split('\n')
            img = self.receive_data(n=int(data[1]/2),dtype='ushort')
        
        # Header
        if not(self.header.is_ready_for_parsing):
            t = get_header_data(hdr,'DICOM.ImagesInMosaic')[0]
            if not(t is None): self.header.NumberOfImagesInMosaic = int(t)
            t = get_header_data(hdr,'DICOM.SpacingBetweenSlices')[0]
            if not(t is None): self.header.SpacingBetweenSlices = t
            # TODO: ImagePositionPatient # 3x1 --> from file
            t = []
            t += get_header_data(hdr,'RowVec.dSag')
            t += get_header_data(hdr,'RowVec.dCor')
            t += get_header_data(hdr,'RowVec.dTra')
            t += get_header_data(hdr,'ColumnVec.dSag')
            t += get_header_data(hdr,'ColumnVec.dCor')
            t += get_header_data(hdr,'ColumnVec.dTra')
            if not(any([i is None for i in t])): self.header.ImageOrientationPatient = t
            t = get_header_data(hdr,'DICOM.NoOfCols')[0]
            if not(t is None): self.header.Columns = int(t)
            t = get_header_data(hdr,'DICOM.NoOfRows')[0]
            if not(t is None): self.header.Rows = int(t)
            t = get_header_data(hdr,'DICOM.SlcNormVector',multiple=True)
            if not(any([i is None for i in t])): self.header.SliceNormalVector = t
            t = get_header_data(hdr,'DICOM.MosaicRefAcqTimes',multiple=True)
            if not(any([i is None for i in t])): self.header.SliceTimes = t

            if not(self.header.is_ready_for_parsing) and len(self.watch_dir): 
                folder = os.path.join(self.watch_dir,'{}.{}.{}'.format(date.today().strftime('%Y%m%d'),self.Dicom_last_name,self.Dicom_ID))
                while True:
                    flist = [f for f in os.listdir(folder) if match(r'.*_.*_[0-9]{6}.dcm',f)]
                    if len(flist) != 0:
                        dat = flist[0].split('_')
                        subject = int(dat[0])
                        session = int(dat[1])
                        break
                dcm_file = os.path.join(folder,'{:03d}_{:06d}_{:06d}.dcm'.format(subject,session,1))
                while os.stat(dcm_file).st_size < 180*1024: pass # 180kB header
                self.header.update(pydicom.read_file(dcm_file))

            if self.header.is_ready_for_parsing:
                self.header.parse()
        
        # Image
        if len(img) and self.header.is_ready_for_parsing:
            dat = numpy.zeros(self.header.Dimensions)
            mosaic = numpy.array(img).reshape(self.header.Columns,self.header.Rows)
            num_mosaic = numpy.ceil(numpy.sqrt(self.header.Dimensions[2]))
            for s in range(0,self.header.Dimensions[2]):
                nx = int(s % num_mosaic)
                ny = int(numpy.ceil((s+1)/num_mosaic) - 1)
                dat[:,:,s] = numpy.rot90(mosaic[ny*self.header.Dimensions[1]:(ny+1)*self.header.Dimensions[1],nx*self.header.Dimensions[0]:(nx+1)*self.header.Dimensions[0]],-1)
    
            return dat
                
    
# ---------------------------------------- UTILS -------------------------------------
def get_header_data(hdr,field,multiple=False):
    ind = utils.list_find(hdr,field)
    if not(len(ind)): return [None]
    if not(multiple): ind = [ind[0]]

    val = list(); field0 = field
    for i in range(0,len(ind)):
        dat = None
        if len(ind) > 1: field = '{}.{:d}'.format(field0,i)
        else: field = field0
        t = search(field +' = ([-+]?[0-9]*\.?[0-9]*)',hdr[ind[i]])
        if t is None: t = search('<'+ field +'>  { ([-+]?[0-9]*\.?[0-9]*)  }',hdr[ind[i]]) # intro header v1
        if t is None: t = search('<'+ field +'>  { <Precision> 16  ([-+]?[0-9]*\.?[0-9]*)  }',hdr[ind[i]]) # intro header v2
        if not(t is None): 
            dat = float(t.groups(1)[0])
        val.append(dat)
    return val