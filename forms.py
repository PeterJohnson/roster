# Forms
from django import forms
from roster.models import *
from django.contrib.localflavor.us.us_states import STATE_CHOICES
from django.contrib.localflavor.us.forms import *
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
    include_name = forms.BooleanField(label="Include Name",
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
    include_name = forms.BooleanField(label="Include Name",
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

class BadgesForm(forms.Form):
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

class AddressForm(forms.ModelForm):
    class Meta:
        model = Address

    def __init__(self, *args, **kwargs):
        super(AddressForm, self).__init__(*args, **kwargs)
        self.fields['zipcode'] = USZipCodeField()

class RegInitialForm(forms.Form):
    usertype = forms.ChoiceField(
        widget=forms.RadioSelect(),
        choices=(
            ('new', "New Member"),
            ('returning', "Returning Member"),
        ),
        initial='returning')

    person = forms.ModelChoiceField(
        required=False,
        queryset=Person.objects.all())

    def clean(self):
        cleaned_data = super(RegInitialForm, self).clean()
        usertype = cleaned_data.get("usertype")
        person = None
        if usertype == 'returning':
            person = cleaned_data.get("person")
            if person is None:
                self._errors["person"] = self.error_class(["Must select person if returning."])
        if person is None:
            person = Person()
        return dict(person=person)

class RegBasicForm(forms.Form):
    firstname = forms.CharField(label="First Name", max_length=100)
    lastname = forms.CharField(label="Last Name", max_length=100)
    suffix = forms.CharField(max_length=10, required=False)
    nickname = forms.CharField(max_length=50, required=False)

    gender = forms.ChoiceField(
        widget=forms.RadioSelect(),
        choices=Person.GENDER_CHOICES)

    def general_fields(self):
        for field in self:
            if field.name in ["firstname", "lastname", "suffix", "nickname"]:
                yield field

    association = forms.ChoiceField(
        widget=forms.RadioSelect(),
        choices=(
            ('student', "K-12 School"),
            ('mentor', "University/Company"),
        ))

    school = forms.ModelChoiceField(
        required=False,
        queryset=School.objects.all())
    grad_year = forms.ChoiceField(required=False, label="HS Grad year")

    company = forms.ModelChoiceField(
        required=False,
        queryset=Company.objects.all())
    company_other = forms.CharField(max_length=50, required=False, label="Other")

    birth_month = forms.IntegerField(
        min_value=1,
        max_value=12,
        error_messages={
            'required': u'Month is required.',
            'invalid': u'Enter a whole number for month.',
            'max_value': u'Month must be between 1 and 12.',
            'min_value': u'Month must be between 1 and 12.',
        })
    birth_day = forms.IntegerField(
        min_value=1,
        max_value=31,
        error_messages={
            'required': u'Day is required.',
            'invalid': u'Enter a whole number for day.',
            'max_value': u'Day must be between 1 and 31.',
            'min_value': u'Day must be between 1 and 31.',
        })
    birth_year = forms.IntegerField(
        required=False,
        min_value=1900,
        max_value=2100,
        error_messages={
            'required': u'Year is required.',
            'invalid': u'Enter a whole number for year.',
            'max_value': u'Please enter a 4 digit year.',
            'min_value': u'Please enter a 4 digit year.',
        })

    shirt_size = forms.ChoiceField(choices=Person.SHIRT_SIZE_CHOICES)

    medical = forms.CharField(label="Conditions/Allergies",
            widget=forms.Textarea,
            required=False)
    medications = forms.CharField(label="Medications",
            widget=forms.Textarea,
            required=False)

    def clean(self):
        cleaned_data = super(RegBasicForm, self).clean()

        person = self.initial["person"]

        person.firstname = cleaned_data.get("firstname", "")
        person.lastname = cleaned_data.get("lastname", "")
        person.suffix = cleaned_data.get("suffix", "")
        person.nickname = cleaned_data.get("nickname", "")
        if cleaned_data.get("gender"):
            person.gender = cleaned_data.get("gender")
        person.birth_month = cleaned_data.get("birth_month")
        person.birth_day = cleaned_data.get("birth_day")
        person.birth_year = cleaned_data.get("birth_year")
        person.shirt_size = cleaned_data.get("shirt_size", "")
        person.medical = cleaned_data.get("medical", "")
        person.medications = cleaned_data.get("medications", "")

        # check student/mentor specific data and clean as appropriate
        association = cleaned_data.get("association")
        company = None
        if association == 'student':
            msg = "This field is required."
            person.school = cleaned_data.get("school")
            if not person.school:
                self._errors["school"] = self.error_class([msg])
            person.grad_year = cleaned_data.get("grad_year")
            if not person.grad_year:
                self._errors["grad_year"] = self.error_class([msg])
            if not self.cleaned_data.get("birth_year"):
                self._errors["birth_year"] = self.error_class([u'Year is required.'])
        elif association == 'mentor':
            person.school = None
            person.grad_year = None
            company = cleaned_data.get("company")
            company_other = cleaned_data.get("company_other")
            if company:
                if company_other:
                    msg = "Specify company or other, not both"
                    self._errors["company"] = self.error_class([msg])
                    self._errors["company_other"] = self.error_class([msg])
            else:
                if not company_other:
                    msg = "Either company or other is required"
                    self._errors["company"] = self.error_class([msg])
                    self._errors["company_other"] = self.error_class([msg])
                else:
                    company = Company(name=company_other)
                    try:
                        company.full_clean()
                    except ValidationError, e:
                        self._errors["company_other"] = \
                                self.error_class(e.message_dict["name"])

        try:
            person.full_clean()
        except ValidationError, e:
            for k, v in e.message_dict.iteritems():
                if k not in self._errors:
                    self._errors[k] = self.error_class(v)
        return dict(association=association, company=company)

    def __init__(self, *args, **kwargs):
        force_grad_year = kwargs.pop("force_grad_year", None)
        super(RegBasicForm, self).__init__(*args, **kwargs)
        import datetime
        now = datetime.datetime.now()
        year = now.year
        if now.month > 6:
            year += 1
        grades = range(12,3,-1)
        years = [year-x+12 for x in grades]
        year_choices = []
        if force_grad_year not in years:
            if not force_grad_year:
                year_choices.append(("", "---------"))
            else:
                year_choices.append(("%d" % force_grad_year,
                                     "Graduated (%d)" % force_grad_year))
        year_choices.extend(reversed([
                ("%d" % year, "%dth grade (%d)" % (grade, year))
                for grade, year in zip(grades, years)]))
        self.fields['grad_year'].choices = year_choices

class RegPhoneForm(forms.Form):
    home_phone = USPhoneNumberField(required=False)
    mobile_phone = USPhoneNumberField(label="Cell Phone", required=False)
    work_phone = USPhoneNumberField(required=False)
    work_ext = forms.CharField(max_length=5, required=False)
    other_phone = USPhoneNumberField(required=False)
    other_ext = forms.CharField(max_length=5, required=False)
    primary = forms.ChoiceField(
        widget=forms.RadioSelect(),
        choices=Phone.LOCATION_CHOICES,
        initial='Mobile')

    def clean(self):
        cleaned_data = super(RegPhoneForm, self).clean()
        primary = cleaned_data.get("primary")
        if primary is None:
            raise ValidationError("Must specify primary phone number")
        fieldname = primary.lower()+"_phone"
        if not cleaned_data.get(fieldname):
            if fieldname not in self._errors:
                self._errors[fieldname] = self.error_class(["Must specify primary phone number."])
            cleaned_data.pop(fieldname, None)
        return cleaned_data

class RegGuardian1Form(forms.Form):
    relationship = forms.ModelChoiceField(
        required=False,
        queryset=RelationshipType.objects.all())

    firstname = forms.CharField(label="First Name", max_length=100,
            required=False)
    lastname = forms.CharField(label="Last Name", max_length=100,
            required=False)
    suffix = forms.CharField(max_length=10, required=False)
    nickname = forms.CharField(max_length=50, required=False)

    gender = forms.ChoiceField(
        required=False,
        widget=forms.RadioSelect(),
        choices=Person.GENDER_CHOICES)

    company = forms.ModelChoiceField(
        required=False,
        queryset=Company.objects.all())
    company_other = forms.CharField(max_length=50, required=False, label="Other")

    def clean_inner(self, cleaned_data, need_company=True):
        # check for required fields based on type
        for fieldname in ["relationship", "firstname", "lastname", "gender"]:
            if not cleaned_data.get(fieldname):
                print fieldname
                self._errors[fieldname] = self.error_class(["This field is required."])

        relationship = cleaned_data.get("relationship")

        guardian = self.initial["guardian"]
        firstname = cleaned_data.get("firstname", "")
        lastname = cleaned_data.get("lastname", "")
        gender = cleaned_data.get("gender", "")
        if firstname != guardian.firstname or lastname != guardian.lastname:
            try:
                guardian = Person.objects.get(firstname=firstname,
                        lastname=lastname)
            except Person.DoesNotExist:
                guardian = Person(firstname=firstname, lastname=lastname)
                guardian.gender = gender
        if guardian.gender and gender != guardian.gender:
            self._errors["gender"] = self.error_class(["Cannot change gender."])
        else:
            guardian.gender = gender
        guardian.suffix = cleaned_data.get("suffix", "")
        guardian.nickname = cleaned_data.get("nickname", "")

        try:
            guardian.full_clean()
        except ValidationError, e:
            for k, v in e.message_dict.iteritems():
                print k, v
                if k not in self._errors:
                    self._errors[k] = self.error_class(v)

        company = None
        if need_company:
            company = cleaned_data.get("company")
            company_other = cleaned_data.get("company_other")
            if company:
                if company_other:
                    msg = "Specify company or other, not both"
                    self._errors["company"] = self.error_class([msg])
                    self._errors["company_other"] = self.error_class([msg])
            else:
                if not company_other:
                    msg = "Either company or other is required"
                    self._errors["company"] = self.error_class([msg])
                    self._errors["company_other"] = self.error_class([msg])
                else:
                    company = Company(name=company_other)
                    try:
                        company.full_clean()
                    except ValidationError, e:
                        self._errors["company_other"] = \
                                self.error_class(e.message_dict["name"])

        return dict(guardian=guardian, relationship=relationship,
                company=company)

    def clean(self):
        cleaned_data = super(RegGuardian1Form, self).clean()
        return self.clean_inner(cleaned_data)

class RegGuardian2Form(RegGuardian1Form):
    only_one_guardian = forms.BooleanField(required=False)

    def clean(self):
        cleaned_data = super(RegGuardian1Form, self).clean()
        only_one = bool(cleaned_data.get("only_one_guardian"))
        if only_one:
            return dict(guardian=None, relationship=None)
        return super(RegGuardian2Form, self).clean_inner(cleaned_data)

class RegGuardian1AddressForm(forms.Form):
    address_type = forms.ChoiceField(
        widget=forms.RadioSelect(),
        choices=(
            ('same', "Same as Student"),
            ('new', "Independent/New"),
        ),
        initial='same')

    line1 = forms.CharField(max_length=50, required=False)
    line2 = forms.CharField(max_length=50, required=False)
    city = forms.CharField(max_length=50, required=False)
    state_choices = [("", "---------")]
    state_choices.extend(STATE_CHOICES),
    state = forms.ChoiceField(choices=state_choices, required=False)
    zipcode = USZipCodeField(required=False)

    def clean(self):
        cleaned_data = super(RegGuardian1AddressForm, self).clean()
        address_type = cleaned_data.get("address_type")
        if address_type == "same":
            address = self.initial["student"]
        elif address_type == "same1":
            address = self.initial["guardian1"]
        elif address_type == "new":
            address = self.initial["address"]
            if not address:
                address = Address()
            address.line1 = cleaned_data.get("line1", "")
            address.line2 = cleaned_data.get("line2", "")
            address.city = cleaned_data.get("city", "")
            address.state = cleaned_data.get("state", "")
            address.zipcode = cleaned_data.get("zipcode", "")
            try:
                # don't check uniqueness
                address.clean_fields()
                address.clean()
            except ValidationError, e:
                for k, v in e.message_dict.iteritems():
                    if k not in self._errors:
                        self._errors[k] = self.error_class(v)
        else:
            address = None
        return dict(address=address)

class RegGuardian2AddressForm(RegGuardian1AddressForm):
    def __init__(self, *args, **kwargs):
        super(RegGuardian2AddressForm, self).__init__(*args, **kwargs)
        self.fields['address_type'].choices = (
                ('same', "Same as Student"),
                ('new', "Independent/New"),
                ('same1', "Same as Guardian 1"),
                )

class RegEmailForm(forms.Form):
    email = forms.EmailField(required=False)
    guardian1_email = forms.EmailField(required=False)
    guardian1_cc = forms.BooleanField(required=False)
    guardian2_email = forms.EmailField(required=False)
    guardian2_cc = forms.BooleanField(required=False)

    def clean(self):
        cleaned_data = super(RegEmailForm, self).clean()
        guardian1 = self.initial["guardian1"]
        guardian2 = self.initial["guardian2"]
        email = cleaned_data.get("email")
        if not guardian1 and not guardian2:
            if not email:
                self._errors["email"] = self.error_class(["This field is required."])
        else:
            if not email and not cleaned_data.get("guardian1_email") and not cleaned_data.get("guardian2_email"):
                raise ValidationError("At least one e-mail address is required.")
            if not email and not (cleaned_data.get("guardian1_cc") or cleaned_data.get("guardian2_cc")):
                raise ValidationError("At least one guardian must be on CC if student address not provided.")
        return cleaned_data

class RegEmergencyForm(RegGuardian1Form):
    def __init__(self, *args, **kwargs):
        super(RegEmergencyForm, self).__init__(*args, **kwargs)
        del self.fields['company']
        del self.fields['company_other']

    def clean(self):
        cleaned_data = super(RegGuardian1Form, self).clean()
        return super(RegEmergencyForm, self).clean_inner(cleaned_data,
                need_company=False)

class RegTeamForm(forms.Form):
    team = forms.ModelChoiceField(
        queryset=Team.objects.filter(reg_show=True))
