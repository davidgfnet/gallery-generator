#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import argparse
import hashlib
import shutil
from PIL import Image, ExifTags

parser = argparse.ArgumentParser(description='Create a photo gallery out of a bunch of images folders')
parser.add_argument('--dir', dest='dir', action='store', help='Directory to process')
parser.add_argument('-o','--output', dest='out', action='store', help='Directory to output the gallery')
parser.add_argument('--extensions', dest='ext', action='store', default="jpg,jpeg,gif,png,tiff,tif,bmp,svg", help='List of accepted photo extensions')
parser.add_argument('--copy', dest='copy', action='store_true', default=False, help='Copy images to the web gallery (instead of linking them)')
parser.add_argument('--thumbnails', dest='thumbs', action='store_true', default=False, help='Create thumbnails for the pictures')

# The gallery will be quite big, ideally three cloumns on lg, two on md and one sm and below
# Will create a thumbnail for each photo (if specified) which should be around 800px width

def rotimg(image):
	if hasattr(image, '_getexif'): # only present in JPEGs
		for orientation in ExifTags.TAGS.keys(): 
			if ExifTags.TAGS[orientation]=='Orientation':
				break 
		e = image._getexif()       # returns None if no EXIF data
		if e is not None:
			exif=dict(e.items())
			orientation = exif[orientation] 

			if orientation == 3:   image = image.transpose(Image.ROTATE_180)
			elif orientation == 6: image = image.transpose(Image.ROTATE_270)
			elif orientation == 8: image = image.transpose(Image.ROTATE_90)

	return image

args = parser.parse_args()

def shash(s): return hashlib.sha1(s).hexdigest()[:16]
def basename(s): return s.split("/")[-1]
def extension(s): return s.split(".")[-1]
def lowercase(n): return n.decode('utf-8').lower().encode('utf-8')

def isvalidphoto(fname):
	for x in args.ext.split(","):
		if lowercase(fname).endswith(x):
			return True
	return False

def contains_photos(path):
	for x in os.listdir(path):
		fn = os.path.join(path,x)
		if os.path.isfile(fn) and isvalidphoto(fn):
			return True
	return False
def get_photos(path):
	r = []
	for x in os.listdir(path):
		fn = os.path.join(path,x)
		if os.path.isfile(fn) and isvalidphoto(fn):
			r.append(fn)
	return r

def contains_dir(path):
	for x in os.listdir(path):
		fn = os.path.join(path,x)
		if os.path.isdir(fn):
			return True
	return False

# Get dir list
def get_dirs(path):
	dirs = [ y for y in [os.path.join(path,x) for x in os.listdir(path)] if os.path.isdir(y) ]
	for p in dirs:
		dirs += get_dirs(p)
	return dirs
def get_child_dirs(path):
	return [ y for y in [os.path.join(path,x) for x in os.listdir(path)] if os.path.isdir(y) ]
def get_dir_hier(path):
	l = path.split("/")
	r = []
	c = ""
	for e in l:
		p = os.path.join(c,e)
		r.append(p)
		c = p
	return r
		

# Returns a set of dirs which will be a gallery
# (leaf dir + some photos there)
def get_gallery_dirs(path):
	dirs = get_dirs(path)
	dirs = [ x for x in dirs if contains_photos(x) and not contains_dir(x) ]
	return dirs
def get_nav_dirs(path):
	dirs = get_dirs(path)
	dirs = [ x for x in dirs if not contains_photos(x) and contains_dir(x) ]
	return dirs

def doheader(path):
	nav = path[len(args.dir):]
	if nav != "":
		nav = get_dir_hier(nav)
		nav = [ '<a href="%s.html">%s</a>'%(shash(os.path.join(args.dir,x)),basename(x)) for x in nav ]
	else:
		nav = []
	nav = " > ".join(['<a href="index.html">Index</a>'] + nav)
	return nav

os.mkdir(args.out)
os.mkdir(os.path.join(args.out,"img"))

# Generate index pages
nav_dirs = get_nav_dirs(args.dir) + [args.dir]
template = open(os.path.join("bs","dir-template.html"),"rb").read()
for d in nav_dirs:
	# Generate a document for each
	dirs = sorted(get_child_dirs(d))
	plist = "\n".join([ '<a class="btn btn-primary btn-padding" href="%s.html" role="button">%s</a>'%(shash(x),basename(x)) for x in dirs ])

	# Nav var
	nav = doheader(d)

	page = template.replace("{DIRS}", plist).replace("{TITLE}", nav)
	name = shash(d) if d != args.dir else "index"
	open(os.path.join(args.out,name+".html"),"wb").write(page)

# Generate gallery pages
photo_dirs = get_gallery_dirs(args.dir)
template = open(os.path.join("bs","gal-template.html"),"rb").read()
for d in photo_dirs:
	photos = sorted(get_photos(d))

	plist = []
	for x in photos:
		# Copy photo if necessary
		if args.copy:
			fn = os.path.join("img",shash(x)+"."+lowercase(extension(x)))
			fn_thumb = os.path.join("img",shash(x)+"_thumb.jpg")
			fn_fullpath = os.path.join(args.out,fn)
			open(fn_fullpath,"wb").write(open(x,"rb").read())
		else:
			fn = x
		# Take thumbnail if necessary
		if args.thumbs:
			fn_thumb_fullpath = os.path.join(args.out,fn_thumb)
			im = rotimg(Image.open(fn_fullpath))
			im.thumbnail((800, 800), Image.ANTIALIAS)
			im.save(fn_thumb_fullpath, "JPEG", quality=60)
		else:
			fn_thumb = fn

		plist.append('<div class="imgdiv col-sm-12 col-md-6 col-lg-4"><a href="%s" target="_blank"><img class="fit lazy" data-original="%s"/></a></div>' % (fn, fn_thumb))
	plist = "\n".join(plist)

	nav = doheader(d)

	page = template.replace("{IMAGES}", plist).replace("{TITLE}", nav)
	open(os.path.join(args.out,shash(d)+".html"),"wb").write(page)

# Copy support files
for e in ["css","js","fonts"]:
	shutil.copytree(os.path.join("bs",e), os.path.join(args.out,e))




