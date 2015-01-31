#! /bin/bash

DIR=/Volumes/2TB-1/LiDAR/source/lidargc

# Create DB
python ${DIR}/createDB.py -c ${DIR}/createDB.cfg -v

# Create las files for DEM and DSM
python ${DIR}/classify.py -c ${DIR}/classify.cfg -g -t -v
