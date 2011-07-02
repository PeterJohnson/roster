# Roster views
from django.http import HttpResponse
from django.utils.html import escape, linebreaks
from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.template import RequestContext

from roster.models import *
from roster.forms import *

def front(request):
    return render_to_response("roster/front.html", locals(),
                              context_instance=RequestContext(request))

@login_required(login_url='/roster/login/')
def email_list(request):
    """Team email list."""

    if request.method == 'GET' and request.GET:
        form = EmailListForm(request.GET)
        if form.is_valid():
            results = PersonEmail.objects.none()

            # General team selections
            for formname, teamname in [('active_fll', 'FLL'),
                                       ('active_ftc', 'FTC'),
                                       ('active_frc', 'FRC')]:
                if formname in form.data:
                    results |= PersonEmail.objects.filter(
                        primary=True,
                        person__member__teams__name__contains=teamname,
                        person__member__status='Active')

            # FLL waitlist
            if 'fll_waitlist' in form.data:
                results |= PersonEmail.objects.filter(
                    primary=True,
                    person__in=WaitlistEntry.objects.filter(
                        program__name__contains='FLL').values('student'))

            # Filter down for various classes of people
            people = Member.objects.none()
            if 'Parent' in form.data['who']:
                people |= Member.objects.filter(adult__role='Parent')
            if 'Volunteer' in form.data['who']:
                people |= Member.objects.filter(adult__role='Volunteer')
            if 'Mentor' in form.data['who']:
                people |= Member.objects.filter(adult__mentor=True)
            if 'Student' in form.data['who']:
                people |= Member.objects.exclude(student=None)

            results = results.filter(person__in=people)

            # CC parents on emails if enabled.  Only does one level
            # (so if a parent has a CC on email, it won't get followed).
            if 'cc_on_email' in form.data:
                results |= PersonEmail.objects.filter(
                    primary=True,
                    person__relationship_from_set__person_from__in=results.values('person'),
                    person__relationship_from_set__cc_on_email=True)

            # Uniquify and get related info to avoid additional queries
            results = results.select_related('person', 'email.email').distinct()

            separator = form.data['separator']

    else:
        form = EmailListForm()

    return render_to_response("roster/email_list.html", locals(),
                              context_instance=RequestContext(request))

