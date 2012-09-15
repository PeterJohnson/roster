# Roster views
from django.http import HttpResponse
from django.utils.html import escape, linebreaks
from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.db.models import Q, Count
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.contrib.formtools.wizard.views import SessionWizardView

from settings import MEDIA_ROOT

from roster.models import *
from roster.forms import *

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, BaseDocTemplate, SimpleDocTemplate, Table, TableStyle, PageBreak, ActionFlowable, Frame, PageTemplate
from reportlab.platypus.flowables import Flowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.graphics.barcode import code39

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
pdfmetrics.registerFont(TTFont('Calibri', 'calibri.ttf'))
pdfmetrics.registerFont(TTFont('Calibri-Bold', 'calibrib.ttf'))
pdfmetrics.registerFont(TTFont('Calibri-Italic', 'calibrii.ttf'))

import os
import csv
import math

team_color1 = (55.0/255.0, 88.0/255.0, 150.0/255.0)
team_color2 = (236.0/255.0, 108.0/255.0, 29.0/255.0)

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
                parent_relationships = RelationshipType.objects.filter(parent=True).values('id')
                students = PersonTeam.objects.filter(role='Student',
                        status__in=form.data.getlist('status'),
                        team__in=form.data.getlist('team')).values('person')
                parents = Relationship.objects.filter(person_from__in=students,
                        relationship__in=parent_relationships).values('person_to')
                results |= PersonEmail.objects.filter(primary=True, person__in=parents)

            # CC on emails if enabled.  Only does one level.
            if results and 'cc_on_email' in form.data:
                cc = Relationship.objects.filter(person_from__in=people,
                        cc_on_email=True).values('person_to')
                results |= PersonEmail.objects.filter(primary=True, person__in=cc)

            # Uniquify and get related info to avoid additional queries
            results = results.select_related('person', 'email.email').distinct()

            include_name = 'include_name' in form.data
            separator = form.data['separator']

    else:
        form = EmailListForm()

    return render_to_response("roster/email_list.html", locals(),
                              context_instance=RequestContext(request))

@login_required(login_url='/roster/login/')
def contact_list(request):
    """Team contact list (phone and email)."""

    if request.method == 'GET' and request.GET:
        form = ContactListForm(request.GET)
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

            results = Person.objects.batch_select('phones')\
                    .filter(id__in=people)

            # Follow relationship to parents from students if enabled.
            if include_parents:
                parent_relationships = RelationshipType.objects.filter(parent=True).values('id')
                students = PersonTeam.objects.filter(role='Student',
                        status__in=form.data.getlist('status'),
                        team__in=form.data.getlist('team')).values('person')
                parents = Relationship.objects.filter(person_from__in=students,
                        relationship__in=parent_relationships)
                parents_map = dict(parents.values_list('person_to', 'person_from'))
                results |= Person.objects.batch_select('phones')\
                        .filter(id__in=parents_map.keys())

            # Uniquify and get related info to avoid additional queries
            results = results.distinct()

            cc_on_email = 'cc_on_email' in form.data
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

                emails = [pe.email for pe in
                        PersonEmail.objects.filter(primary=True, person=result)]
                cc_emails = []
                if cc_on_email:
                    cc = Relationship.objects.filter(person_from=result,
                            cc_on_email=True).values('person_to')
                    cc_emails = sorted(set(pe.email for pe in
                            PersonEmail.objects.filter(primary=True, person__in=cc)))

                final_results.append(dict(name=name, roles=roles, cell=cell,
                                          home=home, emails=emails,
                                          cc_emails=cc_emails))

            teams = Team.objects.filter(id__in=teams).order_by('id')
    else:
        form = ContactListForm()

    return render_to_response("roster/contact_list.html", locals(),
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
                parent_relationships = RelationshipType.objects.filter(parent=True).values('id')
                students = PersonTeam.objects.filter(role='Student',
                        status__in=form.data.getlist('status'),
                        team__in=form.data.getlist('team')).values('person')
                parents = Relationship.objects.filter(person_from__in=students,
                        relationship__in=parent_relationships)
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
def tshirt_list(request):
    """Team T-shirt list."""

    if request.method == 'GET' and request.GET:
        form = TshirtListForm(request.GET)
        if form.is_valid():
            who = set(form.data.getlist('who'))
            include_parents = 'Parent' in who
            who.discard('Parent')

            people = PersonTeam.objects.filter(role__in=who,
                    status__in=form.data.getlist('status'),
                    team__in=form.data.getlist('team')).values('person')

            results = Person.objects.filter(id__in=people)

            # Follow relationship to parents from students if enabled.
            if include_parents:
                parent_relationships = RelationshipType.objects.filter(parent=True).values('id')
                students = PersonTeam.objects.filter(role='Student',
                        status__in=form.data.getlist('status'),
                        team__in=form.data.getlist('team')).values('person')
                parents = Relationship.objects.filter(person_from__in=students,
                        relationship__in=parent_relationships).values('person_to')
                results |= Person.objects.filter(id__in=parents)

            totals_dict = {}
            for tot in results.values('shirt_size').annotate(Count('shirt_size')).order_by():
                totals_dict[tot["shirt_size"]] = tot["shirt_size__count"]

            totals = []
            totals.append(dict(shirt_size="",
                               shirt_size__count=totals_dict[""]))
            for size_short, size_long in Person.SHIRT_SIZE_CHOICES:
                if size_short not in totals_dict:
                    continue
                totals.append(dict(shirt_size=size_long,
                                   shirt_size__count=totals_dict[size_short]))

    else:
        form = TshirtListForm()

    return render_to_response("roster/tshirt_list.html", locals(),
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

            include_name = 'include_name' in form.data
            separator = form.data['separator']
    else:
        form = EventEmailListForm()

    return render_to_response("roster/email_list.html", locals(),
                              context_instance=RequestContext(request))

@login_required(login_url='/roster/login/')
def class_team_list(request):
    """List of people showing their team membership."""

    if request.method == 'GET' and request.GET:
        form = ClassTeamListForm(request.GET)
        if form.is_valid():
            results = Person.objects.filter(
                    grad_year__gte=form.data["class_begin"],
                    grad_year__lte=form.data["class_end"])

            exclude_people = PersonTeam.objects\
                    .filter(person__in=results.values('id'))\
                    .exclude(status__in=('Active', 'Prospective'))\
                    .values('person')
            results = results.exclude(id__in=exclude_people)

            if 'no_team' in form.data:
                exclude_people = PersonTeam.objects\
                        .filter(person__in=results.values('id'))\
                        .values('person')
                results = results.exclude(id__in=exclude_people)
    else:
        form = ClassTeamListForm()

    return render_to_response("roster/class_team_list.html", locals(),
                              context_instance=RequestContext(request))


class Checkbox(Flowable):
    """A checkbox flowable."""
    def __init__(self, checked, size=0.25*inch, color=colors.black):
        self.checked = checked
        self.size = size

    def wrap(self, *args):
        return (0, self.size)

    def draw(self):
        canvas = self.canv
        canvas.setLineWidth(1)
        canvas.setStrokeColor(self.color)
        canvas.rect(0, 0, self.size, self.size)
        if self.checked:
            canvas.line(0, 0, self.size, self.size)
            canvas.line(0, self.size, self.size, 0)

class StartPerson(ActionFlowable):
    def __init__(self, id, firstname, lastname, suffix, adult, team):
        ActionFlowable.__init__(self, ('startPerson', id, firstname,
            lastname, suffix, adult, team))

class RegVerifyDocTemplate(BaseDocTemplate):
    _invalidInitArgs = ('pageTemplates')

    def afterInit(self):
        self.name = None
        self.id = None
        self.team = None
        self.adult = False

        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id='normal')
        self.addPageTemplates([PageTemplate(id='First',frames=frame,onPageEnd=self.afterFirstPage,pagesize=self.pagesize),
                               PageTemplate(id='Later',frames=frame,onPageEnd=self.afterNextPage,pagesize=self.pagesize)])

    def afterFirstPage(self, canv, self2):
        #self.pageTemplate = self.pageTemplates[1]

        # Name in upper left corner
        canv.setFont("Calibri-Bold", 14)
        canv.setFillColor(colors.black)
        canv.drawString(0.5*inch, self.pagesize[1]-0.5*inch, self.name)

        # Box with first letter of last name in upper right corner
        # Color it based on adult
        wh = 0.375*inch
        c = (self.pagesize[0]-0.75*inch, self.pagesize[1]-0.5*inch)
        canv.setFillColor(self.adult and team_color2 or team_color1)
        canv.rect(c[0]-wh/2, c[1]-wh/2,
                  wh, wh, fill=1, stroke=0)

        lsize = 30
        canv.setFillColor(colors.black)
        canv.setFont("Calibri-Bold", lsize)
        canv.drawCentredString(c[0], c[1]-lsize/2/1.4, self.name[0].upper())

        # Admin fields
        canv.setStrokeColor(colors.black)
        canv.setFillColor(colors.black)
        canv.setLineWidth(1)
        title = "Administration Only"
        title_width = canv.stringWidth(title, "Calibri-Italic", 8)
        canv.line(0.5*inch, 0.7*inch,
                  self.pagesize[0]/2-title_width/2, 0.7*inch)
        canv.line(self.pagesize[0]/2+title_width/2, 0.7*inch,
                  self.pagesize[0]-0.5*inch, 0.7*inch)
        #canv.line(0.5*inch, 0.7*inch, self.pagesize[0]-0.5*inch, 0.7*inch)
        canv.setFont("Calibri-Italic", 8)
        canv.drawCentredString(self.pagesize[0]/2, 0.675*inch, title)
        canv.setFont("Calibri", 8)
        canv.setLineWidth(0.5)
        for r, c, sw, vw, s, v in \
                [(0, 0, 0.75, 0.5, "Id:", "%d" % self.id),
                 (1, 0, 0.75, 0.5, "Printed On:",
                  self.today.strftime("%b %-d, %Y")),
                 (0, 1, 0.75, 0.5, "Cash/Check #", None),
                 (1, 1, 0.75, 0.5, "Amount:", None),
                 (0, 2, 0.75, 0.5, "Team:", self.team),
                 (1, 2, 0.75, 0.5, "Paid Date:", None),
                 (0, 3, 1, 0.25, "Release Form:", None),
                 (1, 3, 1, 0.25, "Student Contract:", None)]:
            x = 0.5*inch + c*2*inch
            y = 0.5*inch - r*0.125*inch
            canv.drawString(x, y, s)
            if v is None:
                canv.line(x+sw*inch, y, x+(sw+vw)*inch, y)
            else:
                canv.drawString(x+sw*inch, y, v)

    def afterNextPage(self, canv, self2):
        pass

    def handle_startPerson(self, id, firstname, lastname, suffix, adult,
                           team):
        #self.pageTemplate = self.pageTemplates[0]
        self.name = "%s, %s %s" % (lastname, firstname, suffix)
        self.id = id
        self.adult = adult
        self.team = team

def person_to_pdf(elements, person, title, adult=False, parent=None,
                  contact=None):
    base_style = [
        # default font and text color for table
        ('FONT', (0,0), (-1,-1), 'Calibri', 8),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.black),
        # default to top alignment for table
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        # reduce padding for table
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        # bold first column
        ('FONT', (0,0), (0,-1), 'Calibri-Bold', 8),
        # set up header row
        ('BACKGROUND', (0,0), (-1,0), team_color1),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('SPAN', (0,0), (-1,0)),
        # lines around the table, between each row, and between cols 2 and 3
        ('BOX', (0,0), (-1,-1), 1, colors.black),
        ('LINEBELOW', (0,0), (-1,-1), 1, colors.black),
        ('LINEAFTER', (1,1), (1,-1), 1, colors.black),
        ]
    if person:
        empty_person = False
        def highlight(style, data):
            style.add('BACKGROUND', (2,len(data)), (2,len(data)), colors.yellow)
    else:
        empty_person = True
        def highlight(style, data):
            pass
        person = Person()

    data = []
    style = TableStyle(base_style)

    # Basic information
    data.append((title, "", ""))
    data.append(((parent or contact) and "Name" or "Legal Name",
        "First and Last",
        "%s %s %s" % (person.firstname, person.lastname, person.suffix)))
    if isinstance(contact, Relationship):
        style.add('SPAN', (0,len(data)-1), (0,len(data)))
        data.append(("", "Relationship", contact.relationship))
    elif contact or (parent and not isinstance(parent, Relationship)):
        style.add('SPAN', (0,len(data)-1), (0,len(data)))
        data.append(("", "Relationship", ""))

    if not parent and not contact:
        data.append(("Nickname", "", person.nickname))
        if not person.gender or person.gender == 'U':
            highlight(style, data)
        data.append(("Gender", "", person.get_gender_display()))
        if not person.birth_month or not person.birth_day or person.birth_year is not None and (person.birth_year > 2050 or person.birth_year < 1900):
            highlight(style, data)
        data.append(("Date of Birth", "m/d/yyyy", not empty_person and
            "%s / %s / %s" % (person.birth_month, person.birth_day, person.birth_year) or ""))

    # - School
    if not adult:
        if not person.school:
            highlight(style, data)
        data.append(("School", "", person.school))
        if not person.grad_year:
            highlight(style, data)
        data.append(("HS Graduation Year", "", person.grad_year))

    if not contact:
        # - Company
        if adult and not person.company:
            highlight(style, data)
        data.append(("Company", "", person.company))

        # - Shirt Size
        if not parent:
            if not person.shirt_size:
                highlight(style, data)
            data.append(("Shirt Size", "", person.shirt_size))

        # Parent specific info
        #if isinstance(parent, Relationship):
        #    data.append(("Emergency Contact", "",
        #        parent.emergency_contact and "Yes" or "No"))
        #elif parent:
        #    data.append(("Emergency Contact", "", "Yes / No"))

        # Emails
        emails = PersonEmail.objects.filter(person=person)
        start = len(data)
        first = "Email"
        for email in emails:
            data.append((first, email.email.location, "%s%s" %
                (email.email.email, email.primary and " (primary)" or "")))
            first = ""
        if not emails:
            data.append((first, "Address", ""))
            first = ""
        # - Parent specific info
        if isinstance(parent, Relationship):
            data.append((first, "CC on Student Emails",
                parent.cc_on_email and "Yes" or "No"))
            first = ""
        elif parent:
            data.append((first, "CC on Student Emails", "Yes / No"))
            first = ""
        if len(data)-1 > start:
            style.add('SPAN', (0,start), (0,len(data)-1))

    # Phones
    phones = PersonPhone.objects.filter(person=person)
    wanted_phone_locations = set([u'Cell', u'Home', u'Work'])
    start = len(data)
    first = "Phone"
    for phone in phones:
        location = phone.phone.get_location_display()
        wanted_phone_locations.discard(location)
        data.append((first, location, "%s%s" %
            (phone.phone.render_normal(),
             phone.primary and " (primary)" or "")))
        first = ""
    for location in sorted(wanted_phone_locations):
        #highlight(style, data)
        data.append((first, location, ""))
        first = ""
    if len(data)-1 > start:
        style.add('SPAN', (0,start), (0,len(data)-1))

    if not contact:
        # Addresses
        addresses = not empty_person and person.addresses.all() or []
        for address in addresses:
            style.add('SPAN', (0,len(data)), (0,len(data)+2))
            data.append(("Address", "Line 1", address.line1))
            data.append(("", "Line 2", address.line2))
            data.append(("", "City, State, Zip", "%s, %s %s" %
                (address.city, address.state, address.zipcode)))
        if not addresses:
            style.add('SPAN', (0,len(data)), (0,len(data)+2))
            highlight(style, data)
            data.append(("Address", "Line 1", ""))
            highlight(style, data)
            data.append(("", "Line 2", ""))
            highlight(style, data)
            data.append(("", "City, State, Zip", ""))

        # Medical
        if not parent:
            style.add('SPAN', (0,len(data)), (0,len(data)+1))
            #if not person.medical:
            #    highlight(style, data)
            data.append(("Medical", "Conditions/Allergies", person.medical))
            #if not person.medications:
            #    highlight(style, data)
            data.append(("", "Medications", person.medications))

    elements.append(Table(data, colWidths=(0.75*inch, 1.25*inch, 5*inch),
                    style=style))

def make_reg_verify_pdf(response, people):
    from datetime import date
    today = date.today()

    doc = RegVerifyDocTemplate(response,
            pagesize=letter,
            allowSplitting=0,
            leftMargin=0.5*inch,
            rightMargin=0.5*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch,
            title="Team Registration Verification",
            author="Beach Cities Robotics")
    doc.today = today

    # container for the 'Flowable' objects
    elements = []

    styles = getSampleStyleSheet()
    normal_para_style = styles['Normal']

    parent_relationships = RelationshipType.objects.filter(parent=True).values_list('id', flat=True)

    for person in people:
        adult = person.company or \
                (person.birth_year and person.birth_year > 1900 and
                 (today.year - person.birth_year) > 20)
        team = None
        pts = PersonTeam.objects.filter(person=person, status='Active')
        if pts:
            team = "%s" % pts[0].team
        elements.append(StartPerson(person.id, person.firstname,
                                    person.lastname, person.suffix, adult,
                                    team))
        person_to_pdf(elements, person,
                "%s Information" % (adult and "Mentor" or "Student"),
                adult=adult)
        elements.append(Paragraph("", normal_para_style))

        parents = []
        if not adult:
            # Parents
            parents = Relationship.objects.filter(
                    person_from=person,
                    legal_guardian=True) \
                            .select_related('person_to')
            extra_parents = [1, 2]
            for parent in parents:
                person_to_pdf(elements, parent.person_to,
                    "%s's Information" % parent.relationship,
                    adult=True,
                    parent=parent)
                elements.append(Paragraph("", normal_para_style))
            for parent in extra_parents[len(parents):]:
                person_to_pdf(elements, None,
                    "Legal Guardian %d Information" % parent,
                    adult=True,
                    parent=True)
                elements.append(Paragraph("", normal_para_style))
            parents = parents.values('id')

        # Emergency Contacts
        if adult:
            contacts = Relationship.objects.filter(
                    person_from=person, emergency_contact=True) \
                    .exclude(id__in=parents) \
                    .select_related('person_to')
            for contact in contacts:
                person_to_pdf(elements, contact.person_to,
                    "Emergency Contact Information",
                    adult=True,
                    contact=contact)
                elements.append(Paragraph("", normal_para_style))
            if not contacts:
                person_to_pdf(elements, None,
                    "Emergency Contact Information",
                    adult=True,
                    contact=True)
        elements.append(PageBreak())

    # Generate the document
    doc.build(elements)

@login_required(login_url='/roster/login/')
def team_reg_verify(request):
    """Team registration verification."""
    if request.method != 'GET' or not request.GET:
        form = TeamRegVerifyForm()
        return render_to_response("roster/team_reg_verify.html", locals(),
                                  context_instance=RequestContext(request))

    form = TeamRegVerifyForm(request.GET)
    if not form.is_valid():
        return render_to_response("roster/team_reg_verify.html", locals(),
                                  context_instance=RequestContext(request))

    # configure PDF output
    response = HttpResponse(mimetype='application/pdf')
    response['Content-Disposition'] = 'attachment; filename=TeamRegVerify.pdf'
    people = PersonTeam.objects.filter(
            role__in=form.data.getlist('who'),
            status='Active',
            team__in=form.data.getlist('team')).values('person')

    people = Person.objects.filter(id__in=people)
    make_reg_verify_pdf(response, people)
    return response

@login_required(login_url='/roster/login/')
def signin_person_list(request):
    """Basic easy to parse list of people for signin application."""

    parent_relationships = RelationshipType.objects.filter(parent=True).values_list('id', flat=True)

    people = PersonTeam.objects.filter(status='Active').values('person')
    results = Person.objects.all()#filter(id__in=people)
    #results = results.distinct()

    response = HttpResponse(mimetype='text/csv')
    response['Content-Disposition'] = 'attachment; filename=signin_person_list.csv'

    writer = csv.writer(response)
    writer.writerow(['id', 'name', 'student', 'photo', 'photo size', 'badge'])
    for person in results:
        name = person.render_normal()
        student = person.is_student(parent_relationships)

        # Default to adult if we can't figure out if this is a student or not.
        if student is None:
            student = False

        photourl = ''
        photosize = 0
        if person.photo:
            photourl = person.photo.url
            photosize = person.photo.file.size
        writer.writerow([person.id, name, student, photourl, photosize, person.get_badge()])

    return response

@login_required(login_url='/roster/login/')
@csrf_exempt
@transaction.commit_on_success
def time_record_bulk_add(request):
    """Bulk time record entry for signin application."""

    from datetime import datetime
    def fromiso(t):
        try:
            return datetime.strptime(t, "%Y-%m-%d %H:%M:%S.%f")
        except:
            return datetime.strptime(t, "%Y-%m-%d %H:%M:%S")

    errs = []
    ok = []
    for count, row in enumerate(csv.DictReader(request)):
        try:
            person = Person.objects.get(id=int(row["person"]))
            event = row.get("event", None)
            if event:
                event = Event.objects.get(id=int(event))
            else:
                event = None
            record = TimeRecord(
                    person=person,
                    event=event,
                    clock_in=fromiso(row["clock_in"]),
                    clock_out=fromiso(row["clock_out"]),
                    hours=float(row["hours"]),
                    recorded=fromiso(row["recorded"]),
                    )
            record.save()
            ok.append(count)
        except Exception as e:
            errs.append("%d (%s): %s" % (count, row.get("person", ""), str(e)))

    return HttpResponse(str(ok)+"\n"+"\n".join(errs), content_type="text/plain")

class Badge(Flowable):
    """A badge flowable."""
    # badge dimensions
    width = 2.25*inch
    height = 3.5*inch

    # border thickness
    border_size = 0.125*inch

    # logo location and size
    logo = 0
    logo_width = 0.5*inch
    logo_height = 0.75*inch
    logo_x = width - logo_width - 0.125*inch
    logo_y = height - logo_height - 0.125*inch

    # team name location and size
    team_font = 'Calibri-Bold'
    team_fontsize = 18
    team_x = width / 2.0
    team_y = (1/16.0)*inch
    team_name = "Beach Cities Robotics"

    # photo location and size
    photo_width = 1.25*inch
    photo_height = 1.5*inch
    photo_x = (1/16.0)*inch
    photo_y = height - photo_height - (3/16.0)*inch
    photo_corner = 0.125*inch  # rounded corner radius

    # name location and size
    fullname_font = 'Calibri'
    fullname_fontsize = 10
    fullname_x = 0.125*inch
    fullname_y = photo_y - 0.125*inch
    firstname_font = 'Calibri-Bold'
    firstname_fontsize = 24
    firstname_x = 0.125*inch
    firstname_y = fullname_y - 0.3*inch

    # position location and size
    position_font = 'Calibri'
    position_fontsize = 14
    position_x = 0.125*inch
    position_y = 1*inch
    position_width = width - position_x - 0.125*inch
    position_height = 0.5*inch

    # id font
    id_font = 'Calibri'
    id_fontsize = 8

    # barcode location and size
    barcode_x = 0
    barcode_y = 0.375*inch

    def __init__(self, person, student):
        self.styles = getSampleStyleSheet()
        self.person = person
        self.student = student

    def wrap(self, *args):
        return (0, self.height)

    def draw(self):
        canvas = self.canv
        canvas.saveState()
        canvas.setLineWidth(1)
        canvas.setStrokeColor(colors.black)
        canvas.setFillColor(colors.black)

        # clip to badge boundary
        p = canvas.beginPath()
        p.rect(0, 0, self.width, self.height)
        canvas.clipPath(p)

        # Badge outline / background
        canvas.saveState()
        if self.student:
            color1 = team_color2
            color2 = team_color1
        else:
            color1 = team_color1
            color2 = team_color2
        canvas.radialGradient(0, 0,
                math.sqrt(self.width*self.width+self.height*self.height),
                [colors.white, color1], [0.10, 1])

        canvas.setFillColor(color2)
        canvas.rect(0, 0, self.width, 0.3*inch, stroke=0, fill=1)

        canvas.drawPath(p)
        canvas.restoreState()

        # Team logo
        if self.logo:
            canvas.drawImage(os.path.join(MEDIA_ROOT, "logo.jpeg"),
                    self.logo_x, self.logo_y, self.logo_width, self.logo_height,
                    preserveAspectRatio=True)

        # Team name
        canvas.saveState()
        canvas.setFillColor(colors.black)
        canvas.setFont(self.team_font, self.team_fontsize)
        canvas.drawCentredString(self.team_x, self.team_y, self.team_name)
        canvas.restoreState()

        # Photo
        if self.person.photo:
            # round corners by using a clip path
            canvas.saveState()
            p = canvas.beginPath()
            p.roundRect(self.photo_x, self.photo_y, self.photo_width,
                    self.photo_height, self.photo_corner)
            canvas.clipPath(p, stroke=0)

            # load image
            photopath = os.path.join(MEDIA_ROOT, self.person.photo.name)
            img = ImageReader(photopath)

            # scale/center image so it fills entire area
            imgw, imgh = img.getSize()
            newimgw, newimgh = imgw, imgh
            rw = int(imgh * self.photo_width / self.photo_height)
            if rw <= imgw:
                newimgw = rw
            else:
                newimgh = int(imgw * self.photo_height / self.photo_width)
            width = self.photo_width*((1.0*imgw)/newimgw)
            height = self.photo_height*((1.0*imgh)/newimgh)
            x = self.photo_x - (width-self.photo_width)/2.0
            y = self.photo_y - (height-self.photo_height)/2.0

            # draw image
            canvas.drawImage(img, x, y, width, height)

            # restore state (clip path)
            canvas.restoreState()
        else:
            canvas.saveState()
            canvas.setFillColor(colors.white)
            canvas.roundRect(self.photo_x, self.photo_y, self.photo_width,
                    self.photo_height, self.photo_corner, stroke=1, fill=1)
            canvas.restoreState()

        # Name
        canvas.saveState()
        fullname = "%s, %s %s" % (self.person.lastname, self.person.firstname, self.person.suffix)
        canvas.setFont(self.fullname_font, self.fullname_fontsize)
        canvas.drawString(self.fullname_x, self.fullname_y, fullname)
        canvas.restoreState()

        canvas.saveState()
        canvas.setFont(self.firstname_font, self.firstname_fontsize)
        canvas.drawString(self.firstname_x, self.firstname_y, self.person.get_firstname())
        canvas.restoreState()

        # Position
        position = str(self.person.position)
        if not position:
            if self.student:
                position = "Student"
            else:
                position = "Mentor"
        t = '<font name="%s" size="%d">%s</font>' % \
                (self.position_font, self.position_fontsize, escape(position))
        p = Paragraph(t, style=self.styles['Normal'])
        p.wrapOn(canvas, self.position_width, self.position_height)
        p.drawOn(canvas, self.position_x, self.position_y)

        # Barcode
        idstr = "B%05d" % self.person.get_badge()
        canvas.saveState()
        barcode = code39.Standard39(idstr, humanReadable=0, checksum=1)
        canvas.setFillColor(colors.black)
        barcode.drawOn(canvas, self.barcode_x, self.barcode_y)
        canvas.restoreState()

        # ID
        idstr = "%d" % self.person.get_badge()
        canvas.saveState()
        canvas.setFont(self.id_font, self.id_fontsize)
        canvas.drawString(self.barcode_x + barcode.lquiet,
                self.barcode_y + barcode.height + 3, idstr)
        canvas.restoreState()

        canvas.restoreState()

class BadgesDocTemplate(BaseDocTemplate):
    _invalidInitArgs = ('pageTemplates')

    def afterInit(self):
        width = 2.25*inch
        left = self.leftMargin
        frames = [Frame(self.leftMargin+width*x, self.bottomMargin, width,
            self.height, leftPadding=0, bottomPadding=0, rightPadding=0,
            topPadding=0) for x in range(4)]
        self.addPageTemplates([PageTemplate(id='Page',frames=frames,pagesize=self.pagesize)])

@login_required(login_url='/roster/login/')
def badges(request):
    """Badge generation."""
    if request.method != 'GET' or not request.GET:
        form = BadgesForm()
        return render_to_response("roster/badges.html", locals(),
                                  context_instance=RequestContext(request))

    ids = request.GET.getlist("ids")
    if not ids:
        form = BadgesForm(request.GET)
        if not form.is_valid():
            return render_to_response("roster/badges.html", locals(),
                                      context_instance=RequestContext(request))

        # generate list of people
        people = PersonTeam.objects.filter(
                role__in=form.data.getlist('who'),
                status='Active',
                team__in=form.data.getlist('team')).values('person')
        people = Person.objects.filter(id__in=people)
        return render_to_response("roster/badges.html", locals(),
                                  context_instance=RequestContext(request))

    # configure PDF output
    response = HttpResponse(mimetype='application/pdf')
    response['Content-Disposition'] = 'attachment; filename=Badges.pdf'
    doc = BadgesDocTemplate(response,
            pagesize=landscape(letter),
            allowSplitting=0,
            leftMargin=1*inch,
            rightMargin=1*inch,
            topMargin=0.75*inch,
            bottomMargin=0.5*inch,
            title="Badges",
            author="Beach Cities Robotics")

    # container for the 'Flowable' objects
    elements = []

    styles = getSampleStyleSheet()
    normal_para_style = styles['Normal']

    parent_relationships = RelationshipType.objects.filter(parent=True).values_list('id', flat=True)

    people = Person.objects.filter(id__in=[int(x) for x in ids])

    for person in people:
        student = person.is_student(parent_relationships)
        elements.append(Badge(person, student))
        elements.append(Paragraph("", normal_para_style))

    # Generate the document
    doc.build(elements)
    return response

REG_FORMS = [
        ("initial", RegInitialForm),
        ("basic", RegBasicForm),
        ("address", AddressForm),
        ("phone", RegPhoneForm),
        ("guardian1", RegGuardian1Form),
        ("guardian1address", RegGuardian1AddressForm),
        ("guardian1phone", RegPhoneForm),
        ("guardian2", RegGuardian2Form),
        ("guardian2address", RegGuardian2AddressForm),
        ("guardian2phone", RegPhoneForm),
        ("email", RegEmailForm),
        ("emergency", RegEmergencyForm),
        ("emergencyphone", RegPhoneForm),
        ("team", RegTeamForm),
        ]

REG_TEMPLATES = {
        "initial": "roster/reg/initial.html",
        "basic": "roster/reg/basic.html",
        "phone": "roster/reg/phone.html",
        "guardian1": "roster/reg/guardian.html",
        "guardian1address": "roster/reg/guardian_address.html",
        "guardian1phone": "roster/reg/phone.html",
        "guardian2": "roster/reg/guardian.html",
        "guardian2address": "roster/reg/guardian_address.html",
        "guardian2phone": "roster/reg/phone.html",
        "email": "roster/reg/email.html",
        "emergency": "roster/reg/guardian.html",
        "emergencyphone": "roster/reg/phone.html",
        }

def show_reg_guardian_form_condition(wizard):
    data = wizard.get_cleaned_data_for_step('basic') or {}
    return data.get("association") != "mentor"

def show_reg_guardian2_form_condition(wizard):
    data = wizard.get_cleaned_data_for_step('guardian2') or {}
    return data.get("guardian") is not None

def show_reg_emergency_form_condition(wizard):
    data = wizard.get_cleaned_data_for_step('basic') or {}
    return data.get("association") == "mentor"

def show_reg_team_form_condition(wizard):
    data = wizard.get_cleaned_data_for_step('basic') or {}
    return data.get("association") == "mentor"

REG_COND = {
        "guardian1": show_reg_guardian_form_condition,
        "guardian1address": show_reg_guardian_form_condition,
        "guardian1phone": show_reg_guardian_form_condition,
        "guardian2": show_reg_guardian_form_condition,
        "guardian2address": show_reg_guardian2_form_condition,
        "guardian2phone": show_reg_guardian2_form_condition,
        "emergency": show_reg_emergency_form_condition,
        "emergencyphone": show_reg_emergency_form_condition,
        "team": show_reg_team_form_condition,
        }

REG_DESCS = {
        "initial": "Get Started",
        "basic": "Member's Basic Information",
        "guardian1": "Legal Guardian #1",
        "guardian2": "Legal Guardian #2",
        "email": "E-mail Addresses",
        "emergency": "Emergency Contact",
        "team": "Team Membership",
        }

class RegistrationWizard(SessionWizardView):
    def get_template_names(self):
        if self.steps.current in REG_TEMPLATES:
            return [REG_TEMPLATES[self.steps.current]]
        else:
            return ["roster/reg/base.html"]

    def get_person(self):
        return self.storage.extra_data.get("person")

    def get_form_initial(self, step):
        newdata = super(RegistrationWizard, self).get_form_initial(step)
        person = None
        if step != 'initial':
            person = self.get_person()
            if person is None:
                person = Person()
        newdata["person"] = person
        if step == 'basic':
            newdata["firstname"] = person.firstname
            newdata["lastname"] = person.lastname
            newdata["suffix"] = person.suffix
            newdata["nickname"] = person.nickname
            newdata["gender"] = person.gender
            newdata["birth_month"] = person.birth_month
            newdata["birth_day"] = person.birth_day
            newdata["birth_year"] = person.birth_year
            newdata["company"] = person.company
            newdata["school"] = person.school
            newdata["grad_year"] = person.grad_year
            newdata["shirt_size"] = person.shirt_size
            newdata["medical"] = person.medical
            newdata["medications"] = person.medications
            if person.company:
                newdata["association"] = "mentor"
            elif person.school:
                newdata["association"] = "student"
        elif step == 'phone':
            newdata["primary"] = "Mobile"
            for pp in PersonPhone.objects.filter(person=person):
                location = pp.phone.location.lower()
                newdata[location+"_phone"] = pp.phone.phone
                newdata[location+"_ext"] = pp.phone.ext
                if pp.primary:
                    newdata["primary"] = pp.phone.location
        elif step == 'guardian1' or step == 'guardian2':
            guardians = Relationship.objects.filter(person_from=person, legal_guardian=True).order_by('id')
            n = int(step[-1:]) - 1
            newdata["guardian"] = Person()
            if len(guardians) > n:
                newdata["relationship"] = guardians[n].relationship
                guardian = guardians[n].person_to
                newdata["guardian"] = guardian
                newdata["firstname"] = guardian.firstname
                newdata["lastname"] = guardian.lastname
                newdata["suffix"] = guardian.suffix
                newdata["nickname"] = guardian.nickname
                newdata["gender"] = guardian.gender
                newdata["company"] = guardian.company
            elif person.id and step == 'guardian2':
                newdata["only_one_guardian"] = True
        elif step == 'emergency':
            guardians = Relationship.objects.filter(person_from=person, emergency_contact=True).order_by('id')
            newdata["guardian"] = Person()
            if len(guardians) > 0:
                newdata["relationship"] = guardians[0].relationship
                guardian = guardians[0].person_to
                newdata["guardian"] = guardian
                newdata["firstname"] = guardian.firstname
                newdata["lastname"] = guardian.lastname
                newdata["suffix"] = guardian.suffix
                newdata["nickname"] = guardian.nickname
                newdata["gender"] = guardian.gender
                newdata["company"] = guardian.company
        elif step == 'guardian1address' or step == "guardian2address":
            newdata["student"] = self.storage.extra_data.get("address")
            newdata["guardian1"] = None
            if step == "guardian2address":
                guardian1data = self.get_cleaned_data_for_step("guardian1address") or {}
                newdata["guardian1"] = guardian1data.get("address")
            guardiandata = self.get_cleaned_data_for_step(step[:-7]) or {}
            guardian = guardiandata.get("guardian")
            if guardian and guardian.id and guardian.addresses.all():
                address = guardian.addresses.all()[0]
                if address == newdata["student"]:
                    newdata["address_type"] = "same"
                elif address == newdata["guardian1"]:
                    newdata["address_type"] = "same1"
                else:
                    newdata["address_type"] = "new"
                    newdata["address"] = address
                    newdata["line1"] = address.line1
                    newdata["line2"] = address.line2
                    newdata["city"] = address.city
                    newdata["state"] = address.state
                    newdata["zipcode"] = address.zipcode
        elif step == 'guardian1phone' or step == 'guardian2phone' or step == 'emergencyphone':
            guardiandata = self.get_cleaned_data_for_step(step[:-5]) or {}
            guardian = guardiandata.get("guardian")
            newdata["primary"] = "Mobile"
            for pp in PersonPhone.objects.filter(person=guardian):
                location = pp.phone.location.lower()
                newdata[location+"_phone"] = pp.phone.phone
                newdata[location+"_ext"] = pp.phone.ext
                if pp.primary:
                    newdata["primary"] = pp.phone.location
        elif step == "email":
            # person email
            emails = PersonEmail.objects.filter(person=person, primary=True)
            if emails:
                newdata["email"] = emails[0].email
            # guardian emails
            guardians = Relationship.objects.filter(person_from=person, legal_guardian=True).order_by('id')
            for n in range(1, 3):
                guardiandata = self.get_cleaned_data_for_step("guardian%d" % n) or {}
                guardian = guardiandata.get("guardian")
                newdata["guardian%d" % n] = guardian
                if guardian:
                    emails = PersonEmail.objects.filter(person=guardian, primary=True)
                    if emails:
                        newdata["guardian%d_email" % n] = emails[0].email
                if len(guardians) > n:
                    newdata["guardian%d_cc" % n] = guardians[n-1].cc_on_email
        elif step == "team":
            teams = PersonTeam.objects.filter(person=person, team__reg_show=True).order_by("status")
            if teams:
                newdata["team"] = teams[0].team
        return newdata

    def get_form_kwargs(self, step):
        if step == 'basic':
            # make sure current grad_year is populated
            person = self.get_person()
            if person:
                kwargs = {}
                kwargs["force_grad_year"] = person.grad_year
                return kwargs
        return super(RegistrationWizard, self).get_form_kwargs(step)

    def get_form_instance(self, step):
        if step == 'address':
            person = self.get_person()
            if person.id:
                addresses = person.addresses.all() or [None]
                return addresses[0]
        return super(RegistrationWizard, self).get_form_instance(step)

    def save_address(self, person, address):
        existing_addresses = Address.objects.filter(
                line1=address.line1,
                line2=address.line2,
                city=address.city,
                state=address.state,
                zipcode=address.zipcode)
        if existing_addresses:
            address = existing_addresses[0]
        else:
            address.save()
        person.addresses.clear()
        person.addresses.add(address)

    def save_email(self, person, address):
        existing_emails = Email.objects.filter(email=address)
        if existing_emails:
            email = existing_emails[0]
        else:
            email = Email(email=address, location="Other")
            email.save()
        person.emails.clear()
        pe = PersonEmail(person=person, email=email)
        pe.save()

    def save_phones(self, person, phonestep):
        formdata = self.get_cleaned_data_for_step(phonestep) or {}
        primary = formdata.get("primary")
        person.phones.clear()
        for loc, alias in Phone.LOCATION_CHOICES:
            number = formdata.get("%s_phone" % loc.lower(), "")
            ext = formdata.get("%s_ext" % loc.lower(), "")
            if not number:
                continue
            phones = Phone.objects.filter(phone=number, ext=ext)
            if phones:
                phone = phones[0]
                phone.location = loc
            else:
                phone = Phone(phone=number, ext=ext, location=loc)
            phone.save()
            pp = PersonPhone(person=person, phone=phone,
                    primary=(loc==primary))
            pp.save()

    @transaction.commit_on_success
    def done(self, form_list, **kwargs):
        person = self.get_person()

        # Save person
        formdata = self.get_cleaned_data_for_step("basic") or {}
        association = formdata.get("association")
        company = formdata.get("company")
        if company is not None:
            company.save()
            person.company = company
        person.save()

        # person address
        address = self.storage.extra_data.get("address")
        self.save_address(person, address)

        # person phones
        self.save_phones(person, "phone")

        # emails
        formdata = self.get_cleaned_data_for_step("email") or {}
        person_email = formdata.get("email")
        guardian_email = [(formdata.get("guardian%d_email" % n),
                           formdata.get("guardian%d_cc" % n))
                          for n in range(1, 3)]
        self.save_email(person, person_email)

        # guardians/emergency contact
        Relationship.objects.filter(person_from=person).delete()
        if association == "mentor":
            # emergency contact person
            formdata = self.get_cleaned_data_for_step("emergency") or {}
            contact = formdata.get("guardian")
            relationship = formdata.get("relationship")
            contact.save()

            # emergency contact phones
            self.save_phones(contact, "emergencyphone")

            # save relationship
            rel = Relationship(person_from=person, person_to=contact,
                    relationship=relationship, emergency_contact=True)
            rel.save()
            # save inverse relationship
            if relationship.inverse:
                Relationship.objects.filter(person_from=contact,
                        person_to=person).delete()
                rel = Relationship(person_from=contact, person_to=person,
                        relationship=relationship.inverse)
                rel.save()
        else:
            for n in range(1, 3):
                # guardian person
                formdata = self.get_cleaned_data_for_step("guardian%d" % n) or {}
                guardian = formdata.get("guardian")
                if guardian is None:
                    continue
                relationship = formdata.get("relationship")
                company = formdata.get("company")
                if company is not None:
                    company.save()
                    guardian.company = company
                guardian.save()

                # guardian address
                formdata = self.get_cleaned_data_for_step("guardian%daddress" % n) or {}
                address = formdata.get("address")
                self.save_address(guardian, address)

                # guardian phones
                self.save_phones(guardian, "guardian%dphone" % n)

                # guardian email
                cc_on_email = False
                if guardian_email[n-1][0]:
                    self.save_email(guardian, guardian_email[n-1][0])
                    cc_on_email = bool(guardian_email[n-1][1])

                # save relationship
                rel = Relationship(person_from=person, person_to=guardian,
                        relationship=relationship, legal_guardian=True,
                        emergency_contact=True, cc_on_email=cc_on_email)
                rel.save()
                # save inverse relationship
                if relationship.inverse:
                    Relationship.objects.filter(person_from=guardian,
                            person_to=person).delete()
                    rel = Relationship(person_from=guardian, person_to=person,
                            relationship=relationship.inverse)
                    rel.save()

        # update team relationship
        if association == "mentor":
            formdata = self.get_cleaned_data_for_step("team") or {}
            team = formdata.get("team")
            role = "Mentor"
        else:
            team = None
            role = "Student"
            # determine team from grade
            import datetime
            now = datetime.datetime.now()
            year = now.year
            if now.month > 6:
                year += 1
            year2grade = dict((year-x+12, x) for x in range(12,3,-1))
            grade = year2grade.get(person.grad_year)
            if grade:
                teams = Team.objects.filter(reg_default=True,
                        program__grade_start__lte=grade,
                        program__grade_end__gte=grade)
                if teams:
                    team = teams[0]

        if team:
            try:
                pt = PersonTeam.objects.get(person=person, team=team)
            except PersonTeam.DoesNotExist:
                from datetime import date
                pt = PersonTeam(person=person, team=team,
                        joined=date.today())
            pt.role = role
            pt.status = "Active"
            pt.save()

        response = HttpResponse(mimetype='application/pdf')
        response['Content-Disposition'] = \
                'attachment; filename=RegVerify%d.pdf' % person.id
        make_reg_verify_pdf(response, [person])
        return response

    def process_step(self, form):
        extra_data = self.storage.extra_data
        if self.steps.current == "initial":
            person = form.cleaned_data.get("person")
            extra_data["person"] = person
        elif self.steps.current == "address":
            extra_data["address"] = form.save(commit=False)
        self.storage.extra_data = extra_data
        return self.get_form_step_data(form)

    def get_context_data(self, form, **kwargs):
        context = super(RegistrationWizard, self).get_context_data(form=form, **kwargs)
        desc = "?"
        if self.steps.current in REG_DESCS:
            desc = REG_DESCS[self.steps.current]
        elif self.steps.current == "phone":
            desc = "%s's Phone Numbers" % self.get_person()
        elif self.steps.current == "address":
            desc = "%s's Address" % self.get_person()
        elif self.steps.current == "guardian1phone" or self.steps.current == "guardian2phone" or self.steps.current == "emergencyphone":
            guardiandata = self.get_cleaned_data_for_step(self.steps.current[:-5]) or {}
            desc = "%s's Phone Numbers" % guardiandata.get("guardian")
        elif self.steps.current == "guardian1address" or self.steps.current == "guardian2address":
            guardiandata = self.get_cleaned_data_for_step(self.steps.current[:-7]) or {}
            desc = "%s's Address" % guardiandata.get("guardian")

        context.update({'description': desc})
        return context

registration = RegistrationWizard.as_view(REG_FORMS, condition_dict=REG_COND)
registration = login_required(registration, login_url='/roster/login/')

