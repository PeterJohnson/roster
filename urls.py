from django.conf.urls.defaults import *
from django.contrib.auth.views import login, logout

urlpatterns = patterns('roster.views',
    (r'^$', 'front'),
    #(r'^readme$', 'readme'),    # use to preview readme.md
    (r'^login/$', login, {'template_name': 'roster/login.html'}),
    (r'^logout/$', logout, {'template_name': 'roster/logout.html'}),
    (r'^email/$', 'email_list'),
    #(r'^person/$', 'person_list'),
    #(r'^person/(?P<person_link>[\w-]+)$', 'person_detail'),
    #(r'^student/$', 'student_list'),
    #(r'^student/(?P<student_link>[\w-]+)$', 'student_detail'),
    #(r'^adult/$', 'student_list'),
    #(r'^adult/(?P<student_link>[\w-]+)$', 'adult_detail'),
)
