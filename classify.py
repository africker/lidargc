#! /usr/bin/env python

"LiDAR ground algorithm"

import os, glob, argparse, time, math
import numpy as np
from laspy.file import File
import sqlite3
import ConfigParser

def getArgs():
	parser = argparse.ArgumentParser(
		description="LiDAR ground and canopy classification."
	)
	parser.add_argument(
		"-c",
		"--config",
		type=str,
		required=True,
		help="Configuration File."
	)
	parser.add_argument(
		"-g",
		"--ground",
		action = "store_true",
		help="Ground classification."

	)
	parser.add_argument(
		"-t",
		"--toc",
		action = "store_true",
		help="Canopy classification."

	)
	parser.add_argument(
		"-v",
		"--verbose",
		action = "store_true",
		help="Print status to screen."

	)

	return parser.parse_args()

def getConfigs(configFile):
	Configs={}
	try:
		config = ConfigParser.ConfigParser()
		config.read(configFile)
		Configs["paths"]=dict(config.items("paths"))
		Configs["vars"]=dict(config.items("vars"))
	except Exception as e:
		print "Problem parsing configuration file: {}.".format(configFile)
		raise e
	return Configs

class Points(object):
	def __init__(self, points, configs, filename):
		self.points = points
		self.configs = configs
		self.filename = filename

	def getParams(self):
		"""
		"""
		indirs = self.configs["paths"]["input"]
		indir = indirs.split(":")[0]
		os.chdir(indir)
		infile=glob.glob("*.las")[0]
		data = File(infile, mode="r")
		self.header = data.header
		#print self.header
		self.dtype = data.points.dtype

	def write(self):
		output = self.configs["paths"]["output"]
		points = np.array(self.points, dtype=self.dtype)
		#print self.header
		outfile = File(output + self.filename, mode="w", header=self.header)
		outfile.points = points
		outfile.close()

def setGround(pt):
	pt = list(pt)
	pt[5]=2
	return tuple(pt)

def setCanopy(pt):
	pt = list(pt)
	pt[5]=1
	return tuple(pt)

def height(dz, thresh=1.5):
	return dz < 1.5

def angle(dX, dY, dZ, thresh=5.5, eps=0.000000001):
	hyp = math.sqrt((dX)**2+(dY)**2+(dZ)**2)
	# Use epsilon equality for floats
	if hyp < eps:
		return False
	degrees = math.asin(dZ/hyp)*(180/math.pi)
	return degrees < thresh


def groundFilter(seed, pt):
	X0=seed[0]*0.001
	Y0=seed[1]*0.001
	Z0=seed[2]*0.001
	X1=pt[0]*0.001
	Y1=pt[1]*0.001
	Z1=pt[2]*0.001
	dX = X1-X0
	dY = Y1-Y0
	dZ = Z1-Z0
	# skip duplicated point
	if seed == pt:
		return False
	return height(dZ) and angle(dX, dY, dZ)




def groundClassifier(configs):
	"""
	"""
	t_i = time.time()
	points = []

	database = configs["paths"]["db"]
	conn = sqlite3.connect(database)
	c = conn.cursor()
	minZs = c.execute("""SELECT distinct(hash10), min(Z) FROM pointcloud 
							WHERE num_returns=return_number
							GROUP BY hash10;"""
	).fetchall()
	minZs = list(minZs)
	print minZs
	count = 0
	for h, z in minZs:
		seed = c.execute("""
			SELECT
				X,
				Y,
				Z,
				intensity,
				flag_byte,
				raw_classification,
				scan_angle_rank,
				user_data,
				pt_src_id,
				gps_time
			FROM pointcloud
			WHERE Z=? and hash10=?;
			""", (z, h)).fetchall()[0]
		print seed
		seed = setGround(seed)
		points.append((seed,))
		putative_grounds = c.execute("""
			SELECT
				X,
				Y,
				Z,
				intensity,
				flag_byte,
				raw_classification,
				scan_angle_rank,
				user_data,
				pt_src_id,
				gps_time
			FROM pointcloud
			WHERE hash10=? AND num_returns=return_number;
			""", (h,)).fetchall()
		for putative_ground in putative_grounds:
			if groundFilter(seed, putative_ground):
				putative_ground=setGround(putative_ground)
				points.append((putative_ground,))
		count += 1
		print "Finished {}; block hash {}.".format(count, h)
	conn.close()
	t_f = time.time()
	print "Ground classifier took {} minutes.".format((t_f-t_i)/60.0)
	return points


def canopyClassifier(configs):
	"""
	"""
	t_i = time.time()
	points = []
	scale = float(configs["vars"]["scale"])
	height_max = float(configs["vars"]["height_max"])/scale # depends on scale
	database = configs["paths"]["db"]
	conn = sqlite3.connect(database)
	c = conn.cursor()

	hashmap_list = c.execute("SELECT distinct(hash1),hash10 FROM pointcloud;").fetchall()
	hashmap = {}
	for k,v in hashmap_list:
		hashmap[k]=v

	minZ_list = c.execute("""SELECT distinct(hash10), min(Z) FROM pointcloud
							where num_returns=return_number
							GROUP BY hash10"""
	).fetchall()
	min_z = {}
	for k,v in minZ_list:
		min_z[k]=v

	maxZs = c.execute("""SELECT distinct(hash1), max(Z) FROM pointcloud 
							WHERE return_number=1
							GROUP BY hash1"""	
	).fetchall()
	count = 0
	for h1,h10 in hashmap.iteritems():
		z_max = min_z[h10] + height_max
		results = c.execute("""
			SELECT
				X,
				Y,
				Z,
				intensity,
				flag_byte,
				raw_classification,
				scan_angle_rank,
				user_data,
				pt_src_id,
				gps_time
			FROM pointcloud
			WHERE Z<? and hash1=?;
			""", (z_max, h1)).fetchall()
		heights={}
		for result in results:
			Z = result[2]
			heights[Z]=result
		if len(heights)>0:
			TOC = heights[max(heights)]
			TOC = setCanopy(TOC)
			points.append((TOC,))
			count += 1
			print "Finished {}; block hash {}.".format(count, h1)
	conn.close()
	t_f = time.time()
	print "Canopy classifier took {} minutes.".format((t_f-t_i)/60.0)
	return points

def main():
	t_i = time.time()
	args=getArgs()
	if args.verbose:
		print args
	#base = os.getcwd()
	configs = getConfigs(args.config)
	if args.verbose:
		print configs
	if args.ground:
		points = groundClassifier(configs)
		print points
		groundPoints = Points(points, configs, "ground.las")
		groundPoints.getParams()
		groundPoints.write()
	if args.toc:
		points = canopyClassifier(configs)
		print points
		canopyPoints = Points(points, configs, "canopy.las")
		canopyPoints.getParams()
		canopyPoints.write()
	t_f = time.time()
	if args.verbose:
		print "Total elapsed time {} minutes.".format((t_f-t_i)/60)





			#list_data.append((window_index, data_text))
		#c.executemany('INSERT INTO pointcloud VALUES (?,?)', list_data)


	#data = group(args.input)
	#os.chdir(base)
	#print data






if __name__ == "__main__":
	main()