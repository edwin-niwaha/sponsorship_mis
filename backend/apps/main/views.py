from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.views import View


def home(request):
    return render(request, "users/home.html")


def dashboard(request):
    return render(request, "main/dashoard.html")
