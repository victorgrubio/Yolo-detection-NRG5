#!/bin/bash
cvlc v4l2:///dev/video0 --sout '#transcode{vcodec=h264,vb=512}:standard{access=http,mux=ts,dst=:8099}'
