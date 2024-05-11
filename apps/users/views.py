from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, PasswordChangeView, PasswordResetView
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View

from .forms import (
    ContactForm,
    LoginForm,
    RegisterForm,
    UpdateProfileForm,
    UpdateUserForm,
)
from .models import Profile


def home(request):
    return render(request, "users/home.html")


class RegisterView(View):
    form_class = RegisterForm
    initial = {"key": "value"}
    template_name = "users/register.html"

    def dispatch(self, request, *args, **kwargs):
        # will redirect to the home page if a user tries to access the register page while logged in
        if request.user.is_authenticated:
            return redirect(to="/")

        # else process dispatch as it otherwise normally would
        return super(RegisterView, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        form = self.form_class(initial=self.initial)
        return render(request, self.template_name, {"form": form})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)

        if form.is_valid():
            form.save()

            username = form.cleaned_data.get("username")
            messages.success(request, f"Account created for {username}")

            return redirect(to="login")

        return render(request, self.template_name, {"form": form})


# Class based view that extends from the built in login view to add a remember me functionality
class CustomLoginView(LoginView):
    form_class = LoginForm

    def form_valid(self, form):
        remember_me = form.cleaned_data.get("remember_me")

        if not remember_me:
            # set session expiry to 0 seconds. So it will automatically close the session after the browser is closed.
            self.request.session.set_expiry(0)

            # Set session as modified to force data updates/cookie to be saved.
            self.request.session.modified = True

        # else browser session will be as long as the session cookie time "SESSION_COOKIE_AGE" defined in settings.py
        return super(CustomLoginView, self).form_valid(form)


class ResetPasswordView(SuccessMessageMixin, PasswordResetView):
    template_name = "users/password_reset.html"
    email_template_name = "users/password_reset_email.html"
    subject_template_name = "users/password_reset_subject"
    success_message = (
        "We've emailed you instructions for setting your password, "
        "if an account exists with the email you entered. You should receive them shortly."
        " If you don't receive an email, "
        "please make sure you've entered the address you registered with, and check your spam folder."
    )
    success_url = reverse_lazy("users-home")


class ChangePasswordView(PasswordChangeView):
    template_name = "users/change_password.html"
    success_message = "Successfully Changed Your Password"
    success_url = reverse_lazy("users-home")

@login_required
def profile(request):
    try:
        profile_instance = request.user.profile
    except ObjectDoesNotExist:
        # If the user doesn't have a profile, create one
        profile_instance = Profile.objects.create(user=request.user, bio='', avatar='default.jpg')

    if request.method == "POST":
        user_form = UpdateUserForm(request.POST, instance=request.user)
        profile_form = UpdateProfileForm(
            request.POST, request.FILES, instance=profile_instance
        )

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "Your profile is updated successfully")
            return redirect(to="users-profile")
    else:
        user_form = UpdateUserForm(instance=request.user)
        profile_form = UpdateProfileForm(instance=profile_instance)

    return render(
        request,
        "users/profile.html",
        {"user_form": user_form, "profile_form": profile_form},
    )


def contact_us(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            instance = form.save()

            try:
                # Send email to the user
                subject = 'Your message has been received'
                message = f"Hello {instance.name},\n\nYour message has been received. \
We will get back to you soon!\n\nThanks,\nPerpetual - SDMS\nManagement"
                from_email = settings.EMAIL_HOST_USER  # Use default from email from settings
                to = [instance.email]  # Access email entered in the form
                send_mail(subject, message, from_email, to)

                # Set success message
                messages.success(request, "Your message has been sent successfully. \
We will get back to you soon!")
            except Exception as e:
                # Handle exceptions such as email address not found or internet being off
                print("An error occurred while sending email:", str(e))
                messages.error(request, "Sorry, an error occurred while sending your \
message. Please try again later.")

            # Redirect to the contact page
            return HttpResponseRedirect(reverse('contact_us'))
    else:
        form = ContactForm()

    return render(request, 'users/contact_us.html', {'form': form})