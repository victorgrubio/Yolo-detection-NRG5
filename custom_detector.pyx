from cython import wraparound, boundscheck
from threading import Thread, Lock
import xml_preprocessing as xml_prep
from datetime import datetime
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
cimport numpy as np

from show_video import launch_stream_hls
from video_queue import VideoQueue
from visual_detector import VisualDetector
from thermal_detector import ThermalDetector
# cython: languague_level='3'
# cython: profile=True


@boundscheck(False)
@wraparound(False)
class CustomDetector():
    """
    Class documentation
    """

    def __init__(self, logger, dirname, args=None):
        """
        Constructor
        """
        self.logger = logger
        self.dirname = dirname
        self.date = datetime.now()
        self.config = self.load_config('cfg/detector.yaml', args)
        self.cap = self.start_capture()
        self.width, self.height = self.check_resize()
        self.detector = self.start_detector()
        self.threads = {}
        self.last_detection = None
        self.video_queue = None
        self.img_orig = None
        self.img_proc = None
        self.video_orig = None
        self.video_proc = None
        self.net = None
        self.video_emission = None
        self.is_running_lock = Lock()
        self.is_running = True
        self.is_stopping_lock = Lock()
        self.is_stopping = False

    @property
    def is_running(self):
        self.is_running_lock.acquire(True)
        val = self.__is_running
        self.is_running_lock.release()
        return val

    @is_running.setter
    def is_running(self, value):
        self.is_running_lock.acquire(True)
        self.__is_running = value
        self.is_running_lock.release()

    @property
    def is_stopping(self):
        self.is_stopping_lock.acquire(True)
        val = self.__is_stopping
        self.is_stopping_lock.release()
        return val

    @is_stopping.setter
    def is_stopping(self, value):
        self.is_stopping_lock.acquire(True)
        self.__is_stopping = value
        self.is_stopping_lock.release()

    def load_config(self, config_file, args=None):
        """
        Load config file
        """
        config = ""
        if os.path.exists(config_file):
            with open(config_file, 'rt') as f:
                config = yaml.safe_load(f.read())
        if args is not None:
            # Remove none elements
            args = {k: v for k, v in args.items() if v is not None}
            config['args'].update(args)
        self.logger.debug('Config {}'.format(config))
        return config

    def start_detector(self):
        """
        Start detector
        """
        if self.config['args']['video_path'] is not None \
                and self.config['args']['droneid'] is not None:
            self.logger.error(
                'Can not analyze stored video and drone live video '
                'at the same time')
            sys.exit(1)
        self.logger.info('CAM: {}'.format(self.config['args']['camera']))
        fps_rate = self.config[self.config['args']['camera']]['input_fps_rate']
        # deploy the deep neural network
        detector = None
        if self.config['args']['camera'] == 'visual':
            detector = VisualDetector(self.logger, self.dirname, self.config, self)
        elif self.config['args']['camera'] == 'thermal':
            detector = ThermalDetector(self.logger, self.config, self)
        return detector

    def start_thread(self, daemon=False):
        """
        Start detection thread
        """
        self.logger.info('Starting video thread')
        thread = Thread(target=self.process_video, args=())
        thread.daemon = daemon
        thread.start()
        self.threads['detection_thread'] = thread
        return self

    def get_video_path(self):
        """
        Method documentation
        """
        video_address = ''
        if self.config['args']['droneid'] is not None:
            if 'tcp:' in self.config['args']['droneid']:
                drone_ip = self.config['args']['droneid'].split(':')[1]
            else:
                # remove points from ip to avoid errors
                drone_ip = self.config['args']['droneid']
            video_address = ':'.join(
                ['http', '//' + str(drone_ip),
                 str(self.config['drone']['stream_port'])])
        elif self.config['args']['video_path'] is not None:
            video_address = self.config['args']['video_path']
        return video_address

    def start_capture(self):
        """
        Method documentation
        """
        video_address = self.get_video_path()
        cap = cv2.VideoCapture(video_address)
        return self.cap_resize(cap)

    def check_resize(self):
        """
        Get final width, height
        """
        cdef int width = int(self.cap.get(3))
        cdef int height = int(self.cap.get(4))
        if width > self.config['video']['max_width']:
            if width is not int(self.config['video']['resized_width']):
                width = self.config['video']['resized_width']
            if height is not int(self.config['video']['resized_height']):
                height = self.config['video']['resized_height']
        return width, height

    def cap_resize(self, cap):
        """
        Check if resize is needed due to video dims
        """
        cdef float width = cap.get(3)
        cdef float height = cap.get(4)
        if width > self.config['video']['max_width']:
            width = self.config['video']['resized_width']
            height = self.config['video']['resized_height']
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.logger.info('Image size: {}x{}'.format(cap.get(3), cap.get(4)))
        return cap

    def start_broadcast(self):
        """
        Broadcasting process initialization
        """
        host = self.config['broadcast']['host']
        port = self.config['broadcast']['port']
        protocol = "udp" if self.config["args"]["disable_alerts"] else "http"
        self.logger.info('Streaming fps: {}'.format(float(
            self.config[self.config['args']['camera']]['stream_fps_rate'])))
        self.logger.info('Start broadcast')
        vid = ''
        if vid is None:  # no droneid, assume uploaded video
            vid = self.config['args']['video_path'].split('_')[1]
        elif self.config['args']['droneid'] is not None:
            if 'tcp:' in self.config['args']['droneid']:
                vid = self.config['args']['droneid'].split(':')[1]
                host = '127.0.0.1'
            else:
                # remove points from ip to avoid errors
                vid = ''.join(self.config['args']['droneid'].split('.'))
        #======================================================================
        # stream_address = 'http://%s:%d/%s/%s/%d/%d' % (
        #     host, port, vid, self.config['args']['camera'],
        #     self.width, self.height)
        #======================================================================
        stream_address = '%s://%s:%d/%s/%s' % (
            protocol, host, port, vid, self.config['args']['camera'])
        command = ['ffmpeg',
                   '-f', 'rawvideo',
                   '-s', '%dx%d' % (self.width, self.height),
                   '-pix_fmt', 'bgr24',
                   '-r', str(
                       self.config[
                           self.config['args']['camera']]['stream_fps_rate']),
                   '-i', '-',
                   '-an',
                   '-vcodec', 'mpeg1video',
                   '-b:v', '700k',
                   '-pix_fmt', 'yuv420p',
                   '-bf', '0',
                   '-f', 'mpegts',
                   stream_address]

        self.logger.info('Streaming has started on address: {}'.format(
            stream_address))
        process = subprocess.Popen(command, stdin=subprocess.PIPE)
        return process

    def start_broadcast_hls(self):
        """
        Broadcasting process initialization
        """
        # host = '192.168.0.35'  # for IP stream
        host = '192.168.23.78'
        port = 1935
        self.logger.info('Streaming fps: {}'.format(float(
            self.config[self.config['args']['camera']]['stream_fps_rate'])))
        self.logger.info('Start broadcast')
        vid = ''
        if vid is None:  # no droneid, assume uploaded video
            vid = self.config['args']['video_path'].split('_')[1]
        elif self.config['args']['droneid'] is not None:
            if 'tcp:' in self.config['args']['droneid']:
                vid = self.config['args']['droneid'].split(':')[1]
            else:
                # remove points from ip to avoid errors
                vid = ''.join(self.config['args']['droneid'].split('.'))
        #======================================================================
        # stream_address = 'http://%s:%d/%s/%s/%d/%d' % (
        #     host, port, vid, self.config['args']['camera'],
        #     self.width, self.height)
        #======================================================================
        stream_address = 'rtmp://%s:%d/stream/test' % (host, port)
        command_split = ['ffmpeg',
                         '-f', 'rawvideo',
                         '-s', '%dx%d' % (self.width, self.height),
                         '-pix_fmt', 'bgr24',
                         '-i', '-',
                         '-video_size', '%dx%d' % (self.width, self.height),
                         '-an',
                         '-tune', 'zerolatency',
                         '-preset', 'ultrafast',
                         '-vcodec', 'libx264',
                         '-vprofile', 'baseline',
                         '-b:v', '4000k',
                         '-pix_fmt', 'yuv420p',
                         '-f', 'flv',
                         '-y',
                         stream_address]

        self.logger.info('Streaming has started on address: {}'.format(
            stream_address))

        video_stream = subprocess.Popen(
            command_split, stdin=subprocess.PIPE, stderr=subprocess.PIPE,
            stdout=subprocess.PIPE)
        return video_stream

    def start(self):
        """
        Streming on FFMPEG Initialization
        """
        if self.config['args']['broadcast']:
            self.video_emission = self.start_broadcast()
            self.logger.info('Broadcasting has started')

        elif self.config['args']['local_emission']:
            self.video_emission = launch_stream_hls(self.width, self.height,
                                                    self.config['hls'])
            self.logger.info('LAN streaming has started')

        if self.config['args']['save_video']:
            # Define the codec and create VideoWriter object
            video_proc_name = "videos/{:%H%M_%d%m%y}_processed.avi".format(
                self.date)
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            fps_rate = self.config['video']['record_fps']
            self.logger.info('Processed video dims: {}x{}'.format(
                self.height, self.width))
            self.video_proc = cv2.VideoWriter(
                video_proc_name, fourcc, fps_rate, (self.width, self.height))

        if self.config['args']['save_video_orig']:
            video_name = "videos/{:%H%M_%d%m%y}.avi".format(self.date)
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            self.logger.info('Original video dims: {}x{}'.format(
                self.height, self.width))
            self.video_orig = cv2.VideoWriter(video_name, fourcc, fps_rate,
                                              (self.width, self.height))
        self.start_thread()

    def process_video(self):
        """
        Main processing method. Start video thread and begin the detections
        """
        self.video_queue = VideoQueue(
            self.logger, queue_size=self.config[
                self.config['args']['camera']]['queue_size'],
            path=self.get_video_path(), fps=self.config[
                self.config['args']['camera']]['input_fps_rate'])
        self.video_queue.start()
        if self.config['args']['display']:
            cv2.namedWindow('detection', cv2.WINDOW_NORMAL)
        while self.is_running:
            if self.video_queue.empty():
                # self.logger.debug('Empty queue')
                time.sleep(0.001)
                continue
            try:
                if self.video_queue.is_running:
                    # If there is any img in queue
                    img = self.video_queue.get()
                    # If img exists
                    if type(img) is np.ndarray:
                        start_time = time.time()
                        self.process_img(img)
                    else:
                        break
                    # Write image on streaming feed
                    if self.config['args']['broadcast'] or \
                            self.config['args']['local_emission']:
                        self.video_emission.stdin.write(
                            self.img_proc.tobytes())
                    # Save processed video
                    if self.config['args']['save_video'] and \
                            self.video_proc is not None:
                        self.video_proc.write(self.img_proc)
                    # Save original video
                    if self.config['args']['save_video_orig'] and \
                            self.video_orig is not None:
                        self.video_orig.write(self.img_orig)
                    # Show image on window
                    if self.config['args']['display']:
                        cv2.imshow('detection', self.img_proc)
                        k = cv2.waitKey(1)
                        if k == 0xFF & ord("q"):
                            break
            except KeyboardInterrupt:
                self.logger.warn('KeyboardInterrupt')
                self.logger.error(traceback.format_exc())
                self.finalize()
                sys.exit(1)
            except BrokenPipeError:
                self.logger.error('BrokePipeError')
                self.logger.error(traceback.format_exc())
                self.finalize()
                sys.exit(2)
            except Exception:
                self.logger.error("\n".join([
                    'Exception', traceback.format_exc()]))
                self.finalize()
                sys.exit(3)
        self.finalize()
        self.logger.debug('Cap closed')
        sys.exit(0)

    def process_img(self, img):
        """
        Perform detection on an image
        """
        try:
            for shape_orig, shape_def in zip(
                    list(img.shape), [self.height, self.width, 3]):
                if shape_orig != shape_def:
                    img_res = cv2.resize(img, (self.width, self.height),
                                         interpolation=cv2.INTER_CUBIC)
                    self.img_orig = img_res
                    break
            else:
                self.img_orig = img
            self.img_proc = self.detector.predict_img(self.img_orig.copy())
        except Exception:
            self.logger.error(
                "\n".join(["Exception has occured on process_img",
                           traceback.format_exc()]))

    def finalize(self):
        """
        End detection thread
        """
        self.logger.info('Video detection has finished')
        if self.config['args']['save_video']:
            self.video_proc.release()
        if self.config['args']['broadcast'] or \
                self.config['args']['local_emission']:
            self.logger.info("Quitting broadcast..")
            self.video_emission.stdin.close()
            self.video_emission.wait()
        if self.config['args']['save_video'] and self.video_proc is not None:
            self.video_proc.release()
        if self.config['args']['save_video_orig'] \
                and self.video_orig is not None:
            self.video_orig.release()
        self.video_queue.is_running = False
        self.video_queue.finalize()
