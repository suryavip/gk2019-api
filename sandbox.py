import os

try:
    os.remove('thereisnofile.xxx')
except:
    print('error')
