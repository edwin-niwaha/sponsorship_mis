from django.shortcuts import render


def reports_dash(request):
    return render(request, "main/reports/_reports_dash_.html")
