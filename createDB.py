#! /usr/bin/env python

"LiDAR database"

import os, glob, argparse
import numpy as np
from laspy.file import File
import sqlite3
import hashlib
import ConfigParser
import time
import csv


def getArgs():
	parser = argparse.ArgumentParser(
		description="LiDAR LAS file parsing into an sqlite3 database used for lidar classification."
	)
	parser.add_argument(
		"-c",
		"--config",
		type=str,
		required=True,
		help="Configuration File"
	)
	parser.add_argument(
		"-v",
		"--verbose",
		action = "store_true",
		help="Print notices to screen."

	)
	return parser.parse_args()

def getConfigs(configFile):
	Configs={}
	try:
		config = ConfigParser.ConfigParser()
		config.read(configFile)
		Configs["paths"]=dict(config.items("paths"))
	except Exception as e:
		print "Problem parsing configuration file: {}.".format(configFile)
		raise e
	return Configs


def window(elem,l, scale):
	"""Hash utm coordinates
	"""
	point = elem[0]
	utm_e = point[0]*scale[0] # now in meters
	utm_n = point[1]*scale[1] # now in meters
	index = "{},{}".format(int(utm_e)/int(l),int(utm_n)/int(l))
	n = hashlib.sha224(index).hexdigest()
	return n

def createDB(configs):
	""" Create database
	"""
	database = configs["paths"]["db"]
	
	# Initiate DB
	conn = sqlite3.connect(database)
	c = conn.cursor()
	c.execute('DROP TABLE IF EXISTS pointcloud')
	conn.commit()
	try:
		c.execute(
			'''CREATE TABLE pointcloud (
				filename TEXT,
				hash10 TEXT,
				hash5 TEXT,
				hash1 TEXT, 
				num_returns INTEGER,
				return_number INTEGER,
				X INTEGER,
				Y INTEGER,
				Z INTEGER,
				intensity INTEGER,
				flag_byte INTEGER,
				raw_classification INTEGER,
				scan_angle_rank INTEGER,
				user_data INTEGER,
				pt_src_id INTEGER,
				gps_time REAL
				)'''
		)
		conn.commit()
	except sqlite3.Error as e:
		print "An error was raised: ", e.args[0]
		raise e
	conn.close()
	return 0

def indexDB(configs):
	"""Index hash columns and Z column of DB
	"""
	database = configs["paths"]["db"]
	conn = sqlite3.connect(database)
	c = conn.cursor()
	c.execute('CREATE INDEX hash10index ON pointcloud(hash10)')
	c.execute('CREATE INDEX hash5index ON pointcloud(hash5)')
	c.execute('CREATE INDEX hash1index ON pointcloud(hash1)')
	c.execute('CREATE INDEX zindex ONE pointcloud(Z)')
	conn.close()

def files(configs):
	paths = []
	indirs = configs["paths"]["input"]
	indirs = indirs.split(":")
	for directory in indirs:
		os.chdir(directory)
		infiles = glob.glob("*.las")
		for i, infile in enumerate(infiles):
			path = directory + infile
			paths.append(path)
	return paths


def add_data(infile, configs):
	t_i = time.time()
	database = configs["paths"]["db"]
	conn = sqlite3.connect(database)
	#conn.execute("PRAGMA busy_timeout = 30000")
	c = conn.cursor()
	indata = File(infile, mode="r")
	filename = infile.split("/")[-1]
	points = indata.points
	return_num = indata.return_num
	num_returns = indata.num_returns
	scale = indata.header.scale
	data = []
	count = 0
	for i, elem in enumerate(points):
		X,Y,Z,intensity,flag_byte,raw_classification,scan_angle_rank,user_data,pt_src_id,gps_time=elem[0]
		#print data_text
		row = (
			filename,
			window(elem, 10, scale),
			window(elem, 5, scale),
			window(elem, 1, scale), 
			int(num_returns[i]),
			int(return_num[i]),
			int(X),
			int(Y),
			int(Z),
			int(intensity),
			int(flag_byte),
			int(raw_classification),
			int(scan_angle_rank),
			int(user_data),
			int(pt_src_id),
			float(gps_time)
		)
		data.append(row)
		#row = (window_index, elem)
		count +=1
	c.executemany('INSERT INTO pointcloud VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', data)
	conn.commit()
	indata.close()
	t_f = time.time()
	print "Time for {} with {} records took {} minutes.".format(
		filename,
		count, 
		(t_f-t_i)/60.0
	)



def main():
	t_i = time.time()

	args=getArgs()
	if args.verbose:
		print "Arguments: "
		print args

	configs = getConfigs(args.config)
	if args.verbose:
		print "Configurations: "
		print configs

	paths = files(configs)
	if args.verbose:
		print "Files: "
		print paths

	createDB(configs)
	if args.verbose:
		print "Created database."

	for path in paths:
		add_data(path, configs)
	if args.verbose:
		print "Added data to database."
	indexDB(configs)
	if args.verbose:
		print "Indexed database."

	t_f = time.time()
	print "Finished. Total elapsed time {} minutes.".format((t_f-t_i)/60.0)

if __name__ == "__main__":
	main()