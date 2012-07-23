# Roster views
from django.http import HttpResponse
from django.utils.html import escape, linebreaks
from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.db.models import Q, Count
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction

from settings import MEDIA_ROOT

from PIL import Image

from roster.models import *
from roster.forms import *

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
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
    def __init__(self, firstname, lastname, suffix, adult):
        ActionFlowable.__init__(self, ('startPerson', firstname, lastname,
                                       suffix, adult))

class RegVerifyDocTemplate(BaseDocTemplate):
    _invalidInitArgs = ('pageTemplates')

    def afterInit(self):
        self.name = None
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
                [(0, 0, 0.75, 0.5, "Info Logged:", None),
                 (1, 0, 0.75, 0.5, "Printed On:",
                  self.today.strftime("%b %-d, %Y")),
                 (0, 1, 0.75, 0.5, "Cash/Check #", None),
                 (1, 1, 0.75, 0.5, "Amount:", None),
                 (0, 2, 0.75, 0.5, "Program:", None),
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

    def handle_startPerson(self, firstname, lastname, suffix, adult):
        #self.pageTemplate = self.pageTemplates[0]
        self.name = "%s, %s %s" % (lastname, firstname, suffix)
        self.adult = adult

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
        if isinstance(parent, Relationship):
            data.append(("Emergency Contact", "",
                parent.emergency_contact and "Yes" or "No"))
        elif parent:
            data.append(("Emergency Contact", "", "Yes / No"))

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
    wanted_phone_locations = set([u'Cell', u'Home'])
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
        highlight(style, data)
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
            if not person.medical:
                highlight(style, data)
            data.append(("Medical", "Conditions/Allergies", person.medical))
            if not person.medications:
                highlight(style, data)
            data.append(("", "Medications", person.medications))

    elements.append(Table(data, colWidths=(0.75*inch, 1.25*inch, 5*inch),
                    style=style))

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

    from datetime import date
    today = date.today()

    # configure PDF output
    response = HttpResponse(mimetype='application/pdf')
    response['Content-Disposition'] = 'attachment; filename=TeamRegVerify.pdf'
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

    people = PersonTeam.objects.filter(
            role__in=form.data.getlist('who'),
            status='Active',
            team__in=form.data.getlist('team')).values('person')

    people = Person.objects.filter(id__in=people)

    for person in people:
        adult = (person.birth_year and person.birth_year > 100 and
                 (today.year - person.birth_year) > 20)
        elements.append(StartPerson(person.firstname, person.lastname,
                                    person.suffix, adult))
        person_to_pdf(elements, person,
                "%s Information" % (adult and "Mentor" or "Student"),
                adult=adult)
        elements.append(Paragraph("", normal_para_style))

        parents = []
        if not adult:
            # Parents
            parents = Relationship.objects.filter(
                    person_from=person,
                    relationship__in=parent_relationships) \
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
    writer.writerow(['id', 'name', 'student', 'photo', 'photo size'])
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
        writer.writerow([person.id, name, student, photourl, photosize])

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

def roundRectPath(path, x, y, width, height, radius):
    """Draws a rectangle with rounded corners. The corners are
    approximately quadrants of a circle, with the given radius."""
    #use a precomputed set of factors for the bezier approximation
    #to a circle. There are six relevant points on the x axis and y axis.
    #sketch them and it should all make sense!
    t = 0.4472 * radius

    x0 = x
    x1 = x0 + t
    x2 = x0 + radius
    x3 = x0 + width - radius
    x4 = x0 + width - t
    x5 = x0 + width

    y0 = y
    y1 = y0 + t
    y2 = y0 + radius
    y3 = y0 + height - radius
    y4 = y0 + height - t
    y5 = y0 + height

    path.moveTo(x2, y0)
    path.lineTo(x3, y0) # bottom row
    path.curveTo(x4, y0, x5, y1, x5, y2) # bottom right

    path.lineTo(x5, y3) # right edge
    path.curveTo(x5, y4, x4, y5, x3, y5) # top right

    path.lineTo(x2, y5) # top row
    path.curveTo(x1, y5, x0, y4, x0, y3) # top left

    path.lineTo(x0, y2) # left edge
    path.curveTo(x0, y1, x1, y0, x2, y0) # bottom left

    path.close() #close off, although it should be where it started anyway

class Badge(Flowable):
    """A badge flowable."""
    # badge dimensions
    width = 3.5*inch
    height = 2.25*inch

    # border thickness
    border_size = 0.125*inch

    # logo location and size
    logo = 1
    logo_width = 0.5*inch
    logo_height = 0.75*inch
    logo_x = width - logo_width - 0.25*inch
    logo_y = height - logo_height - 0.125*inch

    # photo location and size
    photo_width = 1.0*inch
    photo_height = 1.25*inch
    photo_x = 0.25*inch
    photo_y = height - photo_height - 0.25*inch
    photo_corner = 0.125*inch  # rounded corner radius

    # name location and size
    name_font = 'Calibri-Bold'
    name_fontsize = 20
    name_x = 0.25*inch
    name_y = 0.5*inch

    # position location and size
    position_font = 'Calibri'
    position_fontsize = 14
    position_x = 0.25*inch
    position_y = 0.25*inch

    # barcode location and size
    barcode_x = 1.75*inch
    barcode_y = 1*inch

    def __init__(self, person, parent_relationships=None):
        self.person = person
        if parent_relationships is None:
            parent_relationships = RelationshipType.objects.filter(parent=True).values_list('id', flat=True)
        self.student = self.person.is_student(parent_relationships)

    def wrap(self, *args):
        return (0, self.height)

    def draw(self):
        canvas = self.canv
        canvas.saveState()
        canvas.setLineWidth(1)
        canvas.setStrokeColor(colors.black)
        canvas.setFillColor(colors.black)

        # Badge outline / border
        canvas.saveState()
        canvas.setFillColor(self.student and team_color1 or team_color2)
        canvas.rect(0, 0, self.width, self.height, fill=1)
        canvas.setFillColor(colors.white)
        canvas.rect(self.border_size, self.border_size,
                self.width-self.border_size*2, self.height-self.border_size*2,
                stroke=0, fill=1)
        canvas.restoreState()

        # Team logo
        if self.logo:
            canvas.drawImage(os.path.join(MEDIA_ROOT, "logo.jpeg"),
                    self.logo_x, self.logo_y, self.logo_width, self.logo_height,
                    preserveAspectRatio=True)

        # Photo
        if self.person.photo:
            # load image
            photopath = os.path.join(MEDIA_ROOT, self.person.photo.name)
            img = Image.open(photopath)

            # crop image to aspect ratio
            imgw, imgh = img.size
            newimgw, newimgh = imgw, imgh
            rw = int(imgh * self.photo_width / self.photo_height)
            if rw <= imgw:
                newimgw = rw
            else:
                newimgh = int(imgw * self.photo_height / self.photo_width)
            left = (imgw-newimgw)/2
            top = (imgh-newimgh)/2
            finalimg = img.crop((left, top, left+newimgw, top+newimgh))
            finalimg.load()

            # round corners by using a clip path
            canvas.saveState()
            p = canvas.beginPath()
            roundRectPath(p, self.photo_x, self.photo_y, self.photo_width,
                    self.photo_height, self.photo_corner)
            canvas.clipPath(p, stroke=0)
            # draw image
            canvas.drawImage(ImageReader(finalimg), self.photo_x, self.photo_y,
                    self.photo_width, self.photo_height,
                    preserveAspectRatio=True)
            canvas.restoreState()
        else:
            canvas.roundRect(self.photo_x, self.photo_y, self.photo_width,
                    self.photo_height, self.photo_corner, stroke=1)

        # Name
        canvas.saveState()
        canvas.setFont(self.name_font, self.name_fontsize)
        canvas.drawString(self.name_x, self.name_y, self.person.render_normal())
        canvas.restoreState()

        # Position
        position = str(self.person.position)
        if not position:
            if self.student:
                position = "Student"
            else:
                position = "Mentor"
        canvas.saveState()
        canvas.setFont(self.position_font, self.position_fontsize)
        canvas.drawString(self.position_x, self.position_y, position)
        canvas.restoreState()

        # Barcode (ID)
        idstr = "%05d" % self.person.id
        canvas.saveState()
        barcode = code39.Standard39(idstr, humanReadable=1, checksum=0)
        canvas.setFillColor(colors.white)
        # increase bounding box a bit to ensure we include the human readable
        # part as well
        canvas.rect(self.barcode_x, self.barcode_y-0.1875*inch, barcode.width,
                barcode.height+0.25*inch, stroke=1, fill=1)
        canvas.setFillColor(colors.black)
        barcode.drawOn(canvas, self.barcode_x, self.barcode_y)
        canvas.restoreState()

        canvas.restoreState()

class BadgesDocTemplate(BaseDocTemplate):
    _invalidInitArgs = ('pageTemplates')

    def afterInit(self):
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id='normal')
        self.addPageTemplates([PageTemplate(id='Page',frames=frame,pagesize=self.pagesize)])

@login_required(login_url='/roster/login/')
def badges(request):
    """Badge generation."""
    if request.method != 'GET' or not request.GET:
        form = BadgesForm()
        return render_to_response("roster/badges.html", locals(),
                                  context_instance=RequestContext(request))

    form = BadgesForm(request.GET)
    if not form.is_valid():
        return render_to_response("roster/badges.html", locals(),
                                  context_instance=RequestContext(request))

    # configure PDF output
    response = HttpResponse(mimetype='application/pdf')
    response['Content-Disposition'] = 'attachment; filename=Badges.pdf'
    doc = BadgesDocTemplate(response,
            pagesize=letter,
            allowSplitting=0,
            leftMargin=0.5*inch,
            rightMargin=0.5*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch,
            title="Badges",
            author="Beach Cities Robotics")

    # container for the 'Flowable' objects
    elements = []

    styles = getSampleStyleSheet()
    normal_para_style = styles['Normal']

    parent_relationships = RelationshipType.objects.filter(parent=True).values_list('id', flat=True)

    people = PersonTeam.objects.filter(
            role__in=form.data.getlist('who'),
            status='Active',
            team__in=form.data.getlist('team')).values('person')

    people = Person.objects.filter(id__in=people)

    for person in people:
        elements.append(Badge(person, parent_relationships))
        elements.append(Paragraph("", normal_para_style))

    # Generate the document
    doc.build(elements)
    return response

