from django.contrib.admin import SimpleListFilter
from models import Person, PersonTeam, Team

class RoleListFilter(SimpleListFilter):
    title = "Role"
    parameter_name = 'role'

    def lookups(self, request, model_admin):
        choices = list(PersonTeam.ROLE_CHOICES)
        choices.append(('None', "None"))
        return choices

    def queryset(self, request, queryset):
        if not self.value():
            return queryset
        if self.value() == 'None':
            return queryset.exclude(id__in=PersonTeam.objects.all().values('person'))
        return queryset.filter(id__in=PersonTeam.objects.filter(
            role=self.value()).values('person'))

class StatusListFilter(SimpleListFilter):
    title = "Status"
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        return PersonTeam.STATUS_CHOICES

    def queryset(self, request, queryset):
        if not self.value():
            return queryset
        return queryset.filter(id__in=PersonTeam.objects.filter(
            status=self.value()).values('person'))

