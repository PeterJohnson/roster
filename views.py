# Roster views
from django.http import HttpResponse
from django.utils.html import escape, linebreaks
from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.db.models import Q

from roster.models import *
from roster.forms import *

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, BaseDocTemplate, SimpleDocTemplate, Table, TableStyle, PageBreak, ActionFlowable, Frame, PageTemplate
from reportlab.platypus.flowables import Flowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
pdfmetrics.registerFont(TTFont('Calibri', 'calibri.ttf'))
pdfmetrics.registerFont(TTFont('Calibri-Bold', 'calibrib.ttf'))
pdfmetrics.registerFont(TTFont('Calibri-Italic', 'calibrii.ttf'))


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
