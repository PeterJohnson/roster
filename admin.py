from django.contrib import admin
from django.contrib.localflavor.us.forms import *
from django import forms
from roster.models import *

def schools_as_choices():
    schools = []
    for school in School.objects.order_by('type', 'longname'):
        stype = school.get_type_display()+"s"
        if not schools or schools[-1][0] != stype:
            schools.append([stype, []])
        schools[-1][1].append((school.id, school.longname))

    return schools

#def people_as_choices():
#    people = []
#    for model in [Student, Adult, Contact]:
#        people.append([model._meta.verbose_name_plural.capitalize(), []])
#        for person in model.objects.all():
#            people[-1][1].append((person.id, unicode(person)))
#
#    return people

class TeamAdmin(admin.ModelAdmin):
    list_display = ['name', 'program']

class PersonInline(admin.TabularInline):
    model = Person
    extra = 1

class PositionAdmin(admin.ModelAdmin):
    list_display = ['title', 'steering']
    list_filter = ['steering']
    inlines = [PersonInline]
    #fieldsets = [(None, {'fields': ['title', 'steering', 'people']})]

class SchoolAdmin(admin.ModelAdmin):
    list_display = ['__unicode__', 'name', 'type']

class EmailPersonInline(admin.TabularInline):
    model = PersonEmail
    extra = 1
    verbose_name = 'Person'
    verbose_name_plural = 'People'

class EmailAdmin(admin.ModelAdmin):
    list_display = ['email', 'location']
    #inlines = [EmailPersonInline]

class AddressPersonInline(admin.TabularInline):
    model = Person.addresses.through
    extra = 1
    max_num = 1
    verbose_name = 'Person'
    verbose_name_plural = 'People'

class AddressAdminForm(forms.ModelForm):
    class Meta:
        model = Address

    def __init__(self, *args, **kwargs):
        super(AddressAdminForm, self).__init__(*args, **kwargs)
        self.fields['zipcode'] = USZipCodeField()

class AddressAdmin(admin.ModelAdmin):
    form = AddressAdminForm
    list_display = ['line1', 'city', 'state', 'zipcode']
    list_filter = ['city', 'state', 'zipcode']
    #inlines = [AddressPersonInline]

class PhonePersonInline(admin.TabularInline):
    model = PersonPhone
    extra = 1
    verbose_name = 'Person'
    verbose_name_plural = 'People'

class PhoneAdmin(admin.ModelAdmin):
    list_display = ['full_phone', 'location']
    #inlines = [PhonePersonInline]

    def full_phone(self, obj):
        if obj.ext:
            return "%s x%s" % (obj.phone, obj.ext)
        else:
            return obj.phone

class PersonEmailInline(admin.TabularInline):
    model = PersonEmail
    extra = 1
    verbose_name = 'Email address'
    verbose_name_plural = 'Email addresses'

class PersonAddressInline(admin.TabularInline):
    model = Person.addresses.through
    extra = 1
    max_num = 1
    verbose_name = 'Address'
    verbose_name_plural = 'Addresses'

class PersonPhoneInline(admin.TabularInline):
    model = PersonPhone
    extra = 1
    verbose_name = 'Phone number'
    verbose_name_plural = 'Phone numbers'

class RelationshipAdminForm(forms.ModelForm):
    class Meta:
        model = Relationship

    def __init__(self, *args, **kwargs):
        super(RelationshipAdminForm, self).__init__(*args, **kwargs)
        #self.fields['person_to'].choices = people_as_choices()

class RelationshipInline(admin.TabularInline):
    model = Relationship
    form = RelationshipAdminForm
    fk_name = 'person_from'
    extra = 1
    verbose_name_plural = 'Relationships'

class ContactAdmin(admin.ModelAdmin):
    list_display = ['__unicode__', 'lastname', 'firstname']
    search_fields = ['^firstname', '^lastname']
    inlines = [PersonPhoneInline, RelationshipInline]
    exclude = ['addresses', 'emails']
    radio_fields = {'gender': admin.HORIZONTAL}

class AdultAdminForm(forms.ModelForm):
    class Meta:
        model = Adult

    def __init__(self, *args, **kwargs):
        super(AdultAdminForm, self).__init__(*args, **kwargs)
        self.fields['medical'].widget = \
                forms.widgets.Textarea(attrs={'rows':2, 'cols':60})
        self.fields['medications'].widget = \
                forms.widgets.Textarea(attrs={'rows':2, 'cols':60})
        self.fields['prospective_source'].widget = \
                forms.widgets.Textarea(attrs={'rows':2, 'cols':60})
        self.fields['comments'].widget = \
                forms.widgets.Textarea(attrs={'rows':2, 'cols':60})

class AdultAdmin(admin.ModelAdmin):
    form = AdultAdminForm
    list_display = ['__unicode__', 'lastname', 'firstname', 'role',
                    'mentor', 'company', 'status']
    list_filter = ['status', 'teams', 'role', 'mentor', 'company']
    search_fields = ['^firstname', '^lastname']
    inlines = [PersonEmailInline, PersonPhoneInline, PersonAddressInline,
               RelationshipInline]
    exclude = ['addresses']
    radio_fields = {'gender': admin.HORIZONTAL}
    fieldsets = [
        (None, {'fields': ['firstname', 'lastname', 'suffix', 'gender',
                           ('birth_month', 'birth_day', 'birth_year'),
                           'company', 'role', 'mentor',
                           'status', 'shirt_size',
                           'joined', 'badge', 'teams', 'left',
                           'receive_email', 'contact_public']}),
        ('Medical information', {'fields': ['medical', 'medications']}),
        ('Misc information', {'fields': ['prospective_source', 'comments']}),
    ]

class StudentAdminForm(forms.ModelForm):
    class Meta:
        model = Student

    def __init__(self, *args, **kwargs):
        super(StudentAdminForm, self).__init__(*args, **kwargs)
        self.fields['birth_year'].required = True
        self.fields['birth_month'].required = True
        self.fields['birth_day'].required = True
        self.fields['school'].choices = schools_as_choices()
        self.fields['medical'].widget = \
                forms.widgets.Textarea(attrs={'rows':2, 'cols':60})
        self.fields['medications'].widget = \
                forms.widgets.Textarea(attrs={'rows':2, 'cols':60})
        self.fields['prospective_source'].widget = \
                forms.widgets.Textarea(attrs={'rows':2, 'cols':60})
        self.fields['comments'].widget = \
                forms.widgets.Textarea(attrs={'rows':2, 'cols':60})

class StudentAdmin(admin.ModelAdmin):
    form = StudentAdminForm
    list_display = ['__unicode__', 'lastname', 'firstname', 'school',
                    'grad_year', 'status']
    list_filter = ['status', 'teams', 'school', 'grad_year']
    search_fields = ['^firstname', '^lastname']
    inlines = [PersonEmailInline, PersonPhoneInline, PersonAddressInline,
               RelationshipInline]
    exclude = ['addresses']
    radio_fields = {'gender': admin.HORIZONTAL}
    fieldsets = [
        (None, {'fields': ['firstname', 'lastname', 'suffix', 'gender',
                           ('birth_month', 'birth_day', 'birth_year'),
                           ('school', 'grad_year'),
                           'status', 'shirt_size',
                           'joined', 'badge', 'teams', 'left',
                           'receive_email', 'contact_public']}),
        ('Medical information', {'fields': ['medical', 'medications']}),
        ('Misc information', {'fields': ['prospective_source', 'comments']}),
    ]

class WaiverAdmin(admin.ModelAdmin):
    list_display = ['person', 'org', 'year']
    list_filter = ['org', 'year', 'person']

class TimeRecordAdmin(admin.ModelAdmin):
    list_display = ['person', 'event', 'clock_in', 'clock_out', 'hours',
                    'recorded']
    list_filter = ['event', 'clock_in', 'recorded', 'person']

class WaitlistEntryAdmin(admin.ModelAdmin):
    list_display = ['student', 'program', 'team', 'date']
    list_filter = ['program', 'team']

class EventPersonInlineForm(forms.ModelForm):
    class Meta:
        model = EventPerson

    def __init__(self, *args, **kwargs):
        super(EventPersonInlineForm, self).__init__(*args, **kwargs)
        #self.fields['person'].choices = people_as_choices()

class EventPersonInline(admin.TabularInline):
    form = EventPersonInlineForm
    model = EventPerson
    extra = 1
    verbose_name = 'Person'
    verbose_name_plural = 'People'

class EventAdmin(admin.ModelAdmin):
    list_display = ['name', 'location', 'date', 'time', 'end_date',
                    'end_time']
    list_filter = ['location', 'date']
    search_fields = ['name']
    inlines = [EventPersonInline]

admin.site.register(Organization)
admin.site.register(Program)
admin.site.register(Team, TeamAdmin)
admin.site.register(Position, PositionAdmin)
admin.site.register(School, SchoolAdmin)
admin.site.register(Company)
admin.site.register(Email, EmailAdmin)
admin.site.register(Address, AddressAdmin)
admin.site.register(Phone, PhoneAdmin)
admin.site.register(RelationshipType)
admin.site.register(Waiver, WaiverAdmin)
admin.site.register(Contact, ContactAdmin)
admin.site.register(Adult, AdultAdmin)
admin.site.register(Student, StudentAdmin)
admin.site.register(TimeRecord, TimeRecordAdmin)
admin.site.register(WaitlistEntry, WaitlistEntryAdmin)
admin.site.register(Event, EventAdmin)

