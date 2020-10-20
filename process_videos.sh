#!/bin/bash

for NUM in 4 5 7 8
do
  python3 main.py -cam visual -s -v "videos/videos_05092019/DJI_000$NUM.MOV"  --disable_alerts
  echo "Finished processing video $NUM"
done
echo "Finished processing ALL VIDEOS"

