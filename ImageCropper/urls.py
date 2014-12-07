from django.conf.urls import patterns, url
from ImageCropper import views


urlpatterns = patterns('',
    # Simple regex pattern that fits a base64 encoded string. Won't work for /crop/encoded/other_parameter/
    url(r'^resize/(?P<crop>\d+)/(?P<encoded>.+)/$', views.crop_handler, name='cropImage'),

)