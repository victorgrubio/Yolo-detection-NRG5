# -*- coding: utf-8 -*-
# @Author: Victor Garcia
# @Date:   2018-10-04 10:33:53
# @Last Modified by:   Victor Garcia
# @Last Modified time: 2019-02-05 12:24:39

from distutils.core import setup
from Cython.Build import cythonize
import os
from shutil import copyfile
from difflib import ndiff

# Cython files that will be compiled and main
dirname  = os.path.dirname(os.path.abspath(__file__))+'/'
pyx_files = [dirname+"*.pyx"]
py_files  = [dirname+"main.py"]
release_folder = dirname+'release/'

#Compile cython files
setup(
    ext_modules = cythonize( pyx_files ),#annotate=True #enables generation html file
)

#Remove .c files and build directory after setup the .so files
files = os.listdir(dirname)
c_cpython_files = [file for file in files if ".c" in file] #.c and .cpython ... .so files
cpython_files = [file for file in files if ".cpython" in file] #.so files only

#Move compiled files to release folder.Also utils,main
if not os.path.isdir(release_folder):
    os.makedirs(release_folder)

#Copy .so and .py files
for file in cpython_files+py_files:
    filename = os.path.basename(file)
    release_filename = release_folder+filename
    #If both are the same file, catch exception.
    #Updates release file. Needed due to error on update process
    try:
        copyfile(file,release_filename)
    except:
        os.remove(release_filename)
        copyfile(file,release_filename)
        pass

#Remove .so and .c files in main folder
for file in c_cpython_files:
    if "pydarknet" in file:
        continue
    else:
        os.remove(dirname+file)
        print("file:",file,"has been removed")
