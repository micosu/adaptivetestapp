from django import forms
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from .models import TestSession

class TestSessionForm(forms.ModelForm):
    class Meta: 
        model = TestSession
        fields = ('age', 'grade', 'hours', 'language')
        # fields = ('lexile', 'age', 'grade', 'hours', 'language')
        widgets = {
            'bio': forms.Textarea(attrs= {'id': 'id_bio_input_text', 'rows': 3}),
            'picture': forms.FileInput(attrs={'id': 'id_profile_picture'})
        }
        labels = {
            'bio': "",
            'picture': "Upload Picture"
        }

    GRADE_CHOICES = [
        ('K-1', 'K-1st'),
        ('2-3', '2nd-3rd'),
        ('4-5', '4th-5th'),
        ('6-8', '6th-8th'),
        ('9-10', '9th-10th'),
        ('11-12', '11th-12th'),
        ('college', 'College'),
        ('none', 'Not in school'),
    ]
    
    age = forms.IntegerField(label="How old are you?")
    grade = forms.ChoiceField(label="What grade are you in?", choices=GRADE_CHOICES)
    hours = forms.FloatField(label="How many hours per week do you read?")
    language = forms.TypedChoiceField(
        label="Is English your first language?",
        choices=[(True, 'Yes'), (False, 'No')],
        coerce=lambda x: x == 'True',
        widget=forms.RadioSelect,
        required=True
    )
    # lexile = forms.IntegerField(label="What is your current lexile score (optional)", required=False)
    

    # def clean_lexile(self):
    #     cleaned_data = super().clean()
    #     lexile = cleaned_data.get('lexile')
    #     if lexile is None:
    #         return lexile

    #     if lexile < 0 or lexile > 2000:
    #         raise forms.ValidationError('Lexile score should be in the range 0 - 2000')
    #     return lexile
    
    def clean_hours(self):
        cleaned_data = super().clean()
        hours = cleaned_data.get('hours')

        if hours < 0 or hours > 168:
            raise forms.ValidationError('This should just be how many hours you read per week')
        return hours
    
    def clean_age(self):
        cleaned_data = super().clean()
        age = cleaned_data.get('age')

        if age < 0 or age > 100:
            raise forms.ValidationError('Wordtag works best if you are between 4 - 100 years old')
        return age
        

    