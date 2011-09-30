# Forms
from django import forms
from roster.models import *
from django.utils.safestring import mark_safe

class HorizRadioRenderer(forms.RadioSelect.renderer):
    """ this overrides widget method to put radio buttons horizontally
        instead of vertically.
    """
    def render(self):
            """Outputs radios"""
            return mark_safe(u'\n'.join([u'%s\n' % w for w in self]))

class TeamReportForm(forms.Form):
    who = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        choices=(
            ('Parent', "Parent"),
            ('Mentor', "Mentor"),
            ('Student', "Student"),
            ('Fan', "Fan"),
        ),
        initial=['Parent', 'Mentor', 'Student'])

    status = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        choices=PersonTeam.STATUS_CHOICES,
        initial=['Active'])

    team = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        choices=[(x.id, x.name) for x in Team.objects.all()])

class EmailListForm(TeamReportForm):
    cc_on_email = forms.BooleanField(label="Include Parent CC",
                                     required=False, initial=True)
    separator = forms.ChoiceField(
        widget=forms.RadioSelect(renderer=HorizRadioRenderer),
        choices=((',',","),(';',";"),('',"None")),
        initial=',',
        required=False)

class PhoneListForm(TeamReportForm):
    pass

class ContactListForm(TeamReportForm):
    cc_on_email = forms.BooleanField(label="Include Parent CC",
                                     required=False, initial=True)

class TshirtListForm(TeamReportForm):
    pass

class EventEmailListForm(forms.Form):
    who = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        choices=(
            ('Volunteer', "Volunteer"),
            ('Participant', "Participant")),
        initial=['Volunteer', 'Participant'])
    event = forms.ModelChoiceField(
        queryset=Event.objects.filter(calendar_post=True))
    cc_on_email = forms.BooleanField(label="Include Parent CC",
                                     required=False, initial=True)
    separator = forms.ChoiceField(
        widget=forms.RadioSelect(renderer=HorizRadioRenderer),
        choices=((',',","),(';',";"),('',"None")),
        initial=',',
        required=False)

class TeamRegVerifyForm(forms.Form):
    who = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        choices=(
            ('Mentor', "Mentor"),
            ('Student', "Student"),
        ),
        initial=['Mentor', 'Student'])

    team = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        choices=[(x.id, x.name) for x in Team.objects.all()])

class TeamMembershipForm(forms.Form):
    team = forms.ModelChoiceField(
        queryset=Team.objects.all(), required=False)

class ClassTeamListForm(forms.Form):
    no_team = forms.BooleanField(label="Only no team", required=False,
                                 initial=False)
    class_begin = forms.IntegerField(label="Beginning class")
    class_end = forms.IntegerField(label="Ending class")

