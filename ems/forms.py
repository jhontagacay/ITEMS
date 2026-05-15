from django import forms
from django.utils import timezone
from .models import BorrowTransaction, Equipment, Division, User
from django.core.exceptions import ValidationError

class YourSignupForm(forms.ModelForm):
    email = forms.EmailField(required=False)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password']

class BorrowForm(forms.ModelForm):
    class Meta:
        model = BorrowTransaction
        fields = ['equipment', 'borrower_name', 'division', 'purpose', 'released_by']
        
        widgets = {
            'purpose': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Enter purpose here...',
            }),
            'due_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')

class ReturnForm(forms.ModelForm):
    class Meta:
        model = BorrowTransaction
        fields = ['returned_by', 'received_by', 'return_notes']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})

class DivisionForm(forms.ModelForm):
    class Meta:
        model = Division 
        fields = ['name']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].widget.attrs.update({'class': 'form-control', 'placeholder': 'e.g. OMCC'})
        
class RegistrationForm(forms.Form):
    username = forms.CharField(max_length=100)
    email = forms.EmailField(required=False)
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            raise ValidationError("Passwords do not match. Please re-enter.")
        
        return cleaned_data

class ReturnForm(forms.ModelForm):
    returned_by  = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control'}))
    received_by  = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control'}))
    return_notes = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}))
    
    class Meta:
        model = BorrowTransaction
        fields = ['returned_by', 'received_by', 'return_notes']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
    

class EquipmentForm(forms.ModelForm):
    class Meta:
        model  = Equipment
        fields = ['name', 'serial_number', 'status', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')

class TransactionFilterForm(forms.Form):
    SORT_CHOICES = [
        ('-date_borrowed', 'Newest first'),
        ('date_borrowed',  'Oldest first'),
        ('-date_returned', 'Recently returned'),
    ]
    search     = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search borrower or equipment...'}))
    division = forms.ModelChoiceField(queryset=Division.objects.all(), required=False,
                     empty_label='All division', widget=forms.Select(attrs={'class': 'form-select'}))
    status     = forms.ChoiceField(choices=[('', 'All statuses'), ('ongoing', 'Ongoing'), ('returned', 'Returned')],
                     required=False, widget=forms.Select(attrs={'class': 'form-select'}))
    date_from  = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    date_to    = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    sort       = forms.ChoiceField(choices=SORT_CHOICES, required=False,
                     widget=forms.Select(attrs={'class': 'form-select'}))