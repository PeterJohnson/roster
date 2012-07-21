from django.contrib import admin
from django.contrib.admin.models import LogEntry
from django.contrib.localflavor.us.forms import *
from django import forms
from roster.models import *
from roster.fields import *
from roster.filters import *

def schools_as_choices():
    schools = [('', "---------")]
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
    #inlines = [MemberInline]
    #fieldsets = [(None, {'fields': ['title', 'steering', 'members']})]

class SchoolAdmin(admin.ModelAdmin):
    list_display = ['__unicode__', 'name', 'type']

class EmailPersonInline(admin.TabularInline):
    model = PersonEmail
    extra = 1
    verbose_name = 'Person'
    verbose_name_plural = 'People'

class EmailAdmin(admin.ModelAdmin):
    list_display = ['email', 'location']
    search_fields = ['email']
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
    search_fields = ['phone', 'ext']

    def full_phone(self, obj):
        if obj.ext:
            return "%s x%s" % (obj.phone, obj.ext)
        else:
            return obj.phone

class PersonTeamInlineForm(forms.ModelForm):
    class Meta:
        model = PersonTeam

    def __init__(self, *args, **kwargs):
        super(PersonTeamInlineForm, self).__init__(*args, **kwargs)
        self.fields['joined'] = \
                USDateFormField(widget=admin.widgets.AdminDateWidget)
        self.fields['joined'].required = False
        self.fields['left'] = \
                USDateFormField(widget=admin.widgets.AdminDateWidget)
        self.fields['left'].required = False

class PersonTeamInline(admin.TabularInline):
    model = PersonTeam
    form = PersonTeamInlineForm
    extra = 1
    verbose_name = 'Team'
    verbose_name_plural = 'Teams'

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

class PersonAdminForm(forms.ModelForm):
    class Meta:
        model = Person

    def __init__(self, *args, **kwargs):
        super(PersonAdminForm, self).__init__(*args, **kwargs)
        self.fields['school'].choices = schools_as_choices()
        self.fields['medical'].widget = \
                forms.widgets.Textarea(attrs={'rows':2, 'cols':60})
        self.fields['medications'].widget = \
                forms.widgets.Textarea(attrs={'rows':2, 'cols':60})
        self.fields['prospective_source'].widget = \
                forms.widgets.Textarea(attrs={'rows':2, 'cols':60})
        self.fields['comments'].widget = \
                forms.widgets.Textarea(attrs={'rows':2, 'cols':60})

class PersonAdmin(admin.ModelAdmin):
    form = PersonAdminForm
    list_display = ['__unicode__', 'lastname', 'get_firstname', 'active_roles']
    list_filter = ['teams', RoleListFilter, StatusListFilter, 'gender']
    search_fields = ['^firstname', '^lastname', '^nickname']
    inlines = [PersonTeamInline,
               PersonEmailInline,
               PersonPhoneInline,
               PersonAddressInline,
               RelationshipInline]
    radio_fields = {'gender': admin.HORIZONTAL}
    fieldsets = [
        (None, {'fields': ['firstname', 'lastname', 'suffix', 'nickname',
                           'gender',
                           ('birth_month', 'birth_day', 'birth_year'),
                           ('school', 'grad_year'),
                           'company',
                           'shirt_size',
                           'photo']}),
        ('Medical information', {'fields': ['medical', 'medications']}),
        ('Misc information', {'fields': ['prospective_source', 'comments']}),
    ]

class RelationshipTypeAdmin(admin.ModelAdmin):
    list_display = ['type', 'parent', 'sort_order']

class WaiverAdmin(admin.ModelAdmin):
    list_display = ['person', 'org', 'year']
    list_filter = ['org', 'year', 'person']

class TimeRecordAdmin(admin.ModelAdmin):
    list_display = ['person', 'event', 'clock_in', 'clock_out', 'hours',
                    'recorded']
    list_filter = ['event', 'clock_in', 'recorded', 'person']

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

class EventAdminForm(forms.ModelForm):
    class Meta:
        model = Event

    def __init__(self, *args, **kwargs):
        super(EventAdminForm, self).__init__(*args, **kwargs)
        self.fields['date'] = \
                USDateFormField(widget=admin.widgets.AdminDateWidget)
        self.fields['end_date'] = \
                USDateFormField(widget=admin.widgets.AdminDateWidget)
        self.fields['end_date'].required = False

class EventAdmin(admin.ModelAdmin):
    form = EventAdminForm
    list_display = ['name', 'location', 'date', 'time', 'end_date',
                    'end_time']
    list_filter = ['location', 'date']
    search_fields = ['name']
    inlines = [EventPersonInline]

class LogEntryAdmin(admin.ModelAdmin):
    list_display = ['__unicode__', 'user', 'action_time']
    readonly_fields = ('content_type', 'user', 'action_time')

admin.site.register(Organization)
admin.site.register(Program)
admin.site.register(Team, TeamAdmin)
admin.site.register(Position, PositionAdmin)
admin.site.register(School, SchoolAdmin)
admin.site.register(Company)
admin.site.register(Email, EmailAdmin)
admin.site.register(Address, AddressAdmin)
admin.site.register(Phone, PhoneAdmin)
admin.site.register(RelationshipType, RelationshipTypeAdmin)
admin.site.register(Waiver, WaiverAdmin)
admin.site.register(Person, PersonAdmin)
admin.site.register(TimeRecord, TimeRecordAdmin)
admin.site.register(Event, EventAdmin)
admin.site.register(LogEntry, LogEntryAdmin)

