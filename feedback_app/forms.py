from django import forms
from feedback_app.models import UserFeedback, CorrectionRequest
class FeedbackForm(forms.ModelForm):
    class Meta: model=UserFeedback; fields=["name","email","message"]
class CorrectionForm(forms.ModelForm):
    class Meta: model=CorrectionRequest; fields=["article_url","name","email","description"]
