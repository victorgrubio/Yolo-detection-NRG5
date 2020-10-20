# -*- coding: utf-8 -*-
# @Author: Victor Garcia
# @Date:   2018-10-04 10:31:05
# @Last Modified by:   Victor Garcia
# @Last Modified time: 2019-03-17 16:52:46
import argparse
import os
import logging
import time
import cv2
from flask import Flask, send_from_directory, Response, render_template
from flask_cors import CORS
from setupLogging import setupLogging
import pyximport
pyximport.install()
from custom_detector import CustomDetector


def create_gunicorn_app():
    flag_detector = True
    app = Flask(__name__, static_folder=os.path.join(os.getcwd(), 'www'))
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
    CORS(app)

#   setup detector
    if flag_detector and 'detector' in app.config:
        logger = logging.getLogger(__name__)
        setupLogging()
        dirname = os.path.dirname(os.path.abspath(__file__))
        detector = CustomDetector(logger, dirname, args=None)
        detector.start()
        app.config['detector'] = detector

    @app.route('/<path:path>')
    def send_static(path):
        return send_from_directory('www/', path)

    @app.route('/')
    def index():
        ip = app.config['detector'].config['video']['stream_ip']
        return render_template('index.html', ip=str(ip))

    @app.after_request
    def add_header(r):
        r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        r.headers["Pragma"] = "no-cache"
        r.headers["Expires"] = "0"
        r.headers["Cache-Control"] = "public, max-age=0"
        return r

    def gen():
        if 'detector' in app.config:
            detector = app.config['detector']
            while True:
                try:
                    img = detector.img_proc
                    _, jpeg = cv2.imencode('.jpg', img)
                    frame = jpeg.tobytes()
                    yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' +
                           frame + b'\r\n\r\n')
                except cv2.error:
                    time.sleep(1)
                    continue

    @app.route('/video_feed')
    def video_feed():
        return Response(gen(),
                        mimetype='multipart/x-mixed-replace; boundary=frame')

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process a video.')
    parser.add_argument('-v', '--video_path', help='Path of video')
    parser.add_argument('-i', '--image_path', help='Path to image')
    parser.add_argument('-id', '--droneid', help='drone id')
    parser.add_argument('-cam', '--camera',
                        help='camera type (visual|thermal) (REQUIRED)',
                        default='visual')
    parser.add_argument('-d', '--display', help='Show detection images',
                        action='store_true')
    parser.add_argument('-b', '--broadcast', help='broadcast processed video',
                        action='store_true')
    parser.add_argument('-l', '--local_emission',
                        help='broadcast processed video', action='store_true',
                        default=True)
    parser.add_argument('-s', '--save_video', help='save processed video',
                        action='store_true')
    parser.add_argument('--save_video_orig', help='Save original streaming',
                        action='store_true')
    parser.add_argument('--disable_alerts', help='Disable NDMWS Alerts',
                        action='store_true')
    parser.add_argument('--xml', help='broadcast processed video',
                        action='store_true')
    parser.add_argument('--mode', type=str,
                        help='mode of detection: empty or all')
    args = vars(parser.parse_args())
    logger = logging.getLogger(__name__)
    setupLogging()

    dirname = os.path.dirname(os.path.abspath(__file__))
    detector = CustomDetector(logger, dirname, args)
    detector.start()
    app = create_gunicorn_app()
    app.config['detector'] = detector
    app.run(host='0.0.0.0')

else:
    app = create_gunicorn_app()
