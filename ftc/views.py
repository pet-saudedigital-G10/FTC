from django.views.generic import CreateView
from django.urls import reverse_lazy
from django.shortcuts import render


# Create your views here.

def homepage(request):
    return render(request, 'home.html')