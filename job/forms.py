from django.forms import forms
from .models import Job
class JobForm(forms.modelForm):
    class Meta:
        model=Job
        fields=['location','date','time','special_requirements']