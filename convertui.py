__author__ = 'wuxiaoyu'

# Use the following mayapy pyside-uic script if you want to convert a .ui file that originates from Qt Designer into Python code:
import sys, pprint
from pysideuic import compileUi
pyfile = open("./qltoolboxui.py", 'w')
compileUi("./qltoolbox.ui", pyfile, False, 4,False)
pyfile.close()