import json
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.decorators import login_required
from django.views import View
from .models import Book
from .forms import BookForm

def home(request):
    return render(request, "users/home.html")


@login_required
def dashboard(request):
    return render(request, "main/dashoard.html")


# @login_required
# def child_list(request):
#     return render(request, "main/child/manage_child.html")
@login_required
def child_list(request):
    return render(request, 'main/child/manage_child.html', {})
@login_required
def book_list(request):
    books = Book.objects.all()
    return render(request, 'main/child/child_list.html', {'books': books})
@login_required
def add_book(request):
    if request.method == "POST":
        form = BookForm(request.POST)
        if form.is_valid():
            book = Book.objects.create(
                title = form.cleaned_data.get('title'),
                author = form.cleaned_data.get('author'),
                description = form.cleaned_data.get('description'),
                year = form.cleaned_data.get('year')
            )
            return HttpResponse(
                status=204,
                headers={
                    'HX-Trigger': json.dumps({
                        "bookListChanged": None,
                        "showMessage": f"{book.title} added."
                    })
                })
        else:
            return render(request, 'main/child/child_form.html', {
                'form': form,
            })
    else:
        form = BookForm()
    return render(request, 'main/child/child_form.html', {
        'form': form,
    })
@login_required
def edit_book(request, pk):
    book = get_object_or_404(Book, pk=pk)
    if request.method == "POST":
        form = BookForm(request.POST, initial={
            'title' : book.title,
            'author' : book.author,
            'description' : book.description,
            'year': book.year
        })
        if form.is_valid():
            book.title = form.cleaned_data.get('title')
            book.author = form.cleaned_data.get('author')
            book.description = form.cleaned_data.get('description')
            book.year = form.cleaned_data.get('year')

            book.save()
            return HttpResponse(
                status=204,
                headers={
                    'HX-Trigger': json.dumps({
                        "bookListChanged": None,
                        "showMessage": f"{book.title} updated."
                    })
                }
            )
        else:
            return render(request, 'main/child/child_form.html', {
                'form': form,
                'book': book,
            })
    else:
        form = BookForm(initial={
            'title' : book.title,
            'author' : book.author,
            'description' : book.description,
            'year': book.year
            })
    return render(request, 'main/child/child_form.html', {
        'form': form,
        'book': book,
    })
@login_required
def remove_book_confirmation(request, pk):
    book = get_object_or_404(Book, pk=pk)
    return render(request, 'main/child/child_delete_confirmation.html', {
        'book': book,
    })
@login_required
@ require_POST
def remove_book(request, pk):
    book = get_object_or_404(Book, pk=pk)
    book.delete()
    return HttpResponse(
        status=204,
        headers={
            'HX-Trigger': json.dumps({
                "bookListChanged": None,
                "showMessage": f"{book.title} deleted."
            })
        })