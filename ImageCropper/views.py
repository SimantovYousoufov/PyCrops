from rest_framework.response import Response
from rest_framework import status
from boto.s3.connection import S3Connection
from boto.s3.key import Key
import boto
from rest_framework.decorators import api_view
import base64
from PIL import Image
import urllib, cStringIO
import StringIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys
import os

from cv2 import *
import numpy as np

# Request handler
# Not necessary to check if key exists in S3 already - this can be done on the front end as the s3 bucket url with
# the encoded filename can be determined on the front end
@api_view(['GET'])
def crop_handler(request, crop, encoded):
    decode = base64.b64decode(encoded).split('|')

    image_desired_data = {
        'width': int(decode[0]),
        'height': int(decode[1])
    }

    image_url = decode[2]

    try:
        image_file = cStringIO.StringIO(urllib.urlopen(image_url).read())

        image = Image.open(image_file)
    except IOError:
        return Response({
            'status': 'Image could not be retrieved from the url specified',
            'url': image_url
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    # Image.size is a tuple (width, height)
    width = image.size[0]
    height = image.size[1]

    #Check if key already exists in s3
    s3check = check_key_exists(str(encoded))
    if s3check:
        url = s3check.generate_url(0)
        response = {
            'status': 'Key already exists',
            'url': url
        }
        return Response(response)

    center = image_center(width, height)

    # Location of content of interest in images varies by orientation.
    # Not a perfect rule but would work for most photos
    # Photos with an aspect ratio of 1 are treated as landscape
    orientation = 'portrait' if height > width else 'landscape'

    altered = alter_image(
        image, image_desired_data, center,
        orientation, crop
    )

    upload_to_s3 = s3_upload(altered, str(encoded), image.format)

    response = {
        'status': 'Success',
        'image_url': upload_to_s3
    }

    return Response(response, status=status.HTTP_201_CREATED)


@api_view(['GET'])
def opencv_test(request):
    img = imread('/home/simon/Dev/ImageCropper/ImageCropper/image.jpg')
    width = img.shape[1]
    height = img.shape[0]

    orientation = 'portrait' if height > width else 'landscape'

    center = image_center(width, height)

    image_desired_data = {
        'width': 300,
        'height': 400
    }

    altered = alter_image(
        img, image_desired_data, center,
        orientation, 1
    )

    upload_to_s3 = s3_upload(altered, 'opencvtest', 'jpg')

    response = {
        'status': 'Success',
        'image_url': upload_to_s3
    }

    return Response(response, status=status.HTTP_201_CREATED)


def alter_image(image, image_desired_data, center, orientation, crop):
    if not int(crop) == 1:
        altered = resize(image, (image_desired_data['width'], image_desired_data['height']))
        return altered

    if orientation == 'landscape':
        height = image_desired_data['height']
        # w/h = r
        # width = int(round(center['ratio']*height))
        width = image_desired_data['width']

        dimensions_desired = (width, height)

        resized = resize(image, dimensions_desired)

        # Calculate cropping out from center
        #
        # actual_width - desired_width = left over part of image that is not needed. Same for height.
        # PIL coordinates for box are (left, upper, right, lower) with left, upper corner being 0,0
        #
        # Half the area left after the crop is the leftover area on one side
        h_to_crop = (width - image_desired_data['width'])/2

        # (offset from left, offset from top, offset from right, offset from bottom)
        box = (0+h_to_crop, 0, width-h_to_crop, height)

        altered = resized[0:height, 0+h_to_crop:width-h_to_crop]

        return altered
    else:
        # For portrait
        width = image_desired_data['width']
        # height = int(round(center['ratio']*width))
        height = image_desired_data['height']
        dimensions_desired = (width, height)
        resized = resize(image, dimensions_desired)
        v_to_crop = (image_desired_data['height'] - height)/2
        box = (0, 0+v_to_crop, width, height-v_to_crop)

        # Image cropping: [y1:y2, x1:x2] where *2>*1
        altered = resized[0+v_to_crop:height-v_to_crop, 0:width]

        response = {
            'original_image': image.shape,
            'altered_shape': altered.shape,
            'resized_shape': resized.shape,
            'y1': 0+v_to_crop,
            'y2': height-v_to_crop,
            'x1': 0,
            'x2': width,
            'desired_data': {
                'height': height,
                'width': width,
                'v_to_crop': v_to_crop,
            }
        }
        return response

        return altered


def image_center(width, height):
    h_center = width/2
    v_center = height/2

    center = {
        'x': h_center,
        'y': v_center,
        'ratio': float(width)/height
    }

    return center


def check_key_exists(file_name):
    try:
        s3 = S3Connection(os.environ['AWS_ACCESS_KEY_ID'], os.environ['AWS_SECRET_KEY'])
    except boto.exception.S3ResponseError:
        return Response({
            'status': 'S3 Connection error',
            'Message': 'The connection to S3 could not be established'
        },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    bucket_name = os.environ['S3_BUCKET_NAME']
    bucket = s3.get_bucket(bucket_name)
    key = bucket.get_key(os.environ['S3_FOLDER_NAME']+file_name)

    return key
    # key_object = Key(bucket)


# Finds the center point of the image, for cropping
# def image_center(width, height):
#     h_center = width/2
#     v_center = height/2
#
#     center = {
#         'x': h_center,
#         'y': v_center,
#         'ratio': float(width)/height
#     }
#
#     return center


# Pillow documentation: http://pillow.readthedocs.org/
# def alter_image(image, image_desired_data, center, orientation, crop):
#     # The cropping methods for orientation types could be abstracted but in the interest of time I did not.
#     if not int(crop) == 1:
#         altered = image.resize(image_desired_data['width'], image_desired_data['height'])
#
#         return altered
#
#     if orientation == 'landscape':
#         height = image_desired_data['height']
#         # w/h = r
#         width = int(round(center['ratio']*height))
#
#         dimensions_desired = (width, height)
#
#         resized = image.resize(dimensions_desired)
#
#         altered = resized
#
#         # Calculate cropping out from center
#         #
#         # actual_width - desired_width = left over part of image that is not needed. Same for height.
#         # PIL coordinates for box are (left, upper, right, lower) with left, upper corner being 0,0
#         #
#         # Half the area left after the crop is the leftover area on one side
#         h_to_crop = (width - image_desired_data['width'])/2
#
#         # (offset from left, offset from top, offset from right, offset from bottom)
#         box = (0+h_to_crop, 0, width-h_to_crop, height)
#
#         altered = resized.crop(box)
#
#         # debug = {
#         #     'resized_width': resized.size[0],
#         #     'resized_height': resized.size[1],
#         #     'dimensions_required': dimensions_desired,
#         #     'h_to_crop': h_to_crop,
#         #     'box': {
#         #         'left': width-h_to_crop,
#         #         'upper': 0,
#         #         'right': 0+h_to_crop,
#         #         'lower': height,
#         #     },
#         #     'cropped': altered.size
#         # }
#
#         return altered
#     else:
#         # For portrait
#         width = image_desired_data['width']
#         height = int(round(center['ratio']*width))
#         dimensions_desired = (width, height)
#         resized = image.resize(dimensions_desired)
#         v_to_crop = (height - image_desired_data['height'])/2
#         box = (0, 0+v_to_crop, width, height-v_to_crop)
#
#         cropped = resized.crop(box)
#
#         return cropped


# Could later implement batch tasks via threading
def s3_upload(image, encoded, format):
    # Need to convert PIL file like object to a Django File Object
    # file = SimpleUploadedFile(image, encoded + '.' + format, format)
    image_io = StringIO.StringIO()
    # image.save(image_io, format=format)

    file = InMemoryUploadedFile(
        image_io, None, encoded+'.'+format,
        'image/'+format, image_io.len, None
    )

    # To prepend folder name
    s3_folder_name = 'ImageCropper/'

    key_name = encoded

    # Secret and key are set in environment variables
    try:
        s3 = S3Connection(os.environ['AWS_ACCESS_KEY_ID'], os.environ['AWS_SECRET_KEY'])
    except boto.exception.S3ResponseError:
        return Response({
            'status': 'S3 Connection error',
            'Message': 'The connection to S3 could not be established'
        },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    bucket_name = os.environ['S3_BUCKET_NAME']
    bucket = s3.get_bucket(bucket_name)
    key_object = Key(bucket)

    key_object.key = s3_folder_name + key_name
    # Setting rewind=true is a workaround for an EOF error
    key_object.set_contents_from_file(file, rewind=True)
    key_object.make_public()

    image_url = key_object.generate_url(expires_in=0, query_auth=False)

    return image_url