############################################################################################
#
# The MIT License (MIT)
# 
# TASS Movidius Facenet Classifier
# Copyright (C) 2018 Adam Milton-Barker (AdamMiltonBarker.com)
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
# Title:         TASS Movidius Facenet Classifier
# Description:   Uses the Facenet classifier to classify directory of test images.
# Configuration: required/confs.json
# Last Modified: 2018-08-17
#
# Example Usage:
#
#   $ python3.5 Classifier.py
#
############################################################################################

print("")
print("")
print("!! Welcome to TASS Movidius Facenet Classifier, please wait while the program initiates !!")
print("")

import os, sys
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

print("-- Running on Python "+sys.version)
print("")

import time,csv,getopt,json, time, cv2
import numpy as np

import JumpWayMQTT.Device as JWMQTTdevice
from tools.Helpers import Helpers
from tools.OpenCV import OpenCVHelpers as OpenCVHelpers
from tools.Facenet import FacenetHelpers

from mvnc import mvncapi as mvnc
from skimage.transform import resize
from datetime import datetime

print("-- Imported Required Modules")

class Classifier():

    def __init__(self):

        self._configs = {}
        self.movidius = None
        self.jumpwayClient = None

        self.graphfile = None
        self.graph = None

        self.CheckDevices()
        self.Helpers = Helpers()
        self._configs = self.Helpers.loadConfigs()
        self.loadRequirements()
        self.startMQTT()

        print("")
        print("-- Classifier Initiated")
        print("")

    def CheckDevices(self):

        #mvnc.SetGlobalOption(mvnc.GlobalOption.LOGLEVEL, 2)
        devices = mvnc.EnumerateDevices()
        if len(devices) == 0:
            print('!! WARNING! No Movidius Devices Found !!')
            quit()

        self.movidius = mvnc.Device(devices[0])
        self.movidius.OpenDevice()

        print("-- Movidius Connected")

    def allocateGraph(self,graphfile):

        self.graph = self.movidius.AllocateGraph(graphfile)

    def loadRequirements(self):

        print(self._configs["ClassifierSettings"]["NetworkPath"] + self._configs["ClassifierSettings"]["Graph"])

        with open(self._configs["ClassifierSettings"]["NetworkPath"] + self._configs["ClassifierSettings"]["Graph"], mode='rb') as f:

            self.graphfile = f.read()

        self.allocateGraph(self.graphfile)

        print("-- Allocated Graph OK")

    def startMQTT(self):

        try:

            self.jumpwayClient = JWMQTTdevice.DeviceConnection({
                "locationID": self._configs["IoTJumpWay"]["Location"],
                "zoneID": self._configs["IoTJumpWay"]["Zone"],
                "deviceId": self._configs["IoTJumpWay"]["Device"],
                "deviceName": self._configs["IoTJumpWay"]["DeviceName"],
                "username": self._configs["IoTJumpWayMQTT"]["MQTTUsername"],
                "password": self._configs["IoTJumpWayMQTT"]["MQTTPassword"]
            })

        except Exception as e:
            print(str(e))
            sys.exit()

        self.jumpwayClient.connectToDevice()

        print("-- IoT JumpWay Initiated")

Classifier = Classifier()
FacenetHelpers = FacenetHelpers()

def main(argv):

    humanStart = datetime.now()
    clockStart = time.time()

    print("-- FACENET TEST MODE STARTING ")
    print("-- STARTED: ", humanStart)
    print("")

    validDir    = Classifier._configs["ClassifierSettings"]["NetworkPath"] + Classifier._configs["ClassifierSettings"]["ValidPath"]
    testingDir  = Classifier._configs["ClassifierSettings"]["NetworkPath"] + Classifier._configs["ClassifierSettings"]["TestingPath"]

    files = 0
    identified = 0

    for test in os.listdir(testingDir):
        
            if test.endswith('.jpg') or test.endswith('.jpeg') or test.endswith('.png') or test.endswith('.gif'):
                #print(testingDir+test)

                test_output = FacenetHelpers.infer(cv2.imread(testingDir+test), Classifier.graph)
                files = files + 1

                for valid in os.listdir(validDir):

                        if valid.endswith('.jpg') or valid.endswith('.jpeg') or valid.endswith('.png') or valid.endswith('.gif'):

                            valid_output = FacenetHelpers.infer(cv2.imread(validDir+valid), Classifier.graph)

                            if (FacenetHelpers.match(valid_output, test_output)):
                                identified = identified + 1
                                print("-- MATCH "+test)
                                print("")

                                Classifier.jumpwayClient.publishToDeviceChannel(
                                    "Warnings",
                                    {
                                        "WarningType":"CCTV",
                                        "WarningOrigin": Classifier._configs["Cameras"][0]["ID"],
                                        "WarningValue": "RECOGNISED",
                                        "WarningMessage":test.rsplit( ".", 1 )[ 0 ]+" Detected"
                                    }
                                )
                                break
                            else:
                                
                                print("-- NO MATCH")
                                print("")

                                Classifier.jumpwayClient.publishToDeviceChannel(
                                    "Warnings",
                                    {
                                        "WarningType":"CCTV",
                                        "WarningOrigin": Classifier._configs["Cameras"][0]["ID"],
                                        "WarningValue": "INTRUDER",
                                        "WarningMessage":"INTRUDER"
                                    }
                                )

    humanEnd = datetime.now()
    clockEnd = time.time()

    print("")
    print("-- FACENET TEST MODE ENDING")
    print("-- ENDED: ", humanEnd)
    print("-- TESTED: ", files)
    print("-- IDENTIFIED: ", identified)
    print("-- TIME(secs): {0}".format(clockEnd - clockStart))
    print("")

    print("!! SHUTTING DOWN !!")
    print("")

    Classifier.graph.DeallocateGraph()
    Classifier.movidius.CloseDevice()

if __name__ == "__main__":

	main(sys.argv[1:])