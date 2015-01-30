README 
======

General
-------
A set of programs to process LiDAR data stored as *.LAS files into new *.LAS files containing to produce a digital elevation model, digital surface model, and digital canopy height model by rasterizing.

Currently, the steps involve 1) creating an SQLite3 database with point data from *.LAS files using the createDB.py command and 2) running either or both the ground classifier andcanopy surface classifier with the classify.py command.

Ground Point Classification
-------
Data are processed with 10 m x 10 m kernels.  The lowest last-return point in the 10 m x 10 m kernel is classified as a seed ground point. Remaining points are classified as ground points if they are < 5.5 degrees from the horizontal plane of the seed ground point and < 1.5 m distant in height.  Only ground classified points are written to a file called ground.las. 

Canopy Point Classification
-------
Data are processed with 1 m x 1 m kernels. The highest first return point in a 1 m x 1 m kernel is classified as a top of the canopy point. Only top of canopy points are written to a file called canopy.las.

Dependencies
-------
<a href="http://www.numpy.org/">numpy</a>, <a href="https://github.com/grantbrown/laspy">laspy</a>

Notes
-------
Expect needing at least 20x the space taken up by the input LAS files for the database.

This program was tested on computer with x86-64 archtecture and 64 GB of RAM running Mac OS X. The hard drive is formated as Mac OS Extended.

Points from above the canopy (e.g. birds, clouds) are filtered by specifying a threshold for the maximum height from the ground. The distance from the ground is approximated by the lowest point in the 10 m x 10 m kernel containing the 1 m x 1 m kernel. 

References
------- 
[1] Asner GP, et al. (2014) Targeted carbon conservation at national scales with high-resolution monitoring. Proc Natl Acad Sci USA. 111(47):E5016–E5022.  <a href="http://dx.doi.org/10.1073/pnas.1419550111">http://dx.doi.org/10.1073/pnas.1419550111</a>