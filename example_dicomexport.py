from pynf.dicomexport import TcpDicom

rtd = TcpDicom()
data = {
    'watch':r'C:\RT\rt',
    'LastName':'TEST_SUBJECT',
    'ID': 'RH'
}
rtd.set_header_from_Dicom(data)
rtd.open_as_server()
rtd.receive_initial()
dat = rtd.receive_scan()