from django.contrib import admin

from .models import (
    ChildPayments,
    DonorPayment,
    StaffPayments,
)


admin.site.register(ChildPayments)
admin.site.register(DonorPayment)
admin.site.register(StaffPayments)
