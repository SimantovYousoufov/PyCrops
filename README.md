PyCrops
============

An ImageCropping API

###What does PyCrops do?
PyCrops will retrieve an image from the specified url, resize and, if requested, crop an image that it retrieves from a URL you specify to the dimensions you specify. It will then upload the altered file to an S3 bucket and return a url through which it can be accessed.

###Environment Setup
Set up a virtual environment with the following dependencies:
- Django (pip install django): https://docs.djangoproject.com/en/1.7/topics/install/
- Django REST Framework: http://www.django-rest-framework.org/) 
  - pip install djangorestframework
  - pip install markdown  
  - pip install django-filter
- Boto (pip install boto): http://boto.readthedocs.org/en/latest/getting_started.html
- MySQL Python (pip install MySQL-Python)
- Pillow - a PIL fork for wasy image processing: http://pillow.readthedocs.org/en/latest/installation.html
  - Install dependencies as listed in the docs, ex for Ubuntu 14.04: 
    ```
    sudo apt-get install libtiff5-dev libjpeg8-dev zlib1g-dev \
    libfreetype6-dev liblcms2-dev libwebp-dev tcl8.6-dev tk8.6-dev python-tk
    ```
  - Install pillow: pip install pillow

###Application Set up
- Fill in MySQL database information in CroppingService/settings.py
  - The database currently isn't being utilized but I have plans for how to use it to help with image cropping in the future.
- From the root project directory run 'python manage.py migrate' to migrate the required Django tables to the database.
- Create CroppingService/appinfo.py from appinfo_sample.py in the same folder and fill in the required information.
- Start the local dev server with 'python manage.py runserver'. Navigating to http://localhost:8000/resize/1/*base64_encoded_request*/ will reach the API.

###Sending Requests
The API accepts requests in a base64 encoded string. The string format is standardized and must be followed. Example:
```
<width desired>|<height desired>|<url of image to retrieve>
450|600|http://www.croscon.com/img/work-bpr/header.jpg
```
Encodes to:
```
NDUwfDYwMHxodHRwOi8vd3d3LmNyb3Njb24uY29tL2ltZy93b3JrLWJwci9oZWFkZXIuanBn
```
https://www.base64encode.org/ is useful for encoding sample requests.

The URL parameters are formatted: /resize/*crop*/*base64_encoded_request*/. Crop = 1 will crop the image from the center, any other value will just resize the image.
