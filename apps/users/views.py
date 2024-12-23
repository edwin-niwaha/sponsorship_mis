from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, PasswordChangeView, PasswordResetView
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.storage import default_storage
from django.core.mail import send_mail
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import transaction
from django.http import (
    HttpResponseBadRequest,
    HttpResponseRedirect,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View

from apps.users.decorators import (
    admin_or_manager_or_staff_required,
    admin_or_manager_required,
    admin_required,
)

from .forms import (
    ContactForm,
    DocumentForm,
    EbookForm,
    LoginForm,
    PolicyForm,
    RegisterForm,
    UpdateProfileAllForm,
    UpdateProfileForm,
    UpdateUserForm,
)
from .models import (
    Contact,
    DocumentUpload,
    Ebook,
    Policy,
    PolicyRead,
    Profile,
)


# =================================== Home User  ===================================
def home(request):
    return render(request, "accounts/home.html")


# =================================== Register User  ===================================
class RegisterView(View):
    form_class = RegisterForm
    initial = {"key": "value"}
    template_name = "accounts/register.html"

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
            messages.success(
                request, f"Account created for {username}", extra_tags="bg-success"
            )

            return redirect(to="login")

        return render(request, self.template_name, {"form": form})


# =================================== Login View ===================================


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


# =================================== Reset password View  ===================================


class ResetPasswordView(SuccessMessageMixin, PasswordResetView):
    template_name = "accounts/password_reset.html"
    email_template_name = "accounts/password_reset_email.html"
    subject_template_name = "accounts/password_reset_subject"
    success_message = (
        "We've emailed you instructions for setting your password, "
        "if an account exists with the email you entered. You should receive them shortly."
        " If you don't receive an email, "
        "please make sure you've entered the address you registered with, and check your spam folder."
    )
    success_url = reverse_lazy("users-home")


# =================================== Change Passord  ===================================


class ChangePasswordView(PasswordChangeView):
    template_name = "accounts/change_password.html"
    success_message = "Successfully Changed Your Password"
    success_url = reverse_lazy("users-home")


# =================================== Profile List View  ===================================


@login_required
@admin_required
def profile_list(request):
    # Fetch all profiles and related user data
    queryset = Profile.objects.select_related("user").all().order_by("user__username")

    # Search functionality
    search_query = request.GET.get("search")
    if search_query:
        queryset = queryset.filter(user__username__icontains=search_query)

    # Pagination
    paginator = Paginator(queryset, 50)
    page_number = request.GET.get("page")

    try:
        profiles = paginator.page(page_number)
    except PageNotAnInteger:
        # If page is not an integer, deliver the first page.
        profiles = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g., 9999), deliver the last page of results.
        profiles = paginator.page(paginator.num_pages)

    return render(
        request,
        "accounts/profile_list.html",  # Ensure this is the correct template name
        {
            "profiles": profiles,
            "table_title": "Profile List",
        },
    )


# =================================== Update Profile ===================================
@login_required
@transaction.atomic
def update_profile(request, pk, template_name="accounts/profile_update.html"):
    profile = get_object_or_404(Profile, pk=pk)

    if request.method == "POST":
        form = UpdateProfileAllForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Updated successfully!", extra_tags="bg-success")
            return redirect("profile_list")
    else:
        form = UpdateProfileAllForm(instance=profile)

    # Render the form in the template
    context = {"form_name": "Update Profile", "form": form}
    return render(request, template_name, context)


# =================================== Profile Update ===================================
@login_required
@transaction.atomic
def profile(request):
    try:
        profile_instance = request.user.profile
    except ObjectDoesNotExist:
        # If the user doesn't have a profile, create one
        profile_instance = Profile.objects.create(
            user=request.user, bio="", avatar="default.jpg"
        )

    if request.method == "POST":
        user_form = UpdateUserForm(request.POST, instance=request.user)
        profile_form = UpdateProfileForm(
            request.POST, request.FILES, instance=profile_instance
        )

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(
                request, "Your profile is updated successfully", extra_tags="bg-success"
            )
            return redirect(to="users-profile")
    else:
        user_form = UpdateUserForm(instance=request.user)
        profile_form = UpdateProfileForm(instance=profile_instance)

    return render(
        request,
        "accounts/profile.html",
        {"user_form": user_form, "profile_form": profile_form},
    )


# =================================== Delete Profile ===================================
@login_required
@admin_or_manager_required
@transaction.atomic
def delete_profile(request, pk):
    profile = Profile.objects.get(id=pk)
    profile.delete()
    messages.info(request, "Profile deleted successfully!", extra_tags="bg-danger")
    return HttpResponseRedirect(reverse("profile_list"))


# =================================== View Policy  ===================================


@login_required
@admin_or_manager_or_staff_required
def policy_list(request):
    queryset = Policy.objects.all().order_by("id")

    search_query = request.GET.get("search")
    if search_query:
        queryset = queryset.filter(title__icontains=search_query)

    paginator = Paginator(queryset, 50)
    page = request.GET.get("page")

    try:
        records = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        records = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        records = paginator.page(paginator.num_pages)

    return render(
        request,
        "accounts/policy_list.html",
        {"records": records, "table_title": "Policies"},
    )


# =================================== Register Policy  ===================================


@login_required
@admin_or_manager_required
@transaction.atomic
def upload_policy(request):
    if request.method == "POST":
        form = PolicyForm(request.POST, request.FILES)

        if form.is_valid():
            form.save()
            messages.success(
                request, "Record saved successfully!", extra_tags="bg-success"
            )
            return redirect("policy_list")
        else:
            # Display an error message if the form is not valid
            messages.error(
                request,
                "There was an error saving the record. Please check the form for errors.",
                extra_tags="bg-danger",
            )

    else:
        form = PolicyForm()

    return render(
        request,
        "accounts/policy_upload.html",
        {"form_name": "Create Policy", "form": form},
    )


# =================================== Update Policy ===================================
@login_required
@admin_or_manager_required
@transaction.atomic
def update_policy(request, pk, template_name="accounts/policy_upload.html"):
    try:
        policy = Policy.objects.get(pk=pk)
    except Policy.DoesNotExist:
        messages.error(request, "Record not found!", extra_tags="bg-danger")
        return redirect("policy_list")  # Or a relevant error page

    if request.method == "POST":
        form = PolicyForm(request.POST, request.FILES, instance=policy)
        if form.is_valid():
            form.save()

            messages.success(
                request, "Policy updated successfully!", extra_tags="bg-success"
            )
            return redirect("policy_list")
    else:
        form = PolicyForm(instance=policy)

    context = {"form_name": "POLICY UPDATE", "form": form}
    return render(request, template_name, context)


# =================================== Delete selected Policy ===================================
@login_required
@admin_or_manager_required
@transaction.atomic
def delete_policy(request, pk):
    policy = Policy.objects.get(id=pk)
    policy.delete()
    messages.info(request, "Policy deleted successfully!", extra_tags="bg-danger")
    return HttpResponseRedirect(reverse("policy_list"))


# =================================== Validate Policy  ===================================
@login_required
@admin_required
@transaction.atomic
def validate_policy(request, policy_id):
    policy = get_object_or_404(Policy, id=policy_id)

    if request.method == "POST":
        if not policy.is_valid:
            policy.is_valid = True
            policy.save()

            messages.success(
                request, "Policy validated successfully!", extra_tags="bg-success"
            )
            return HttpResponseRedirect(reverse("policy_list"))

    return HttpResponseBadRequest("Invalid request")


# =================================== Read Policy  ===================================


@login_required
@admin_or_manager_or_staff_required
@transaction.atomic
def read_policy(request, policy_id):
    policy = get_object_or_404(Policy, id=policy_id)

    if request.method == "POST":
        _, created = PolicyRead.objects.get_or_create(user=request.user, policy=policy)

        if created:
            messages.success(
                request, "Policy marked as read successfully!", extra_tags="bg-success"
            )
        else:
            messages.info(
                request, "You have already read this policy.", extra_tags="bg-danger"
            )

    return HttpResponseRedirect(reverse("policy_list"))


# =================================== Policy Report ===================================
@login_required
@admin_or_manager_required
def policy_report(request):
    if request.method == "POST":
        policy_id = request.POST.get("id")
        if policy_id:
            selected_policy = get_object_or_404(Policy, id=policy_id)
            policy_read = PolicyRead.objects.filter(policy_id=policy_id)
            policies = Policy.objects.all().order_by("id")
            return render(
                request,
                "accounts/policy_rpt.html",
                {
                    "table_title": "policies read",
                    "policies": policies,
                    "policy_name": selected_policy.title,
                    "policy_upload": selected_policy.upload,
                    "policy_read": policy_read,
                },
            )
        else:
            messages.error(request, "No policy selected.", extra_tags="bg-danger")
    else:
        policies = Policy.objects.all().order_by("id")
    return render(
        request,
        "accounts/policy_rpt.html",
        {"table_title": "policies read", "policies": policies},
    )


# =================================== Uplaod ebook  ===================================
@login_required
@admin_or_manager_required
@transaction.atomic
def upload_ebook(request):
    if request.method == "POST":
        form = EbookForm(request.POST, request.FILES)

        if form.is_valid():
            form.save()
            messages.success(
                request, "Record saved successfully!", extra_tags="bg-success"
            )
            return redirect("ebook_list")
        else:
            # Display an error message if the form is not valid
            messages.error(
                request,
                "There was an error saving the record. Please check the form for errors.",
                extra_tags="bg-danger",
            )

    else:
        form = EbookForm()

    return render(
        request,
        "accounts/ebook_upload.html",
        {"form_name": "UPLOAD BOOK", "form": form},
    )


# ===================================  Books list  ===================================
@login_required
@admin_or_manager_or_staff_required
def ebook_list(request):
    queryset = Ebook.objects.all().order_by("id")

    search_query = request.GET.get("search")
    if search_query:
        queryset = queryset.filter(title__icontains=search_query)

    paginator = Paginator(queryset, 50)
    page = request.GET.get("page")

    try:
        records = paginator.page(page)
    except PageNotAnInteger:
        records = paginator.page(1)
    except EmptyPage:
        records = paginator.page(paginator.num_pages)

    # Add file existence information to each record
    for record in records:
        file_path = record.ebook_file.name
        record.file_exists = default_storage.exists(file_path)

    return render(
        request,
        "accounts/ebook_list.html",
        {"records": records, "table_title": "Books List"},
    )


# =================================== Update Book ===================================
@login_required
@admin_or_manager_required
@transaction.atomic
def update_ebook(request, pk, template_name="accounts/ebook_upload.html"):
    # Retrieve the ebook record by primary key, or return a 404 error if not found
    client_record = get_object_or_404(Ebook, pk=pk)

    if request.method == "POST":
        # Bind the form to the request data and files, including the instance to update
        form = EbookForm(request.POST, request.FILES, instance=client_record)
        if form.is_valid():
            # Save the updated record
            form.save()

            # Add a success message and redirect to the ebook list
            messages.success(
                request, "Client record updated successfully!", extra_tags="bg-success"
            )
            return redirect("ebook_list")  # Adjust the redirect as needed
    else:
        # Pre-populate the form with existing data
        form = EbookForm(instance=client_record)

    # Render the form in the template
    context = {"form_name": "Update Book", "form": form}
    return render(request, template_name, context)


# =================================== Delete Book ===================================
@login_required
@admin_or_manager_required
@transaction.atomic
def delete_ebook(request, pk):
    ebook = Ebook.objects.get(id=pk)
    ebook.delete()
    messages.info(request, "Book deleted successfully!", extra_tags="bg-danger")
    return HttpResponseRedirect(reverse("ebook_list"))


# ===================================  Contact Us  ===================================
@transaction.atomic
def contact_us(request):
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            instance = form.save()

            try:
                # Send email to the user
                subject = "Your message has been received"
                message = f"Hello {instance.name},\n\nYour message has been received. \
We will get back to you soon!\n\nThanks,\nPerpetual - SDMS\nManagement"
                from_email = (
                    settings.EMAIL_HOST_USER
                )  # Use default from email from settings
                to = [instance.email]  # Access email entered in the form
                send_mail(subject, message, from_email, to)

                # Set success message
                messages.success(
                    request,
                    "Your message has been sent successfully. \
We will get back to you soon!",
                    extra_tags="bg-success",
                )
            except Exception as e:
                # Handle exceptions such as email address not found or internet being off
                print("An error occurred while sending email:", str(e))
                messages.error(
                    request,
                    "Sorry, an error occurred while sending your \
message. Please try again later.",
                    extra_tags="bg-danger",
                )

            # Redirect to the contact page
            return HttpResponseRedirect(reverse("contact_us"))
    else:
        form = ContactForm()

    return render(request, "accounts/contact_us.html", {"form": form})


# =================================== Display User Feedback ===================================
@login_required
@admin_or_manager_required
@transaction.atomic
def user_feedback(request):
    feedback = Contact.objects.all()
    return render(
        request,
        "accounts/user_feedback.html",
        {"table_title": "User Feedback", "feedback": feedback},
    )


# =================================== Delete User Feedback ===================================
@login_required
@admin_or_manager_required
@transaction.atomic
def delete_feedback(request, pk):
    feedback = Contact.objects.get(id=pk)
    feedback.delete()
    messages.info(request, "Record deleted!", extra_tags="bg-danger")
    return HttpResponseRedirect(reverse("user_feedback"))


# =================================== Validate User Feedback  ===================================
@login_required
@admin_or_manager_required
@transaction.atomic
def validate_user_feedback(request, contact_id):
    user_feedback = get_object_or_404(Contact, id=contact_id)

    if request.method == "POST":
        if not user_feedback.is_valid:
            user_feedback.is_valid = True
            user_feedback.save()

            messages.success(
                request, "User validated successfully!", extra_tags="bg-success"
            )
            return HttpResponseRedirect(reverse("user_feedback"))

    return HttpResponseBadRequest("Invalid request")


# ===================================  Documents list  ===================================
@login_required
@admin_or_manager_or_staff_required
def doc_list(request):
    queryset = DocumentUpload.objects.all().order_by("id")

    search_query = request.GET.get("search")
    if search_query:
        queryset = queryset.filter(title__icontains=search_query)

    paginator = Paginator(queryset, 50)
    page_number = request.GET.get("page", 1)

    try:
        records = paginator.page(page_number)
    except PageNotAnInteger:
        records = paginator.page(1)
    except EmptyPage:
        records = paginator.page(paginator.num_pages)

    # Add file existence information to each record
    for record in records:
        file_path = (
            record.file.name
        )  # Ensure 'file' is used if 'file' is the correct field
        record.file_exists = default_storage.exists(file_path)

    return render(
        request,
        "accounts/default_upload_list.html",
        {"records": records, "table_title": "Documents List"},
    )


# =================================== Uplaod Document  ===================================
@login_required
@admin_or_manager_required
@transaction.atomic
def upload_doc(request):
    if request.method == "POST":
        form = DocumentForm(request.POST, request.FILES)

        if form.is_valid():
            form.save()
            messages.success(
                request, "Record saved successfully!", extra_tags="bg-success"
            )
            return redirect("doc_list")
        else:
            # Display an error message if the form is not valid
            messages.error(
                request,
                "There was an error saving the record. Please check the form for errors.",
                extra_tags="bg-danger",
            )

    else:
        form = DocumentForm()

    return render(
        request,
        "accounts/default_upload.html",
        {"form_name": "UPLOAD DOCUMENT", "form": form},
    )


# =================================== Update Documents ===================================
@login_required
@admin_or_manager_required
@transaction.atomic
def update_doc(request, pk, template_name="accounts/default_upload.html"):
    # Retrieve the doc record by primary key, or return a 404 error if not found
    record = get_object_or_404(DocumentUpload, pk=pk)

    if request.method == "POST":
        # Bind the form to the request data and files, including the instance to update
        form = DocumentForm(request.POST, request.FILES, instance=record)
        if form.is_valid():
            # Save the updated record
            form.save()

            # Add a success message and redirect to the doc list
            messages.success(
                request, "Record updated successfully!", extra_tags="bg-success"
            )
            return redirect("doc_list")  # Adjust the redirect as needed
    else:
        # Pre-populate the form with existing data
        form = DocumentForm(instance=record)

    # Render the form in the template
    context = {"form_name": "Update Documents", "form": form}
    return render(request, template_name, context)


# =================================== Delete Document ===================================
@login_required
@admin_or_manager_required
@transaction.atomic
def delete_doc(request, pk):
    doc = DocumentUpload.objects.get(id=pk)
    doc.delete()
    messages.info(request, "Document deleted successfully!", extra_tags="bg-danger")
    return HttpResponseRedirect(reverse("doc_list"))
