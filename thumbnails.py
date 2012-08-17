import subprocess
import sys
import json
import os
import argparse
import urlparse
import logging
import datetime

import flask

GM=os.path.abspath('./gm_thumbnails')
CURL='curl'
WORKDIR=os.path.abspath('./tmp')
LOGGER = logging.getLogger(__name__)

PARAM_IMAGE_URL='image_url'
PARAM_QUALITY='quality'
PARAM_RESIZE_METHOD='resize_method'
PARAM_BLUR='blur'

SETS = ['1', '2']

RESIZE_METHODS = list(enumerate([
    'Thumbnail',
    'Scale',
    'Sample',
    'Point',
    'Box',
    'Triangle',
    'Hermite',
    'Hanning',
    'Hamming',
    'Blackman',
    'Gaussian',
    'Quadratic',
    'Cubic',
    'Catrom',
    'Mitchell',
    'Lanczos',
    'Bessel',
    'Sinc'
]))

app = flask.Flask(__name__)

def download_file(url, dest=None, workdir=WORKDIR, curl=CURL, username='admin', password='admin', logger=LOGGER):
    if dest is None:
        dest = os.path.join(workdir, os.path.basename(url))
    cmd = [curl, '-u', '%s:%s' % (username, password), '-s', '-f', '-o', dest, url]
    p = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    out,err = p.communicate()
    if p.returncode != 0:
        logger.error('%s | while downloading %s -> %s', err, url, dest)
    return (p,out,err)



class RenditionSpec(object):
    def __init__(self, dimension, spec, rendition_path, rendition_url, original_url, resize_method, blur, quality):
        self.spec = spec
        self.rendition_path = rendition_path
        self.rendition_url = rendition_url
        self.original_url = original_url
        self.rendition_size = None
        self.resize_method = resize_method
        self.blur = blur
        self.quality = quality
        self.rendition_dimension = dimension 


    def __str__(self):
        return 'RenditionSpec("%s","%s")' % (self.spec, self.rendition_path)


def generate_thumbnails(image_path, rendition_specs):
    cmd = [GM, image_path]
    for specs in rendition_specs:
        for spec in specs:
            cmd.append('-f')
            cmd.append(spec.spec)
            cmd.append('-o')
            cmd.append(spec.rendition_path)
    app.logger.debug(' '.join(cmd))
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out,err = p.communicate()
    return (p, out, err)



@app.route("/", methods=['GET'])
def index():
    return flask.render_template('index.html', 
            RESIZE_METHODS = RESIZE_METHODS,
            PARAM_IMAGE_URL=PARAM_IMAGE_URL,
            PARAM_QUALITY=PARAM_QUALITY,
            PARAM_RESIZE_METHOD=PARAM_RESIZE_METHOD,
            PARAM_BLUR=PARAM_BLUR)

@app.route("/thumbnails", methods=['POST'])
def make_thumbnails():
    image_url = flask.request.form[PARAM_IMAGE_URL]
    _,ext = os.path.splitext(image_url)
    if len(ext) < 2: #image_url has extension. ends with .X
        return flask.render_template('make_thumbnails.html', error_msg='not a valid image url: %s' % image_url)

    quality = {}
    blur = {}
    resize_method = {}

    for i in SETS:
        quality[i] = int(flask.request.form[PARAM_QUALITY + i], 10)
        blur[i] = float(flask.request.form[PARAM_BLUR + i])
        resize_method[i] = int(flask.request.form[PARAM_RESIZE_METHOD + i], 10)


    json_url = image_url + '/jcr:content/renditions.-1.json'
    parsed = urlparse.urlparse(image_url)

    relative_path = os.path.join(parsed.netloc, parsed.path[1:] if parsed.path.startswith('/') else parsed.path)
    basedir = os.path.join(WORKDIR, relative_path)

    if not os.path.exists(basedir):
        app.logger.debug('making dir: %s', basedir)
        os.makedirs(basedir)

    image_path = os.path.join(basedir, 'original' + ext)
    json_path = os.path.join(basedir, 'original.json')

    download_file(image_url, image_path)
    download_file(json_url, json_path)

    rendition_specs = []

    with open(json_path, 'r') as f:
        renditions = json.load(f)
        for rendition_name,rendition in renditions.iteritems():
            try:
                if type(rendition) == dict and rendition['nym:shouldCrop']:
                    crop_x = rendition['nym:cropX']
                    crop_y = rendition['nym:cropY']
                    crop_w = rendition['nym:cropWidth']
                    crop_h = rendition['nym:cropHeight']
                    width = rendition['nym:width']
                    height = rendition['nym:height']

                    specs = []
                    for i in SETS:
                        spec_str = '%dx%d+%d+%d+%dx%d+%d+%d+%d' % (crop_w, crop_h, crop_x, crop_y, width, height, resize_method[i], blur[i], quality[i])
                        spec = RenditionSpec(width * height, spec_str, os.path.join(basedir, spec_str + ext), os.path.join('/thumbnails', relative_path, spec_str + ext), image_url + '/jcr:content/renditions/' + rendition_name, RESIZE_METHODS[resize_method[i]][1], blur[i], quality[i])
                        specs.append(spec)

                    rendition_specs.append(specs)
            except KeyError:
                pass

    rendition_specs.sort(lambda x,y: cmp(x[0].rendition_dimension, y[0].rendition_dimension))
    
    t = datetime.datetime.now()
    p,out,err = generate_thumbnails(image_path, rendition_specs)
    if p.returncode:
        return flask.render_template('make_thumbnails.html', error_msg=err)
    took = datetime.datetime.now() - t

    for specs in rendition_specs:
        for spec in specs:
            try:
                spec.rendition_size = os.path.getsize(spec.rendition_path) / (2 ** 10)
            except:
                pass
    
    return flask.render_template('make_thumbnails.html', took=took, image_url=image_url, rendition_specs=rendition_specs)

@app.route("/thumbnails/<path:filename>")
def serve_thumbnails(filename):
    return flask.send_from_directory(WORKDIR, filename)

def main():
    logging.basicConfig()
    logger = LOGGER
    logger.setLevel(logging.INFO)

    image_url = 'http://localhost:4502/content/dam/fashion/test/LillyJessMason_SalesStudentjpg.jpg'
    json_url = image_url + '/jcr:content/renditions.-1.json'
    parsed = urlparse.urlparse(image_url)
    
    dir_path = os.path.dirname(parsed.path)
    if dir_path.startswith('/'):
        dir_path = dir_path[1:]

    basedir = os.path.join(WORKDIR, parsed.netloc, dir_path)

    if not os.path.exists(basedir):
        logger.debug('making dir: %s', basedir)
        os.makedirs(basedir)

    image_name = os.path.basename(parsed.path)
    image_path = os.path.join(basedir, image_name)
    json_path = os.path.join(basedir, image_name + '.json')

    download_file(image_url, image_path)
    download_file(json_url, json_path)

    with open(json_path, 'r') as f:
        renditions = json.load(f)
        for rendition_name,rendition in renditions.iteritems():
            try:
                if type(rendition) == dict and rendition['nym:shouldCrop']:
                    crop_x = rendition['nym:cropX']
                    crop_y = rendition['nym:cropY']
                    crop_w = rendition['nym:cropWidth']
                    crop_h = rendition['nym:cropHeight']
                    width = rendition['nym:width']
                    height = rendition['nym:height']
                    print('%dx%d+%d+%d+%dx%d' % (crop_w, crop_h, crop_x, crop_y, width, height))
            except KeyError:
                pass

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
    
