# Roster views
from django.http import HttpResponse
from django.utils.html import escape, linebreaks
from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.template import RequestContext

from roster.models import *
from roster.forms import *

@login_required(login_url='/roster/login/')
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
            active = False

            # General team selections
            for formname, teamname in [('active_fll', 'FLL'),
                                       ('active_ftc', 'FTC'),
                                       ('active_frc', 'FRC')]:
                if formname in form.data:
                    results |= PersonEmail.objects.filter(
                        primary=True,
                        person__member__teams__name__contains=teamname,
                        person__member__status='Active')
                    active = True

            # FLL waitlist
            if 'fll_waitlist' in form.data:
                results |= PersonEmail.objects.filter(
                    primary=True,
                    person__in=WaitlistEntry.objects.filter(
                        program__name__contains='FLL').values('student'))
                active = True

            # Filter down for various classes of people
            who = form.data.getlist('who')
            people = Member.objects.none()
            if 'Parent' in who:
                people |= Member.objects.filter(adult__role='Parent')
            if 'Volunteer' in who:
                people |= Member.objects.filter(adult__role='Volunteer')
            if 'Mentor' in who:
                people |= Member.objects.filter(adult__mentor=True)
            if 'Student' in who:
                people |= Member.objects.exclude(student=None)

            results = results.filter(person__in=people)

            # CC parents on emails if enabled.  Only does one level
            # (so if a parent has a CC on email, it won't get followed).
            if active and 'cc_on_email' in form.data:
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

@login_required(login_url='/roster/login/')
def phone_list(request):
    """Team phone list."""

    if request.method == 'GET' and request.GET:
        form = PhoneListForm(request.GET)
        if form.is_valid():
            results = Person.objects.batch_select('phones').none()

            # General team selections
            for formname, teamname in [('active_fll', 'FLL'),
                                       ('active_ftc', 'FTC'),
                                       ('active_frc', 'FRC')]:
                if formname in form.data:
                    results |= Person.objects.batch_select('phones').filter(
                        member__teams__name__contains=teamname,
                        member__status='Active')

            # FLL waitlist
            if 'fll_waitlist' in form.data:
                results |= Person.objects.batch_select('phones').filter(
                    id__in=WaitlistEntry.objects.filter(
                        program__name__contains='FLL').values('student'))

            # Filter down for various classes of people
            who = form.data.getlist('who')
            parents = set()
            volunteers = set()
            mentors = set()
            students = set()
            if 'Parent' in who:
                parents = set(Adult.objects.filter(role='Parent').values_list('id', flat=True))
            if 'Volunteer' in who:
                volunteers = set(Adult.objects.filter(role='Volunteer').values_list('id', flat=True))
            if 'Mentor' in who:
                mentors = set(Adult.objects.filter(mentor=True).values_list('id', flat=True))
            if 'Student' in who:
                students = set(Student.objects.all().values_list('id', flat=True))
            people = parents|volunteers|mentors|students

            results = results.filter(id__in=people)

            # Uniquify and get related info to avoid additional queries
            results = results.distinct()

            final_results = []
            for result in results:
                name = result.render_normal()
                if result.id in parents:
                    role = "Parent"
                elif result.id in mentors:
                    role = "Mentor"
                elif result.id in volunteers:
                    role = "Volunteer"
                elif result.id in students:
                    role = "Student"
                else:
                    role = ""
                cell = ""
                home = ""
                for phone in result.phones_all:
                    if phone.location == 'Mobile':
                        cell = phone.render_normal()
                    elif phone.location == 'Home':
                        home = phone.render_normal()
                final_results.append(dict(name=name, role=role, cell=cell,
                                          home=home))

    else:
        form = PhoneListForm()

    return render_to_response("roster/phone_list.html", locals(),
                              context_instance=RequestContext(request))

@login_required(login_url='/roster/login/')
def event_email_list(request):
    """Event email list."""

    if request.method == 'GET' and request.GET:
        form = EventEmailListForm(request.GET)
        if form.is_valid():
            event_people = EventPerson.objects.filter(
                event=form.cleaned_data['event'],
                role__in=form.cleaned_data['who'])

            results = PersonEmail.objects.filter(
                primary=True,
                person__in=event_people.values('person'))

            # CC parents on emails if enabled.  Only does one level
            # (so if a parent has a CC on email, it won't get followed).
            if form.data['who'] and 'cc_on_email' in form.data:
                results |= PersonEmail.objects.filter(
                    primary=True,
                    person__relationship_from_set__person_from__in=results.values('person'),
                    person__relationship_from_set__cc_on_email=True)

            # Uniquify and get related info to avoid additional queries
            results = results.select_related('person', 'email.email').distinct()

            separator = form.data['separator']
    else:
        form = EventEmailListForm()

    return render_to_response("roster/email_list.html", locals(),
                              context_instance=RequestContext(request))

