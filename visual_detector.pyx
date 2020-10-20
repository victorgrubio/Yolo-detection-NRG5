from show_video import launch_stream_hls
import xml_preprocessing as xml_prep
from my_darknet import MyDarknet
from ndmws import NDMWS
from datetime import datetime
import cython
import math
import numpy as np
import subprocess
import traceback
import yaml
import os
import sys
import cv2
import time
"""
Created on Mon Jan 29 17:25:59 2018

@author: victor

Script which obtains the image predicted
"""
import pyximport
pyximport.install()  # allow .pyx files import
# cython values to speed up numpy arrays
cimport numpy as np


# cython values to speed up numpy arrays
@cython.profile(True)
@cython.boundscheck(False)
@cython.wraparound(False)
class VisualDetector():

    def __init__(self, logger, dirname, config, custom_detector):
        self.logger = logger
        self.dirname = dirname
        self.config = config
        self.custom_detector = custom_detector
        self.net = None
        self.ndmws = None
        self.start()

    def start(self):
        if 'release' in self.dirname:
            self.dirname = os.path.dirname(self.dirname)
        # Load model from config file
        # Load cfg, weights and names files using model defined in config
        model = self.config[self.config['args']['camera']]['model']
        cfg = self.config[model]['cfg']
        weights = self.config[model]['weights']
        names = self.config[model]['data']

        if(os.path.isfile(self.dirname + cfg) and
           os.path.isfile(self.dirname + weights)):
            self.logger.info('Models already downloaded')
        else:
            self.logger.info('Downloading models using script')
            subprocess.call("download_models.sh", shell=True)
        self.net = MyDarknet(self.dirname, cfg, weights, names)
        self.logger.info('Neural Network loaded')

    def predict_img(self, img):
        start_time = time.time()
        # Reshape has been made
        img_proc = self.sliding_window(img)
        self.logger.debug("Detection time: {}".format(
            time.time() - start_time))
        self.logger.debug('Detection on img finished')
        return img_proc

    def sliding_window(self, img):
        """
        Main detection process
        """
        # Init parameters for sliding window process
        cdef int step_x = 1
        cdef int step_y = 1
        cdef int y_elim_div = 0
        # Counters
        cdef int count_x_win = 0
        cdef int count_y_win = 0
        cdef int total_counter = 0
        cdef int counter_id = 0
        # Remove specific section of the image (height)
        if y_elim_div is not 0:
            img = img[:, img.shape[1] //
                      y_elim_div:img.shape[1] -
                      img.shape[1] //
                      y_elim_div, :]
        cdef int window_y = int(img.shape[0] / step_y)
        cdef int window_x = int(img.shape[1] / step_x)

        xml_filename = None
        if self.config['args']['xml']:
            xml_filename = xml_prep.create_xml()

        if step_x == step_y == 1:
            x_win, y_win = 0, 0
            if self.config['args']['xml']:
                counter_id, img = self.detection(counter_id, img, y_win=0,
                                            x_win=0, xml_filename=xml_filename)
            else:
                counter_id, img = self.detection(counter_id, img)
        else:
            start_time = time.time()
            # Sliding window method
            for y_win in range(0, img.shape[0], window_y):
                count_x_win = 0
                count_y_win += 1
                for x_win in range(0, img.shape[1], window_x):
                    count_x_win += 1
                    total_counter += 1
                    window = img[y_win:y_win + window_y,
                                 x_win:x_win + window_x]
                    self.logger.debug('window shape: {}x{}'.format(
                        window_y, window_x))
                    if not xml_filename:
                        counter_id, window = self.detection(counter_id, window,
                                                    y_win=0, x_win=0)
                        img[y_win:y_win + window_y, x_win:x_win + window_x] = window
                        #self.logger.info("Test IMG after draw = {}".format(np.array_equal(test_img, img)))

                    else:
                        counter_id, window = self.detection(
                            counter_id, window, y_win, x_win, xml_filename)
                if self.config['args']['display']:
                    self.logger.debug('\n'.join([
                        'y_win_number: {}'.format(count_y_win),
                        'x_win_number: {}'.format(count_x_win),
                        'total windows: {}'.format(total_counter),
                        'window size: {}x{}'.format(window_x, window_y)]))
                self.logger.debug('Sliding window time {}'.format(
                    time.time() - start_time))
        return img

    def detection(self, counter_id, window,
                  y_win=0, x_win=0, xml_filename=None):
        """
        Apply YOLO detection to current window
        """
        start_time = time.time()
        self.logger.debug('Entering detection')
        cdef int min_score = self.config['visual']['min_score']
        # modify to be relative to image size
        cdef int area_limit = (window.shape[0] * window.shape[1]) / 4
        source = ''
        if self.config['args']['video_path'] is not None:
            source = self.config['args']['video_path'].split('/').pop()
        elif self.config['args']['droneid'] is not None:
            source = self.config['args']['droneid']
        start_time = time.time()
        # dark_img = Image(window)
        # results = self.net.detect(dark_img)
        # del dark_img
        results = self.net.detect(window)
        # Filter results for specific categories
        if self.config['args']['mode'] is not 'all':
            results = self.category_filter(results)
        objects = {}
        self.logger.debug('Entering draw detection loop')
        for cat, score, bounds in results:
            if (score * 100 > min_score):
                x, y, w, h = bounds
                if(h > 0 and w > 0 and math.isfinite(w) and math.isfinite(h)):
                    obj = cat.decode('utf-8')
                    self.logger.debug('{} detected'.format(obj))
                    objects[obj] = 1 if obj not in \
                        objects else objects[obj] + 1
                    window = self.draw_detection(
                        window, x_win, y_win, x, y, w, h, cat, score)
                    if xml_filename is not None:
                        xml_prep.add_detection_xml(
                            xml_filename, counter_id, x_win + int(x),
                            y_win + int(y), w, h, cat, score)
                    counter_id += 1

        if self.config['args']['disable_alerts'] is not True:
            if len(objects) > 0:
                a = []
                for k, v in objects.items():
                    a.append("%d %s" % (v, k + 's' if v > 1 else k))
                    alarm = ', '.join(a)
                    reco = "RECO_PERSON" if "person" in alarm else "RECO_CAR"
                    self.ndmwsAlert(source, reco, alarm)
        self.logger.debug('Individual detection took {} (s)'.format(
            time.time() - start_time))
        self.logger.debug('Exit detection')
        return counter_id, window

    def category_filter(self, results):
        """
        Filter detection to select only relevant categories
        """
        cat_array = self.config['visual']['categories']
        # FILTRO DE CATEGORIAS
        relevants = []
        for element in results:
            # Element[0] = category
            if(str(element[0].decode("utf-8")) in cat_array):
                relevants.append(element)
        return relevants

    def draw_detection(self, img, x_win, y_win, x, y, w, h, cat, score):
        """
        Draw detection on image
        """
#        test_img = img.copy()
#        print("drawing detection")
#        print("Rectangle coordinates {}, {}".format(
#          (x_win + int(x - w / 2), y_win + int(y - h / 2)),
#          (x_win + int(x + w / 2), y_win + int(y + h / 2))
#        ))
        cv2.putText(img, str(cat.decode("utf-8")),
                    (x_win + int(x - w / 2), y_win + int(y - h / 1.9)),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 1)
        cv2.putText(img, str(int(score * 100)),
                    (x_win + int(x + w / 3), y_win + int(y - h / 1.9)),
                    cv2.FONT_HERSHEY_PLAIN, 1, (0, 0, 255), 1)
        # PEOPLE BOUNDING
        cv2.rectangle(img, (x_win + int(x - w / 2), y_win + int(y - h / 2)),
                      (x_win + int(x + w / 2), y_win + int(y + h / 2)),
                      (0, 255, 0), 2)
       # self.logger.info("Test equal after draw = {}".format(np.array_equal(test_img, img)))
        return img

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
                ret = self.ndmws.triggeralarm(reco, t, subplan_time_space, self.config['args']['send_subplan'])
            elif self.config['args']['video_path'] is not None:
                ret = self.ndmws.sendalarm(source, alarm, t)  # it's an uploaded file
        except Exception:
            self.logger.error(traceback.format_exc())
            self.custom_detector.finalize()
