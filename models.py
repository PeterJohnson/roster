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

class School(models.Model):
    name = models.CharField("Name", max_length=20, unique=True)
    longname = models.CharField("Long name", max_length=50)
    type = models.CharField("Type", max_length=20, choices=(
        ('elementary', "Elementary School"),
        ('middle', "Middle School"),
        ('high', "High School"),
        ('home', "Homeschool"),
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
        ('home', "Home"),
        ('work', "Work"),
        ('other', "Other"),
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

    class Meta:
        verbose_name_plural = "Addresses"
        ordering = ['state', 'city', 'line1']

class Phone(models.Model):
    phone = models.CharField("Phone Number", max_length=30, unique=True)
    location = models.CharField("Location", max_length=10, choices=(
        ('home', "Home"),
        ('cell', "Cell"),
        ('work', "Work"),
        ('other', "Other"),
    ))

    def __unicode__(self):
        return self.phone

    class Meta:
        ordering = ['phone']

class Person(models.Model):
    badge = models.IntegerField("Badge Number", unique=True, null=True)

    firstname = models.CharField("First Name", max_length=100)
    lastname = models.CharField("Last Name", max_length=100)
    suffix = models.CharField("Suffix", max_length=10)

    gender = models.CharField("Gender", max_length=2, choices=(
        ('M', "Male"),
        ('F', "Female"),
    ))

    status = models.CharField("Status", max_length=20, choices=(
        ('tooyoung', "Too Young"),
        ('prospective', "Prospective"),
        ('active', "Active"),
        ('alumnus', "Alumnus"),
        ('disinterested', "Disinterested"),
        ('contact', "Contact Only"),
    ))

    programs = models.ManyToManyField(Program)

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

    joined = models.DateField("Joined team", null=True)
    left = models.DateField("Left team", null=True)
    birthdate = models.DateField("Birthdate", null=True)

    emergency_contact = models.ForeignKey('self', null=True)
    emergency_contact_relation = \
            models.CharField("Emergency Contact Relation", max_length=30,
                             blank=True)

    prospective_source = models.CharField("Prospective Source",
                                          max_length=255, blank=True)

    comments = models.TextField("Comments", blank=True)

    receive_email = models.BooleanField("Receive Email")
    contact_public = models.BooleanField("Public Contact Info")

    lead = models.BooleanField("Lead", default=False)
    position = models.CharField("Position", max_length=50, blank=True)

    emails = models.ManyToManyField(Email, through='PersonEmail')
    addresses = models.ManyToManyField(Address)
    phones = models.ManyToManyField(Phone, through='PersonPhone')

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

class Adult(models.Model):
    person = models.ForeignKey(Person)
    role = models.CharField("Role", max_length=10, choices=(
        ('parent', "Parent"),
        ('volunteer', "Volunteer"),
    ))
    company = models.ForeignKey(Company, null=True)
    mentor = models.BooleanField("Is Mentor", help_text="Is a mentor")

class Student(models.Model):
    person = models.ForeignKey(Person)
    school = models.ForeignKey(School)
    grad_year = models.IntegerField("Graduation Year")
    relationships = models.ManyToManyField(Adult, through='Relationship')

class Relationship(models.Model):
    student = models.ForeignKey(Student)
    adult = models.ForeignKey(Adult)
    relationship = models.CharField("Relationship", max_length=30)
    cc_on_email = models.BooleanField("CC on Emails", default=False)

class FeePaid(models.Model):
    student = models.ForeignKey(Student)
    year = models.IntegerField("Year")

    class Meta:
        verbose_name_plural = "Fees paid"

class TimeRecord(models.Model):
    person = models.ForeignKey(Person)
    location = models.CharField("Location", max_length=80)
    clock_in = models.DateTimeField("Clocked in")
    clock_out = models.DateTimeField("Clocked out", null=True)
    hours = models.FloatField("Hours")
    recorded = models.DateField("Recorded")

