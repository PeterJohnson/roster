from django.db import models, IntegrityError
from django.contrib.localflavor.us.models import *
from batch_select.models import BatchManager

# Base models
class Organization(models.Model):
    name = models.CharField("Name", max_length=30, unique=True)

    def __unicode__(self):
        return self.name

    def clean(self):
        for field in self._meta.fields:
            if isinstance(field, (models.CharField, models.TextField)):
                setattr(self, field.name, getattr(self, field.name).strip())

    class Meta:
        ordering = ['name']

class Program(models.Model):
    name = models.CharField("Name", max_length=20, unique=True)
    longname = models.CharField("Long name", max_length=50)
    org = models.ForeignKey(Organization)

    def __unicode__(self):
        return self.name

    def clean(self):
        for field in self._meta.fields:
            if isinstance(field, (models.CharField, models.TextField)):
                setattr(self, field.name, getattr(self, field.name).strip())

    class Meta:
        ordering = ['name']

class Team(models.Model):
    name = models.CharField("Name", max_length=20, unique=True)
    startdate = models.DateField("Start date")
    program = models.ForeignKey(Program)

    def __unicode__(self):
        return self.name

    def clean(self):
        for field in self._meta.fields:
            if isinstance(field, (models.CharField, models.TextField)):
                setattr(self, field.name, getattr(self, field.name).strip())

    class Meta:
        ordering = ['name']

class Position(models.Model):
    title = models.CharField(max_length=50, unique=True)
    steering = models.BooleanField(default=False)

    def clean(self):
        for field in self._meta.fields:
            if isinstance(field, (models.CharField, models.TextField)):
                setattr(self, field.name, getattr(self, field.name).strip())

    class Meta:
        ordering = ['title']

class School(models.Model):
    name = models.CharField("Name", max_length=20, unique=True)
    longname = models.CharField("Long name", max_length=50)
    type = models.IntegerField("Type", choices=(
        (0, "Elementary School"),
        (1, "Middle School"),
        (2, "High School"),
        (3, "Homeschool"),
    ))

    def __unicode__(self):
        return "%s" % self.longname

    def clean(self):
        for field in self._meta.fields:
            if isinstance(field, (models.CharField, models.TextField)):
                setattr(self, field.name, getattr(self, field.name).strip())

    class Meta:
        ordering = ['longname']

class Company(models.Model):
    name = models.CharField("Name", max_length=50, unique=True)

    def __unicode__(self):
        return self.name

    def clean(self):
        for field in self._meta.fields:
            if isinstance(field, (models.CharField, models.TextField)):
                setattr(self, field.name, getattr(self, field.name).strip())

    class Meta:
        verbose_name_plural = "Companies"
        ordering = ['name']

class Email(models.Model):
    email = models.EmailField("Email", max_length=255, unique=True)
    location = models.CharField("Location", max_length=10, choices=(
        ('Home', "Home"),
        ('Work', "Work"),
        ('Other', "Other"),
    ))

    def __unicode__(self):
        return self.email

    def clean(self):
        for field in self._meta.fields:
            if isinstance(field, (models.CharField, models.TextField)):
                setattr(self, field.name, getattr(self, field.name).strip())

    class Meta:
        ordering = ['email']

class Address(models.Model):
    line1 = models.CharField("Line 1", max_length=50)
    line2 = models.CharField("Line 2", max_length=50, blank=True)
    city = models.CharField("City", max_length=50)
    state = USStateField("State")
    zipcode = models.CharField("Zip Code", max_length=10, blank=True)

    def __unicode__(self):
        return "%s, %s, %s" % (self.line1, self.city, self.state)

    def clean(self):
        for field in self._meta.fields:
            if isinstance(field, (models.CharField, models.TextField)):
                setattr(self, field.name, getattr(self, field.name).strip())

    class Meta:
        verbose_name_plural = "Addresses"
        ordering = ['line1']

class Phone(models.Model):
    phone = PhoneNumberField("Phone Number")
    ext = models.CharField("Extension", max_length=5, blank=True)
    location = models.CharField("Type", max_length=10, choices=(
        ('Home', "Home"),
        ('Mobile', "Cell"),
        ('Work', "Work"),
        ('Other', "Other"),
    ))

    def __unicode__(self):
        if self.ext:
            return "%s x%s (%s)" % (self.phone, self.ext,
                                    self.get_location_display())
        else:
            return "%s (%s)" % (self.phone, self.get_location_display())

    def render_normal(self):
        if self.ext:
            return "%s x%s" % (self.phone, self.ext)
        else:
            return self.phone

    def clean(self):
        for field in self._meta.fields:
            if isinstance(field, (models.CharField, models.TextField)):
                setattr(self, field.name, getattr(self, field.name).strip())

    class Meta:
        ordering = ['phone']
        unique_together = ['phone', 'ext']

class RelationshipType(models.Model):
    type = models.CharField(max_length=30, unique=True)
    parent = models.BooleanField("Parent", default=False)
    sort_order = models.IntegerField("Sort order")

    def __unicode__(self):
        return self.type

    def clean(self):
        for field in self._meta.fields:
            if isinstance(field, (models.CharField, models.TextField)):
                setattr(self, field.name, getattr(self, field.name).strip())

    class Meta:
        ordering = ['sort_order']

class Person(models.Model):
    firstname = models.CharField("First Name", max_length=100)
    lastname = models.CharField("Last Name", max_length=100)
    suffix = models.CharField("Suffix", max_length=10, blank=True)
    nickname = models.CharField("Nickname", max_length=50, blank=True)

    GENDER_CHOICES=(
        ('M', "Male"),
        ('F', "Female"),
    )
    gender = models.CharField("Gender", max_length=1, choices=GENDER_CHOICES)

    company = models.ForeignKey(Company, null=True, blank=True)
    school = models.ForeignKey(School, null=True, blank=True)
    grad_year = models.IntegerField("Graduation year", null=True, blank=True)

    badge = models.IntegerField("Badge Number", unique=True, null=True,
                                blank=True)

    teams = models.ManyToManyField(Team, through='PersonTeam', blank=True)

    shirt_size = models.CharField("Shirt Size", max_length=3, blank=True,
                                  choices=(
        ('YS', "Youth Small"),
        ('YM', "Youth Medium"),
        ('YL', "Youth Large"),
        ('S', "Small"),
        ('M', "Medium"),
        ('L', "Large"),
        ('XL', "XL"),
        ('XXL', "XXL"),
    ))
    medical = models.TextField("Medical Concerns", blank=True)
    medications = models.TextField("Medications", blank=True)

    birth_year = models.IntegerField(null=True, blank=True)
    birth_month = models.IntegerField(null=True, blank=True)
    birth_day = models.IntegerField(null=True, blank=True)

    prospective_source = models.CharField("Prospective Source",
                                          max_length=255, blank=True)

    comments = models.TextField("Comments", blank=True)

    position = models.ForeignKey(Position, null=True, blank=True)

    emails = models.ManyToManyField(Email, through='PersonEmail', blank=True)
    addresses = models.ManyToManyField(Address, blank=True)
    phones = models.ManyToManyField(Phone, through='PersonPhone', blank=True)

    def __unicode__(self):
        if self.suffix:
            return "%s %s %s" % (self.get_firstname(), self.lastname,
                                 self.suffix)
        else:
            return "%s %s" % (self.get_firstname(), self.lastname)

    def render_normal(self):
        return self.__unicode__()

    def get_firstname(self):
        if self.nickname:
            return self.nickname
        else:
            return self.firstname
    get_firstname.short_description = 'First Name'

    def active_roles(self):
        results = PersonTeam.objects.filter(person=self,
                status__in=('Active', 'Prospective'))
        results = results.select_related('team.name')
        return ", ".join("%s (%s%s)" %
                (x.team.name,
                 x.status == 'Prospective' and "Prospective " or "",
                 x.role)
                for x in results)
    active_roles.short_description = 'Active Roles'

    objects = BatchManager()

    def clean(self):
        for field in self._meta.fields:
            if isinstance(field, (models.CharField, models.TextField)):
                setattr(self, field.name, getattr(self, field.name).strip())

    class Meta:
        verbose_name_plural = "People"
        ordering = ['lastname', 'firstname']
        unique_together = ['firstname', 'lastname', 'suffix']

class PersonTeam(models.Model):
    person = models.ForeignKey(Person)
    team = models.ForeignKey(Team)

    ROLE_CHOICES=(
        ('Mentor', "Mentor"),
        ('Student', "Student"),
        ('Fan', "Fan"),
    )
    role = models.CharField("Role", max_length=10, choices=ROLE_CHOICES)

    STATUS_CHOICES=(
        ('Prospective', "Prospective"),
        ('Active', "Active"),
        ('Alumnus', "Alumnus"),
        ('Disinterested', "Disinterested"),
    )
    status = models.CharField("Status", max_length=20, choices=STATUS_CHOICES)

    joined = models.DateField("Joined", null=True, blank=True)
    left = models.DateField("Left", null=True, blank=True)

    def __unicode__(self):
        return "%s %s, %s" % (self.status, self.role, self.team.name)

    class Meta:
        unique_together = ['team', 'person']

class PersonEmail(models.Model):
    person = models.ForeignKey(Person)
    email = models.ForeignKey(Email)
    primary = models.BooleanField("Primary", default=True)

    def __unicode__(self):
        return "%s (%s)" % (self.email, self.primary and "Primary" or "Alternate")

class PersonPhone(models.Model):
    person = models.ForeignKey(Person)
    phone = models.ForeignKey(Phone)
    primary = models.BooleanField("Primary", default=True)

    def __unicode__(self):
        return "%s (%s)" % (self.phone, self.primary and "Primary" or "Alternate")

class Waiver(models.Model):
    person = models.ForeignKey(Person)
    org = models.ForeignKey(Organization)
    year = models.IntegerField("Year")

    def __unicode__(self):
        return "%s (%s)" % (self.org, self.year)

class Relationship(models.Model):
    person_from = models.ForeignKey(Person,
                                    related_name="relationship_to_set")
    person_to = models.ForeignKey(Person,
                                  related_name="relationship_from_set")
    relationship = models.ForeignKey(RelationshipType)
    cc_on_email = models.BooleanField("CC on Emails", default=False)
    emergency_contact = models.BooleanField("Emergency Contact", default=False)

    def __unicode__(self):
        return "%s (%s)" % (self.person_to, self.relationship)

    class Meta:
        unique_together = ['person_from', 'person_to']

class Event(models.Model):
    name = models.CharField(max_length=50)
    location = models.CharField(max_length=50)
    date = models.DateField()
    time = models.TimeField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    calendar_post = models.BooleanField(default=True)
    fee = models.DecimalField(decimal_places=2, max_digits=5, default=0.0)
    people = models.ManyToManyField(Person, through='EventPerson',
                                    blank=True)

    def __unicode__(self):
        return "%s: %s" % (self.date.strftime('%a %b %d, %Y'), self.name)

    def clean(self):
        for field in self._meta.fields:
            if isinstance(field, (models.CharField, models.TextField)):
                setattr(self, field.name, getattr(self, field.name).strip())

    class Meta:
        ordering = ['date', 'time']

class EventPerson(models.Model):
    event = models.ForeignKey(Event)
    person = models.ForeignKey(Person)
    role = models.CharField("Role", max_length=20, choices=(
        ('Participant', "Participant"),
        ('Volunteer', "Volunteer"),
    ))
    fee_paid = models.DecimalField(decimal_places=2, max_digits=5,
                                   default=0.0)
    comments = models.TextField("Comments", blank=True)

    def __unicode__(self):
        return "%s (%s) - %s" % (self.person, self.role, self.fee_paid)

    class Meta:
        unique_together = ['event', 'person']

class TimeRecord(models.Model):
    person = models.ForeignKey(Person)
    event = models.ForeignKey(Event, null=True, blank=True)
    clock_in = models.DateTimeField("Clocked in")
    clock_out = models.DateTimeField("Clocked out", null=True, blank=True)
    hours = models.FloatField("Hours")
    recorded = models.DateField("Recorded")

