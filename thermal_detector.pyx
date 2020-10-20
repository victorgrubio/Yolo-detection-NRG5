import cv2
cimport numpy as cnp
import numpy as np
import time
import sys
import traceback
import pyximport
from ndmws import NDMWS
pyximport.install()


class ThermalDetector():

    def __init__(self, logger, config, custom_detector):
        self.logger = logger
        self.config = config
        self.ndmws = None
        self.custom_detector = custom_detector

    def predict_img(self, img):
        start_time = time.time()
        img_proc = self.check_thermical_img(img)
        self.logger.debug("Thermical img process time: {}".format(
            time.time() - start_time))
        return img_proc

    def check_thermical_img(self, img):
        # Debemos buscar una acumulación de blancos
        # Processing the img
        hsv_img = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        # con la dimension s de la imgn hsv podemos diferenciar
        # claramente el blanco del resto de colores
        img_proc = hsv_img[:, :, 1]
        img_proc_inv = 255 - img_proc
        img_proc_inv_blur = cv2.GaussianBlur(img_proc_inv, (7, 7), 0)
        ret, img_thresh1 = cv2.threshold(img_proc_inv_blur,
                                         127, 255, cv2.THRESH_TOZERO)
        drawn_img = self.find_contours(img_thresh1, img)
        return drawn_img

    def find_contours(self, img_thresh, img):
        cdef int area_size_threshold = self.get_area_threshold(img)
        img2, contours, hierarchy = cv2.findContours(
            img_thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        valid_contours = [cnt for cnt in contours
                          if cv2.contourArea(cnt) > area_size_threshold]
        for contour in valid_contours:
            x, y, w, h = cv2.boundingRect(contour)
            cv2.rectangle(img, (x, y), (x + w, y + h), (0, 0, 0), 2)
        source = ''
        if self.config['args']['video_path'] is not None:
            source = self.config['args']['video_path'].split('/').pop()
        elif self.config['args']['droneid'] is not None:
            if 'tcp:' in self.config['args']['droneid']:  # localhost
                source = self.config['args']['droneid'].split(':')[1]
            else:
                source = self.config['args']['droneid']
        self.get_alarms(source, valid_contours)
        return img

    def get_area_threshold(self, img):
        val = 300
        return val

    def morph_tranfs(img_thresh, cv2_morph_trans, kernel_size):
        cdef cnp.ndarray kernel = np.ones(kernel_size, np.uint8)
        return cv2.morphologyEx(img_thresh, cv2_morph_trans, kernel)

    def get_alarms(self, source, contours):
        if self.config['args']['disable_alerts'] is not True:
            if len(contours) > 0:
                text = 'dangerously hot region'
                num_zones = len(contours)
                alarm = "%d %s" % (num_zones, text + 's'
                                   if len(contours) > 1 else text)
                reco = "RECO_THERMAL_DANGER"
                self.ndmwsAlert(source, alarm, reco)
                
    def ndmwsAlert(self, source, reco, alarm):
        ''' The 'src' param should be self.droneid if the
            video source comes from a drone live video or the label id (user
            supplied when a video is uploaded.'''
        ret = None
        if self.ndmws is None:
            if self.config['args']['droneid']:
                self.ndmws = NDMWS(
                    inifile='ndmws.ini',
                    droneid=self.config['args']['droneid'])
            else:
                self.ndmws = NDMWS(inifile='ndmws.ini')
        # Send an alarm triggered by the detection algorithm (time gets usec)
        # TODO: get the timestamp FROM THE VIDEO, not from the system
        t = time.time() * 1e3
        # self.logger.info('Alarm in t=%d (%s)' % (t, time.ctime(t / 1e3)))
        # Trigger the proper obj alarm library alarm (see NDMWS) - generates
        # and sends a subplan
        try:
            # TODO: change this with an object to alarm ID as specified in the
            # config file
            if self.config['args']['video_path'] is None and\
               self.config['args']['droneid']:  # it's a drone
                subplan_time_space = self.custom_detector.config['drone']['subplan_time_space']
                print('Go to trigger alarm')
                ret = self.ndmws.triggeralarm(reco, t, subplan_time_space, self.config['send_subplan'])
            elif self.config['args']['video_path'] is not None:
                ret = self.ndmws.sendalarm(source, alarm, t)  # it's an uploaded file
        except Exception:
            self.logger.error(traceback.format_exc())
            self.custom_detector.finalize()