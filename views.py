# Roster views
from django.http import HttpResponse
from django.utils.html import escape, linebreaks
from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.db.models import Q

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
            who = set(form.data.getlist('who'))
            include_parents = 'Parent' in who
            who.discard('Parent')

            people = PersonTeam.objects.filter(role__in=who,
                    status__in=form.data.getlist('status'),
                    team__in=form.data.getlist('team')).values('person')

            results = PersonEmail.objects.filter(primary=True, person__in=people)

            # Follow relationship to parents from students if enabled.
            if include_parents:
                students = PersonTeam.objects.filter(role='Student',
                        status__in=form.data.getlist('status'),
                        team__in=form.data.getlist('team')).values('person')
                parents = Relationship.objects.filter(person_from__in=students,
                        relationship__type__in=['Father', 'Mother']).values('person_to')
                results |= PersonEmail.objects.filter(primary=True, person__in=parents)

            # CC on emails if enabled.  Only does one level.
            if results and 'cc_on_email' in form.data:
                cc = Relationship.objects.filter(person_from__in=people,
                        cc_on_email=True).values('person_to')
                results |= PersonEmail.objects.filter(primary=True, person__in=cc)

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
            who = set(form.data.getlist('who'))
            include_parents = 'Parent' in who
            who.discard('Parent')

            status = form.data.getlist('status')
            teams = sorted(form.data.getlist('team'))
            team_index = dict((int(x[1]), x[0]) for x in enumerate(teams))
            print team_index

            people = PersonTeam.objects.filter(role__in=who,
                    status__in=status, team__in=teams).values('person')

            results = Person.objects.batch_select('phones').filter(id__in=people)

            # Follow relationship to parents from students if enabled.
            if include_parents:
                students = PersonTeam.objects.filter(role='Student',
                        status__in=form.data.getlist('status'),
                        team__in=form.data.getlist('team')).values('person')
                parents = Relationship.objects.filter(person_from__in=students,
                        relationship__type__in=['Father', 'Mother'])
                parents_map = dict(parents.values_list('person_to', 'person_from'))
                results |= Person.objects.batch_select('phones').filter(
                        id__in=parents_map.keys())

            # Uniquify and get related info to avoid additional queries
            results = results.distinct()

            final_results = []
            for result in results:
                name = result.render_normal()

                roles = [""]*len(teams)
                if include_parents and result.id in parents_map:
                    for x in PersonTeam.objects.filter(person__id=parents_map[result.id],
                            status__in=status, team__in=teams):
                        roles[team_index[x.team.id]] = "%sParent" % \
                            (x.status == 'Prospective' and "Prospective " or "",)

                for x in PersonTeam.objects.filter(person=result,
                        status__in=status, team__in=teams):
                    roles[team_index[x.team.id]] = "%s%s" % \
                         (x.status == 'Prospective' and "Prospective " or "",
                          x.role)

                cell = ""
                home = ""
                for phone in result.phones_all:
                    if phone.location == 'Mobile':
                        cell = phone.render_normal()
                    elif phone.location == 'Home':
                        home = phone.render_normal()
                final_results.append(dict(name=name, roles=roles, cell=cell,
                                          home=home))

            teams = Team.objects.filter(id__in=teams).order_by('id')
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
            people = EventPerson.objects.filter(
                event=form.cleaned_data['event'],
                role__in=form.cleaned_data['who']).values('person')

            results = PersonEmail.objects.filter(primary=True, person__in=people)

            # CC parents on emails if enabled.  Only does one level
            # (so if a parent has a CC on email, it won't get followed).
            if people and 'cc_on_email' in form.data:
                cc = Relationship.objects.filter(person_from__in=people,
                        cc_on_email=True).values('person_to')
                results |= PersonEmail.objects.filter(primary=True, person__in=cc)

            # Uniquify and get related info to avoid additional queries
            results = results.select_related('person', 'email.email').distinct()

            separator = form.data['separator']
    else:
        form = EventEmailListForm()

    return render_to_response("roster/email_list.html", locals(),
                              context_instance=RequestContext(request))

@login_required(login_url='/roster/login/')
def team_reg_verify(request):
    """Team registration verification."""

    if request.method == 'GET' and request.GET:
        form = TeamRegVerifyForm(request.GET)
        if form.is_valid():
            people = PersonTeam.objects.filter(
                    role__in=form.data.getlist('who'),
                    status='Active',
                    team__in=form.data.getlist('team')).values('person')

            people = Person.objects.filter(id__in=people)

            parent_relationships = RelationshipType.objects.filter(parent=True).values_list('id', flat=True)

            results = []
            for person in people:
                r = {}
                r["person"] = person
                if person.gender == 'M':
                    r["gender"] = "Male"
                elif person.gender == 'F':
                    r["gender"] = "Female"
                else:
                    r["gender"] = ""
                r["emails"] = PersonEmail.objects.filter(person=person)
                r["addresses"] = person.addresses.all()
                r["phones"] = PersonPhone.objects.filter(person=person)

                parents = Relationship.objects.filter(
                        person_from=person,
                        relationship__in=parent_relationships) \
                                .select_related('person_to')
                r["parents"] = []
                for x in parents:
                    parent = {}
                    parent["person"] = x.person_to
                    parent["relationship"] = x.relationship
                    parent["cc_on_email"] = x.cc_on_email
                    parent["emergency_contact"] = x.emergency_contact
                    parent["emails"] = PersonEmail.objects.filter(person=x.person_to)
                    parent["addresses"] = x.person_to.addresses.all()
                    parent["phones"] = PersonPhone.objects.filter(person=x.person_to)
                    r["parents"].append(parent)

                r["emergency"] = []
                for x in Relationship.objects.filter(
                        person_from=person, emergency_contact=True) \
                        .exclude(id__in=parents.values('id')) \
                        .select_related('person_to'):
                    contact = {}
                    contact["person"] = x.person_to
                    contact["relationship"] = x.relationship
                    contact["phones"] = PersonPhone.objects.filter(person=x.person_to)
                    r["emergency"].append(contact)

                results.append(r)
    else:
        form = TeamRegVerifyForm()

    return render_to_response("roster/team_reg_verify.html", locals(),
                              context_instance=RequestContext(request))

