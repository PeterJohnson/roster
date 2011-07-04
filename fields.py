from django import forms
import datetime
import time
import settings

class USDateFormField(forms.DateField):
    def __init__(self, input_formats=None, *args, **kwargs):
        super(USDateFormField, self).__init__(*args, **kwargs)
        self.input_formats = input_formats or settings.DATE_INPUT_FORMATS

    def clean(self, value):
        super(forms.DateField, self).clean(value)
        if value in forms.fields.EMPTY_VALUES:
            return None
        if isinstance(value, datetime.datetime):
            return value.date()
        if isinstance(value, datetime.date):
            return value
        for format in self.input_formats:
            try:
                y, m, d = time.strptime(value, format)[:3]
                if y == 1900:
                    y = datetime.datetime.now().year
                return datetime.date(y, m, d)
            except ValueError:
                continue
        raise forms.util.ValidationError(self.error_messages['invalid'])

