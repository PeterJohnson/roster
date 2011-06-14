from django.contrib import admin
from roster.models import *

class PersonPhoneInline(admin.StackedInline):
    model = PersonPhone
    extra = 1

class PersonEmailInline(admin.StackedInline):
    model = PersonEmail
    extra = 1

class PersonAdmin(admin.ModelAdmin):
    inlines = [PersonPhoneInline, PersonEmailInline]
    list_filter = ['status', 'lead', 'programs']

admin.site.register(Organization)
admin.site.register(Program)
admin.site.register(School)
admin.site.register(Company)
admin.site.register(Email)
admin.site.register(Address)
admin.site.register(Phone)
admin.site.register(Person, PersonAdmin)
#admin.site.register(PersonEmail)
#admin.site.register(PersonPhone)
admin.site.register(Waiver)
admin.site.register(Adult)
admin.site.register(Student)
admin.site.register(Relationship)
admin.site.register(FeePaid)
admin.site.register(TimeRecord)

