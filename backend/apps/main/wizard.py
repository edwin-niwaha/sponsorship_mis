# def show_education_form(wizard):
#     cleaned_data = wizard.get_cleaned_data_for_step('0') or {}
#     return cleaned_data.get('is_child_in_school')

# @method_decorator(login_required, name='dispatch')
# class ChildWizardView(SessionWizardView):
#     template_name = "main/child/manage_child_wizard.html"
#     # form_list = [ChildDetailForm, EducatonDetailForm, Step3Form, Step4Form, 
#       Step5Form, Step6Form, Step7Form, Step8Form]
#     form_list = [ChildDetailForm, EducationDetailForm, Step3Form]

#     condition_dict = {"1": show_education_form}

#     def done(self, form_list, **kwargs):
#         print(form_list)
#         child_form = form_list[0]
#         if child_form.cleaned_data.get('is_child_in_school'):
#             education = form_list[1].save()
#             child_details = child_form.save(commit=False)
#             child_details.education = education
#             child_details.save()
#         else:
#             child_details = child_form.save()

#         form3 = form_list[-1].save(commit=False)
#         form3.child_details = child_details
#         form3.save()

#         # return HttpResponseRedirect(reverse("register_child"))
#         return HttpResponse("Form Submtted!")
