from pynf.dicomexport import TcpDicom

rtd = TcpDicom()
data = {
    'watch':r'C:\RT\rt',
    'LastName':'Test_Subject',
    'ID': 'RHUL'
}
rtd.set_header_from_Dicom(data)
rtd.open_as_server(); rtd.receive_initial()
dat = []
for n in range(0,10): dat.append(rtd.receive_scan())