# -*- coding: utf-8 -*-
# @Author: Victor Garcia
# @Date:   2019-06-29 17:44:48
# @Last Modified by:   Victor Garcia
# @Last Modified time: 2019-07-01 16:29:38
import os
import subprocess
import argparse
import cv2
import traceback

def launch_stream_rtmp_video(width, height, input_video='-'):
    width = 1680
    height = 1050
    stream_address = 'rtmp://localhost:1935/stream/test'
    command_split = ['ffmpeg',
                     '-i', '/home/visiona/Videos/amazon_webinars/TensorFlow_and_MxNet/tensorflow_and_mxnet_aws_webinar.mkv',
                     '-video_size', '%dx%d' % (width, height),
                     '-an',
                     '-tune', 'zerolatency',
                     '-preset', 'ultrafast',
                     '-vcodec', 'libx264',
                     '-vprofile', 'baseline',
                     '-b:v', '4000k',
                     '-pix_fmt', 'yuv420p',
                     '-f', 'flv',
                     stream_address]
    video_stream = subprocess.Popen(command_split)
    return video_stream

def launch_stream_rtmp(width, height, input_video='-'):
    stream_address = 'rtmp://localhost:1935/stream/test'
    command_split = ['ffmpeg',
                     '-f', 'rawvideo',
                     '-s', '%dx%d' % (width, height),
                     '-pix_fmt', 'bgr24',
                     '-r','10'
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
                     stream_address]
    FNULL = open(os.devnull, 'w')
    video_stream = subprocess.Popen(
        command_split, stdin=subprocess.PIPE, stdout=FNULL,
        stderr=subprocess.STDOUT)
    return video_stream

def launch_stream_hls(width, height, video_input='-'):
    video_folder = "/var/www/html/index.m3u8"
    dict_hls = {
        'fps': 10, 'min_rate': 3, 'max_rate': 3.5, 'buffer_rate': 1.5,
        'hls_time': 4, 'num_ts': 4, 'threads': 4,
        'stream_address': 'index.m3u8'}
    min_bitrate = int((dict_hls['min_rate'] * width * height) / 1000)
    max_bitrate = int((dict_hls['max_rate'] * width * height) / 1000)
    buffer_size = int(dict_hls['buffer_rate'] * min_bitrate)
    command = 'ffmpeg -i {} -s 768x432 -an -f hls -hls_time {} -g {} -hls_wrap {} -hls_segment_filename hls_stream_%03d.ts -hls_flags -delete_segments -tune zerolatency -preset ultrafast -vcodec libx264 -b:v {}k -maxrate {}k -bufsize {}k -pix_fmt yuv420p -y {}'.format(
        video_input, dict_hls['hls_time'], dict_hls['hls_time'], dict_hls['num_ts'],
        min_bitrate, max_bitrate, buffer_size, dict_hls['stream_address'])
    FNULL = open(os.devnull, 'w')
    video_stream = subprocess.Popen(command.split())
    return video_stream

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-v', '--video', help='Video Path to stream', required=True)
    parser.add_argument(
        '--host', help='Host of stream', type=str, default='192.168.23.78')
    parser.add_argument(
        '--port', help='Port of stream', type=str, default='8081')
    parser.add_argument(
        '--display', help='Show CV window', action='store_true')
    parser.add_argument(
        '--stream', action='store_true', default=True)
    args = vars(parser.parse_args())

    if args['video'] in ["0", "1", "2"]:
        cap = cv2.VideoCapture(int(args['video']))
    else:
        cap = cv2.VideoCapture(args['video'])
    stream = launch_stream_rtmp(640, 480)

    
    # stream = launch_stream_rtmp_video(640, 480)
    # args['stream'] = False


    if args['display']:
        cv2.namedWindow('{}:{}'.format(args['host'], args['port']))

    while(True):
        try:
            # Capture img-by-img
            ret, img = cap.read()
            if ret:
                if args['display']:
                    cv2.imshow('{}:{}'.format(args['host'], args['port']), img)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break

                if args['stream']:
                    # img = img.reshape(img.shape[1], img.shape[0], 3)
                    # print(img.shape)
                    # print(img.tostring())
                    # stream.stdin.write(img.tostring())
                    stream.stdin.write(img.tobytes())
            else:
                print('ret: {}'.format(ret))
                continue

        except KeyboardInterrupt:
            print('User finished using CTRL+C')
            stream.stdin.close()
            stream.wait()
            break

        except Exception as e:
            # print('Exception')
            print(traceback.format_exc())
            pass

        except:
            print("Unexpected error:", sys.exc_info()[0])

    cv2.destroyAllWindows()
    stream.stdin.close()
    stream.wait()
    cap.release()