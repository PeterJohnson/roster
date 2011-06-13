Roster
======

A team roster implemention built for django.

Setup
-----

* Clone the latest copy from github into your django project.
* Add the roster to your `INSTALLED_APPS` in `settings.py`:

        'roster',
    
* Add a url mapping to your project's `urls.py` file (an empty prefix will work, but put it last):

        (r'^roster/$', include('roster.urls')),
        
* Make sure you have a `MEDIA_ROOT` and `MEDIA_URL` set up in your `settings.py`:

        MEDIA_ROOT = '/home/www/mydjango-project/media/'

* Sync the database:

        % python manage.py syncdb
        
* Provide css and images at `{{MEDIA_URL}}roster/style`.

Administration
--------------

Administration is easiest through the django admin interface.
