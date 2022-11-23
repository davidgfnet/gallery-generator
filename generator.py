#!/usr/bin/python
# -*- coding: utf-8 -*-

import os, argparse, re, hashlib, shutil, urllib
from PIL import Image, ExifTags, ImageFile
from tqdm import tqdm
from moviepy.editor import *
ImageFile.LOAD_TRUNCATED_IMAGES = True

parser = argparse.ArgumentParser(description='Create a photo gallery out of a bunch of images folders')
parser.add_argument('--dir', dest='dir', required=True, action='store', help='Directory to process')
parser.add_argument('-o','--output', dest='out', action='store', required=True, help='Directory to output the gallery')
parser.add_argument('--photo-extensions', dest='iext', action='store', default="jpg,jpeg,gif,png,tiff,tif,bmp,svg", help='List of accepted photo extensions')
parser.add_argument('--video-extensions', dest='vext', action='store', default="mp4,mkv,mod,mpg,mpeg,avi,avi,webm", help='List of accepted video extensions')
parser.add_argument('--basepath', dest='bpath', action='store', default="", help='Basepath for the video/images in case they are not copied')
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
			orientation = exif.get(orientation, 0)

			if orientation == 3:   image = image.transpose(Image.ROTATE_180)
			elif orientation == 6: image = image.transpose(Image.ROTATE_270)
			elif orientation == 8: image = image.transpose(Image.ROTATE_90)

	return image

args = parser.parse_args()

def shash(s): return hashlib.sha1(s).hexdigest()[:16]
def basename(s): return s.split("/")[-1]
def extension(s): return s.split(".")[-1]
def lowercase(n): return n.decode('utf-8').lower().encode('utf-8')

def getmime(f):
	extension = f.lower().split(".")[-1]
	mapping = {
		"webm": "video/webm",
		"ogg":  "video/ogg",
		"mp4":  "video/mp4",
		"webm": "video/webm",
	if f.endswith(".webm"):
		return "video/webm"
	if f.endswith(".ogg"):
		return "video/ogg"
	return "video/mp4"

def isvalidphoto(fname):
	for x in args.iext.split(","):
		if lowercase(fname).endswith(x):
			return True
	return False

def isvalidvideo(fname):
	for x in args.vext.split(","):
		if lowercase(fname).endswith(x):
			return True
	return False

def get_photos(path):
	files = [os.path.join(path, x) for x in os.listdir(path)]
	return [fn for fn in files if os.path.isfile(fn) and isvalidphoto(fn)]

def get_videos(path):
	files = [os.path.join(path, x) for x in os.listdir(path)]
	return [fn for fn in files if os.path.isfile(fn) and isvalidvideo(fn)]

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

def doheader(path):
	nav = path[len(args.dir):]
	if nav != "":
		nav = get_dir_hier(nav)
		nav = [ '<a href="%s.html">%s</a>'%(shash(os.path.join(args.dir,x)),basename(x)) for x in nav ]
	else:
		nav = []
	nav = " > ".join(['<a href="index.html">Index</a>'] + nav)
	return nav

def dobrowse(path):
	# Generate a document for each
	dirs = sorted(get_child_dirs(path))
	plist = "\n".join(['<a class="btn btn-primary btn-padding" href="%s.html" role="button">%s</a>' %
						(shash(x),basename(x)) for x in dirs ])
	return plist


os.mkdir(args.out)
os.mkdir(os.path.join(args.out,"img"))

# Generate gallery pages
photo_dirs = get_dirs(args.dir) + [args.dir]
template = open(os.path.join("bs","template.html"),"rb").read()
for d in photo_dirs:
	page = template
	photos = sorted(get_photos(d))
	videos = sorted(get_videos(d))
	subdirs = dobrowse(d)

	page = re.sub("{IMGSECTION(.*)/IMGSECTION}", r"\1" if photos else "", page, flags=re.DOTALL)
	page = re.sub("{VIDSECTION(.*)/VIDSECTION}", r"\1" if videos else "", page, flags=re.DOTALL)
	page = re.sub("{DIRSECTION(.*)/DIRSECTION}", r"\1" if subdirs else "", page, flags=re.DOTALL)

	plist, vlist, vlist2 = [], [], []
	for x in tqdm(photos):
		try:
			# Copy photo if necessary
			if args.copy:
				fn = os.path.join("img", shash(x) + "." + lowercase(extension(x)))
				fn_thumb = os.path.join("img", shash(x) + "_thumb.jpg")
				fn_fullpath = os.path.join(args.out, fn)
				open(fn_fullpath, "wb").write(open(x, "rb").read())
			else:
				fn = os.path.join(args.bpath, x)
			# Take thumbnail if necessary
			if args.thumbs:
				fn_thumb_fullpath = os.path.join(args.out,fn_thumb)
				im = rotimg(Image.open(fn_fullpath))
				im.thumbnail((600, 600), Image.ANTIALIAS)
				im.save(fn_thumb_fullpath, "JPEG", quality=60)
			else:
				fn_thumb = fn

			plist.append('<a href="%s"><img src="%s"/></a>' % (fn, fn_thumb))
		except:
			print "Could not read image", x

	for i, fn in enumerate(tqdm(videos)):
		fn_frame = os.path.join("img", shash(fn) + "_frame.jpg")
		fn_thumb = os.path.join("img", shash(fn) + "_thumb.jpg")
		clip = VideoFileClip(fn)
		clip.save_frame(os.path.join(args.out, fn_frame), t=1.00)
		# if fn.lower().endswith(".mod"): # Patch for wrong aspect ratio
		im = Image.open(os.path.join(args.out, fn_frame))
		im = im.resize((int(im.size[0] * 4.0/3), im.size[1]))
		im.save(os.path.join(args.out, fn_frame), "JPEG", quality=80)
		im = Image.open(os.path.join(args.out, fn_frame))
		im.thumbnail((300, 300), Image.ANTIALIAS)
		im.save(os.path.join(args.out, fn_thumb), "JPEG", quality=60)
		vlist.append("""
			<div style="display:none;" id="video%d">
				<video class="lg-video-object lg-html5" controls preload="none">
					<source src="%s" type="%s">
				</video>
			</div>""" % (i, urllib.quote_plus(fn.replace(args.dir, args.bpath)), getmime(fn)))
		vlist2.append("""
			<li data-poster="%s" data-sub-html="%s" data-html="#video%d" class="col-xs-6 col-sm-4 col-md-3 col-lg-2 video vpad">
			  <img class="img-responsive" src="%s" />
			</li>""" % (fn_frame, basename(fn), i, fn_thumb))

	plist = "\n".join(plist)
	vlist = "\n".join(vlist)
	vlist2 = "\n".join(vlist2)

	# Special care with index
	name = shash(d) if d != args.dir else "index"
	page = page.replace("{IMAGES}", plist).replace("{TITLE}", doheader(d))
	page = page.replace("{DIRS}", subdirs).replace("{VIDEOS}", vlist2).replace("{VIDEOSSRC}", vlist)
	open(os.path.join(args.out,name+".html"),"wb").write(page)

# Copy support files
for e in ["css", "js", "fonts"]:
	shutil.copytree(os.path.join("bs", e), os.path.join(args.out, e))


