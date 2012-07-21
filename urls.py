from django.conf.urls.defaults import *
from django.contrib.auth.views import login, logout

urlpatterns = patterns('roster.views',
    url(r'^$', 'front', name="front"),
    #(r'^readme$', 'readme'),    # use to preview readme.md
    url(r'^login/$', login, {'template_name': 'roster/login.html'}, "login"),
    url(r'^logout/$', logout, {'template_name': 'roster/logout.html'}, "logout"),
    url(r'^email/$', 'email_list', name="email_list"),
    url(r'^phone/$', 'phone_list', name="phone_list"),
    url(r'^contact/$', 'contact_list', name="contact_list"),
    url(r'^tshirt/$', 'tshirt_list', name="tshirt_list"),
    url(r'^event_email/$', 'event_email_list', name="event_email_list"),
    url(r'^team_reg_verify/$', 'team_reg_verify', name="team_reg_verify"),
    url(r'^class_team_list/$', 'class_team_list', name="class_team_list"),
    url(r'^signin_person_list/$', 'signin_person_list', name="signin_person_list"),
    url(r'^time_record_bulk_add/$', 'time_record_bulk_add', name="time_record_bulk_add"),
    #(r'^person/$', 'person_list'),
    #(r'^person/(?P<person_link>[\w-]+)$', 'person_detail'),
    #(r'^student/$', 'student_list'),
    #(r'^student/(?P<student_link>[\w-]+)$', 'student_detail'),
    #(r'^adult/$', 'student_list'),
    #(r'^adult/(?P<student_link>[\w-]+)$', 'adult_detail'),
)
