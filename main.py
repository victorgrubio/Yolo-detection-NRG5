# -*- coding: utf-8 -*-
# @Author: Victor Garcia
# @Date:   2018-10-04 10:31:05
# @Last Modified by:   Victor Garcia
# @Last Modified time: 2019-03-17 16:52:46
import logging
import os
import argparse
from setupLogging import setupLogging
import pyximport
import cv2
pyximport.install()
from custom_detector import CustomDetector

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('-v', '--video_path', help='Path of video')
    parser.add_argument('-i', '--image_path', help='Path of image')
    parser.add_argument('-id', '--droneid', help='drone id')
    parser.add_argument(
        '-cam', '--camera', help='camera type (visual|thermal)', required=True)
    parser.add_argument(
        '-d', '--display', help='Show detection images',
        action='store_true', default=None)
    parser.add_argument(
        '-b', '--broadcast', help='broadcast processed video',
        action='store_true', default=None)
    parser.add_argument(
        '-l', '--local_emission', help='broadcast processed video',
        action='store_true', default=None)
    parser.add_argument(
        '-s', '--save_video', help='save processed video',
        action='store_true', default=None)
    parser.add_argument(
        '--save_video_orig', help='Save original streaming',
        action='store_true', default=None)
    parser.add_argument(
        '--disable_alerts', help='Disable NDMWS Alerts',
        action='store_true', default=None)
    parser.add_argument(
        '--xml', help='broadcast processed video',
        action='store_true', default=None)
    parser.add_argument(
        '--web', help='Show processing on web',
        action='store_true', default=None)
    args = vars(parser.parse_args())

    logger = logging.getLogger(__name__)
    setupLogging()
    dirname = os.path.dirname(os.path.abspath(__file__))
    detector = CustomDetector(logger, dirname, args)

    if args['image_path'] is not None:
        detector.process_img(cv2.imread(args['image_path']))
    else:
        try:
            detector.start()
        except KeyboardInterrupt:
            detector.finalize()
