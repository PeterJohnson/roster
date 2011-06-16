from django.db import models

# Base models
class Organization(models.Model):
    name = models.CharField("Name", max_length=30, unique=True)

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ['name']

class Program(models.Model):
    name = models.CharField("Name", max_length=20, unique=True)
    longname = models.CharField("Long name", max_length=50)
    org = models.ForeignKey(Organization)

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ['name']

class Team(models.Model):
    name = models.CharField("Name", max_length=20, unique=True)
    startdate = models.DateField("Start date")
    program = models.ForeignKey(Program)

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ['name']

class Position(models.Model):
    title = models.CharField(max_length=50, unique=True)
    steering = models.BooleanField(default=False)

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

    class Meta:
        ordering = ['type', 'longname']

class Company(models.Model):
    name = models.CharField("Name", max_length=20, unique=True)
    longname = models.CharField("Long name", max_length=50)

    def __unicode__(self):
        return self.name

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

    class Meta:
        ordering = ['email']

class Address(models.Model):
    line1 = models.CharField("Line 1", max_length=50)
    line2 = models.CharField("Line 2", max_length=50, blank=True)
    city = models.CharField("City", max_length=50)
    state = models.CharField("State", max_length=2)
    zipcode = models.CharField("Zip Code", max_length=10, blank=True)

    def __unicode__(self):
        return "%s, %s, %s" % (self.line1, self.city, self.state)

    class Meta:
        verbose_name_plural = "Addresses"
        ordering = ['state', 'city', 'line1']

class Phone(models.Model):
    phone = models.CharField("Phone Number", max_length=30, unique=True)
    location = models.CharField("Location", max_length=10, choices=(
        ('Home', "Home"),
        ('Mobile', "Mobile"),
        ('Work', "Work"),
        ('Other', "Other"),
    ))

    def __unicode__(self):
        return "%s (%s)" % (self.phone, self.get_location_display())

    class Meta:
        ordering = ['phone']

class RelationshipType(models.Model):
    type = models.CharField(max_length=30, unique=True)

    def __unicode__(self):
        return self.type

class Person(models.Model):
    badge = models.IntegerField("Badge Number", unique=True, null=True,
                                blank=True)

    firstname = models.CharField("First Name", max_length=100)
    lastname = models.CharField("Last Name", max_length=100)
    suffix = models.CharField("Suffix", max_length=10, blank=True)

    gender = models.CharField("Gender", max_length=2, choices=(
        ('M', "Male"),
        ('F', "Female"),
    ))

    status = models.CharField("Status", max_length=20, choices=(
        ('Too Young', "Too Young"),
        ('Prospective', "Prospective"),
        ('Active', "Active"),
        ('Alumnus', "Alumnus"),
        ('Disinterested', "Disinterested"),
        ('Contact', "Contact Only"),
    ))

    teams = models.ManyToManyField(Team, blank=True)

    shirt_size = models.CharField("Shirt Size", max_length=3, blank=True,
                                  choices=(
        ('S', "Small"),
        ('M', "Medium"),
        ('L', "Large"),
        ('XL', "XL"),
        ('XXL', "XXL"),
    ))
    medical = models.TextField("Medical Concerns", blank=True)
    medications = models.TextField("Medications", blank=True)

    joined = models.DateField("Joined team", null=True, blank=True)
    left = models.DateField("Left team", null=True, blank=True)
    birthdate = models.DateField("Birthdate", null=True, blank=True)

    emergency_contact = models.ForeignKey('Adult', null=True, blank=True)
    emergency_contact_relation = models.ForeignKey('RelationshipType',
                                                   null=True, blank=True)

    prospective_source = models.CharField("Prospective Source",
                                          max_length=255, blank=True)

    comments = models.TextField("Comments", blank=True)

    receive_email = models.BooleanField("Receive Email", default=True)
    contact_public = models.BooleanField("Release Contact Info")

    position = models.ForeignKey(Position, null=True, blank=True)

    emails = models.ManyToManyField(Email, through='PersonEmail', blank=True)
    addresses = models.ManyToManyField(Address, blank=True)
    phones = models.ManyToManyField(Phone, through='PersonPhone', blank=True)

    def __unicode__(self):
        return "%s, %s" % (self.lastname, self.firstname)

    class Meta:
        verbose_name_plural = "People"
        ordering = ['lastname', 'firstname']

class PersonEmail(models.Model):
    person = models.ForeignKey(Person)
    email = models.ForeignKey(Email)
    primary = models.BooleanField("Primary")

class PersonPhone(models.Model):
    person = models.ForeignKey(Person)
    phone = models.ForeignKey(Phone)
    primary = models.BooleanField("Primary")

class Waiver(models.Model):
    person = models.ForeignKey(Person)
    org = models.ForeignKey(Organization)
    year = models.IntegerField("Year")

class Adult(Person):
    role = models.CharField("Role", max_length=10, choices=(
        ('Contact', "Contact"),
        ('Parent', "Parent"),
        ('Volunteer', "Volunteer"),
    ))
    company = models.ForeignKey(Company, null=True, blank=True)
    mentor = models.BooleanField(default=False)

class Student(Person):
    school = models.ForeignKey(School, null=True)
    grad_year = models.IntegerField("Graduation year", null=True)
    relationships = models.ManyToManyField(Adult, through='Relationship')

class Relationship(models.Model):
    student = models.ForeignKey(Student)
    adult = models.ForeignKey(Adult)
    relationship = models.ForeignKey(RelationshipType)
    cc_on_email = models.BooleanField("CC on Emails", default=False)

class FeePaid(models.Model):
    student = models.ForeignKey(Student)
    year = models.IntegerField()
    amount = models.DecimalField(decimal_places=2, max_digits=5, null=True,
                                 blank=True)

    class Meta:
        verbose_name_plural = "Fees paid"

class Event(models.Model):
    name = models.CharField(max_length=50, unique=True)
    location = models.CharField(max_length=50, unique=True)
    date = models.DateField()
    time = models.TimeField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    people = models.ManyToManyField(Person, through='EventPerson',
                                    blank=True)

class EventPerson(models.Model):
    event = models.ForeignKey(Event)
    person = models.ForeignKey(Person)

class TimeRecord(models.Model):
    person = models.ForeignKey(Person)
    event = models.ForeignKey(Event, null=True, blank=True)
    clock_in = models.DateTimeField("Clocked in")
    clock_out = models.DateTimeField("Clocked out", null=True, blank=True)
    hours = models.FloatField("Hours")
    recorded = models.DateField("Recorded")

class WaitlistEntry(models.Model):
    student = models.ForeignKey(Student)
    program = models.ForeignKey(Program)
    team = models.ForeignKey(Team, null=True, blank=True)
    date = models.DateField("Wait list date", null=True, blank=True)

    class Meta:
        verbose_name_plural = "Waitlist entries"

