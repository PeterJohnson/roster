from django.contrib import admin
from roster.models import *

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

class AddressAdmin(admin.ModelAdmin):
    list_display = ['line1', 'city', 'state', 'zipcode']
    list_filter = ['city', 'state', 'zipcode']
    #inlines = [AddressPersonInline]

class PhonePersonInline(admin.TabularInline):
    model = PersonPhone
    extra = 1
    verbose_name = 'Person'
    verbose_name_plural = 'People'

class PhoneAdmin(admin.ModelAdmin):
    list_display = ['phone', 'location']
    #inlines = [PhonePersonInline]

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

class RelationshipInline(admin.TabularInline):
    model = Relationship
    extra = 1
    verbose_name_plural = 'Relationships'

class AdultAdmin(admin.ModelAdmin):
    list_display = ['__unicode__', 'lastname', 'firstname', 'lead', 'role',
                    'mentor', 'company', 'status']
    list_filter = ['status', 'lead', 'programs', 'role', 'mentor', 'company']
    inlines = [PersonAddressInline, PersonPhoneInline, PersonEmailInline,
               RelationshipInline]
    exclude = ['addresses']
    radio_fields = {'gender': admin.HORIZONTAL}
    fieldsets = [
        (None, {'fields': ['firstname', 'lastname', 'suffix', 'gender',
                           'status', 'company', 'role', 'mentor', 'programs',
                           'badge', 'joined', 'left', 'receive_email',
                           'contact_public', 'lead', 'position']}),
        ('Medical information', {'fields': ['medical', 'medications'],
                                 'classes': ['collapse']}),
        ('Emergency information', {'fields': ['emergency_contact',
                                              'emergency_contact_relation'],
                                   'classes': ['collapse']}),
        ('Misc information', {'fields': ['shirt_size', 'birthdate',
                                         'prospective_source', 'comments'],
                              'classes': ['collapse']}),
    ]

class StudentAdmin(admin.ModelAdmin):
    list_display = ['__unicode__', 'lastname', 'firstname', 'school',
                    'grad_year', 'status']
    list_filter = ['status', 'lead', 'programs', 'school', 'grad_year']
    inlines = [PersonAddressInline, PersonPhoneInline, PersonEmailInline,
               RelationshipInline]
    exclude = ['addresses']
    radio_fields = {'gender': admin.HORIZONTAL}
    fieldsets = [
        (None, {'fields': ['firstname', 'lastname', 'suffix', 'gender',
                           'status', 'school', 'grad_year', 'programs',
                           'badge', 'joined', 'left', 'waitlist_date',
                           'receive_email', 'contact_public',
                           'lead', 'position']}),
        ('Medical information', {'fields': ['medical', 'medications'],
                                 'classes': ['collapse']}),
        ('Emergency information', {'fields': ['emergency_contact',
                                              'emergency_contact_relation'],
                                   'classes': ['collapse']}),
        ('Misc information', {'fields': ['shirt_size', 'birthdate',
                                         'prospective_source', 'comments'],
                              'classes': ['collapse']}),
    ]

class WaiverAdmin(admin.ModelAdmin):
    list_display = ['person', 'org', 'year']
    list_filter = ['org', 'year', 'person']

class FeePaidAdmin(admin.ModelAdmin):
    list_display = ['student', 'year']
    list_filter = ['year', 'student']

class TimeRecordAdmin(admin.ModelAdmin):
    list_display = ['person', 'location', 'clock_in', 'clock_out', 'hours',
                    'recorded']
    list_filter = ['location', 'clock_in', 'recorded', 'person']

admin.site.register(Organization)
admin.site.register(Program)
admin.site.register(School, SchoolAdmin)
admin.site.register(Company)
admin.site.register(Email, EmailAdmin)
admin.site.register(Address, AddressAdmin)
admin.site.register(Phone, PhoneAdmin)
admin.site.register(Waiver, WaiverAdmin)
admin.site.register(Adult, AdultAdmin)
admin.site.register(Student, StudentAdmin)
admin.site.register(FeePaid, FeePaidAdmin)
admin.site.register(TimeRecord, TimeRecordAdmin)

