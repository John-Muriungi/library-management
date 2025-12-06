from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Book, BorrowRecord, Reservation, Table


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name',
                  'email', 'password1', 'password2')


class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = ['title', 'author', 'isbn', 'category',
                  'description', 'total_copies', 'cover_image']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }


class BorrowBookForm(forms.ModelForm):
    class Meta:
        model = BorrowRecord
        fields = ['due_date']
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}),
        }


class ReservationForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = ['reservation_date', 'start_time', 'end_time', 'purpose']
        widgets = {
            'reservation_date': forms.DateInput(attrs={'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
            'purpose': forms.Textarea(attrs={'rows': 3}),
        }


class TableForm(forms.ModelForm):
    class Meta:
        model = Table
        fields = ['table_number', 'capacity',
                  'location', 'status', 'description']
        widgets = {
            'table_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., T-001'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 10}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Main Hall, Reading Room'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Optional description...'}),
        }
