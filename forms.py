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

class EmailListForm(forms.Form):
    who = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        choices=(
            ('Parent', "Parent"),
            ('Volunteer', "Volunteer"),
            ('Mentor', "Mentor"),
            ('Student', "Student")),
        initial=['Parent', 'Volunteer', 'Mentor', 'Student'])

    active_fll = forms.BooleanField(label="Active FLL", required=False)
    active_ftc = forms.BooleanField(label="Active FTC", required=False)
    active_frc = forms.BooleanField(label="Active FRC", required=False)
    fll_waitlist = forms.BooleanField(label="FLL Waitlist", required=False)
    cc_on_email = forms.BooleanField(label="Include Parent CC",
                                     required=False, initial=True)
    separator = forms.ChoiceField(
        widget=forms.RadioSelect(renderer=HorizRadioRenderer),
        choices=((',',","),(';',";")), initial=',')

class PhoneListForm(forms.Form):
    who = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        choices=(
            ('Parent', "Parent"),
            ('Volunteer', "Volunteer"),
            ('Mentor', "Mentor"),
            ('Student', "Student")),
        initial=['Parent', 'Volunteer', 'Mentor', 'Student'])

    active_fll = forms.BooleanField(label="Active FLL", required=False)
    active_ftc = forms.BooleanField(label="Active FTC", required=False)
    active_frc = forms.BooleanField(label="Active FRC", required=False)
    fll_waitlist = forms.BooleanField(label="FLL Waitlist", required=False)

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
        choices=((',',","),(';',";")), initial=',')

class TeamMembershipForm(forms.Form):
    team = forms.ModelChoiceField(
        queryset=Team.objects.all(), required=False)

