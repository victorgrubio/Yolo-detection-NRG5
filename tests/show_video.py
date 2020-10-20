# -*- coding: utf-8 -*-
import os
import sys
import argparse
import cv2
import subprocess
import time


def launch_stream_multihls():
    input_ffmpeg = "ffmpeg -f rawvideo -s 640x480 -pix_fmt bgr24 -r 25 -i - -an -f hls"
    input_360 = "-vf scale=w=480:h=360:force_original_aspect_ratio=decrease -hls_time 4 -hls_wrap 10 -hls_flags -delete_segments -tune zerolatency -preset ultrafast -c:v libx264 -crf 20 -sc_threshold 0 -g 48 -keyint_min 48 -b:v 800k -maxrate 856k -bufsize 1200k -pix_fmt yuv420p -hls_segment_filename www/videos/360p_%03d.ts www/videos/360p.m3u8"
    input_480 = "-vf scale=w=640:h=480:force_original_aspect_ratio=decrease -hls_time 4 -hls_wrap 10 -hls_flags -delete_segments -tune zerolatency -preset ultrafast -c:v libx264 -crf 20 -sc_threshold 0 -g 48 -keyint_min 48 -b:v 1400k -maxrate 1498k -bufsize 2100k -pix_fmt yuv420p -hls_segment_filename www/videos/480p_%03d.ts www/videos/480p.m3u8"
    input_720 = "-vf scale=w=960:h=720:force_original_aspect_ratio=decrease -hls_time 4 -hls_wrap 10 -hls_flags -delete_segments -tune zerolatency -preset ultrafast -c:v libx264 -crf 20 -sc_threshold 0 -g 48 -keyint_min 48 -b:v 2800k -maxrate 2996k -bufsize 4200k -pix_fmt yuv420p -hls_segment_filename www/videos/720p_%03d.ts www/videos/720p.m3u8"
    input_1080 = "-vf scale=w=1440:h=1080:force_original_aspect_ratio=decrease -hls_time 4 -hls_wrap 10 -hls_flags -delete_segments -tune zerolatency -preset ultrafast -c:v libx264 -crf 20 -sc_threshold 0 -g 48 -keyint_min 48 -b:v 5000k -maxrate 5350k -bufsize 7500k -pix_fmt yuv420p -hls_segment_filename www/videos/1080p_%03d.ts www/videos/1080p.m3u8"
    command = " ".join(
        [input_ffmpeg, input_360, input_480, input_720, input_1080])
    command_split = command.split(' ')
    FNULL = open(os.devnull, 'w')
    video_stream = subprocess.Popen(
        command_split, stdin=subprocess.PIPE, stdout=FNULL,
        stderr=subprocess.STDOUT)
    return video_stream


def launch_stream_hls(width, height, dict_hls="", video_input='-'):
    if dict_hls is None or type(dict_hls) != dict:
        dict_hls = {
            'fps': 10, 'min_rate': 3, 'max_rate': 3.5, 'buffer_rate': 1.5,
            'hls_time': 4, 'num_ts': 4, 'threads': 4,
            'stream_address': 'index.m3u8'}
    min_bitrate = int((dict_hls['min_rate'] * width * height) / 1000)
    max_bitrate = int((dict_hls['max_rate'] * width * height) / 1000)
    buffer_size = int(dict_hls['buffer_rate'] * min_bitrate)
    command = 'ffmpeg -f rawvideo -threads {} -s {}x{} -pix_fmt bgr24 -r {} -i {} -an -f hls -hls_time {} -g {} -hls_wrap {} -hls_segment_filename www/videos/hls_stream_%03d.ts -hls_flags -delete_segments -tune zerolatency -preset ultrafast -vcodec libx264 -b:v {}k -maxrate {}k -bufsize {}k -pix_fmt yuv420p -y {}'.format(
        dict_hls['threads'], width, height, dict_hls['fps'], video_input, dict_hls['hls_time'], dict_hls['hls_time'],
        dict_hls['num_ts'], min_bitrate, max_bitrate, buffer_size, dict_hls['stream_address'])
    FNULL = open(os.devnull, 'w')
    video_stream = subprocess.Popen(
        command.split(), stdin=subprocess.PIPE, stdout=FNULL,
        stderr=subprocess.STDOUT)
    return video_stream


def launch_stream_ffmpeg(width, height):
    stream_address = 'test.mp4'
    command_split = ['ffmpeg',
                     '-f', 'rawvideo',
                     '-s', '%dx%d' % (width, height),
                     '-pix_fmt', 'bgr24',
                     '-re',
                     '-i', '-',
                     '-an',
                     '-b:v', '512k',
                     '-bf', '0',
                     '-vcodec', 'mpeg4',
                     '-tune', 'zerolatency',
                     '-pix_fmt', 'yuv420p',
                     '-preset', 'ultrafast',
                     '-y',
                     stream_address]

    video_stream = subprocess.Popen(
        command_split, stdin=subprocess.PIPE, stderr=subprocess.PIPE,
        stdout=subprocess.PIPE)
    return video_stream


def launch_stream_rtmp(width, height):
    stream_address = 'rtmp://192.168.23.78:1935/stream/test'
    command_split = ['ffmpeg',
                     '-f', 'rawvideo',
                     '-s', '%dx%d' % (width, height),
                     '-pix_fmt', 'bgr24',
                     '-i', '-',
                     '-video_size', '%dx%d' % (width, height),
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

    video_stream = subprocess.Popen(
        command_split, stdin=subprocess.PIPE, stderr=subprocess.PIPE,
        stdout=subprocess.PIPE)
    return video_stream


def launch_stream_vlc():
    command = 'cvlc --demux=rawvideo --rawvid-fps=25 --rawvid-width=640 --rawvid-height=480 - --sout "#transcode{vcodec=h264,vb=512,fps=25,width=640,height=480}:rtp{dst=localhost,port=8090,sdp=rtsp://localhost:8090/test.sdp}'
    command = "cvlc v4l2:///dev/video0 --sout '#transcode{vcodec=h264,vb=512}:standard{access=http,mux=ts,dst=:8081}'"
    command = 'cvlc --demux=rawvideo --rawvid-fps=30 --rawvid-width=640 --rawvid-height=480 --rawvid-chroma=RV24 - --sout "#transcode{vcodec=h264,vb=512,fps=30,width=640,height=480}:standard{access=http{mime=video/x-flv},mux=ffmpeg{mux=flv},dst=:8090/stream.flv}"'
    command = 'cvlc --demux=rawvideo --rawvid-fps=30 --rawvid-width=640 --rawvid-height=480 --rawvid-chroma=RV24 - --sout "#transcode{vcodec=h264,vb=512,fps=30,width=640,height=480}:standard{access=http,mux=ts,dst=:8090}"'
    command_split = command.split(' ')
    video_stream = subprocess.Popen(
        command_split, stdin=subprocess.PIPE, stderr=subprocess.PIPE,
        stdout=subprocess.PIPE)
    return video_stream


def launch_stream_udp(width, height, args):
    stream_address = 'udp://{}:{}'.format(args['host'], args['port'])
    command = "ffmpeg -f rawvideo -s 640x480 -pix_fmt bgr24 -r 25 -i - -an -f mpegts {}".format(stream_address)
    FNULL = open(os.devnull, 'w')
    video_stream = subprocess.Popen(command.split(), stdin=subprocess.PIPE, stdout=FNULL, stderr=subprocess.STDOUT)
    return video_stream



if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-v', '--video', help='Video Path to stream', required=True)
    parser.add_argument('--stream', help='Stream video to port', type=str)
    parser.add_argument('--host', help='Host of stream',
                        type=str, default='localhost')
    parser.add_argument('--port', help='Port of stream',
                        type=str, default='8081')
    parser.add_argument('--display', help='Show CV window',
                        action='store_true')
    args = vars(parser.parse_args())

    if args['video'] in ["0", "1", "2"]:
        cap = cv2.VideoCapture(int(args['video']))
    else:
        cap = cv2.VideoCapture(args['video'])
    stream = None

    if args['display']:
        cv2.namedWindow('{}'.format(args.video))
    if args['stream'] == 'multihls':
        stream = launch_stream_multihls(int(cap.get(3)), int(cap.get(4)))
    elif args['stream'] == 'hls':
        cap.set(3, 854)
        cap.set(4, 480)
        stream = launch_stream_hls(int(cap.get(3)), int(cap.get(4)))
    elif args['stream'] == 'rtmp':
        stream = launch_stream_rtmp(int(cap.get(3)), int(cap.get(4)))
    elif args['stream'] == 'udp':
        stream = launch_stream_udp(int(cap.get(3)), int(cap.get(4)), args)

    while(True):
        try:
            # Capture frame-by-frame
            ret, frame = cap.read()
            if ret:
                if args['display']:
                    cv2.imshow('{}'.format(args.video), frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break

                if args['stream']:
                    stream.stdin.write(frame.tobytes())
            else:
                print('ret: {}'.format(ret))
                time.sleep(1)
                continue

        except KeyboardInterrupt:
            print('User finished using CTRL+C')
            stream.stdin.close()
            stream.wait()
            break

        except Exception as e:
            print("Exception: {}".format(e))

        except:
            print("Unexpected error:", sys.exc_info()[0])

    cv2.destroyAllWindows()
    stream.stdin.close()
    stream.wait()
    cap.release()
