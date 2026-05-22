from django.contrib import admin

from .models import (
    ChartOfAccounts,
    Loan,
    LoanApplicationDocument,
    LoanDisbursement,
    LoanPenalty,
    LoanRepayment,
    TransactionHistory,
)


class LoanRepaymentInline(admin.TabularInline):
    model = LoanRepayment
    extra = 0
    fields = ("repayment_date", "principal_payment", "interest_payment", "penalty_payment", "account")
    readonly_fields = fields
    can_delete = False


class LoanDisbursementInline(admin.TabularInline):
    model = LoanDisbursement
    extra = 0
    fields = ("account", "payment_method", "disbursed_amount", "interest_amount")
    readonly_fields = fields
    can_delete = False


class LoanApplicationDocumentInline(admin.TabularInline):
    model = LoanApplicationDocument
    extra = 0
    fields = ("document_type", "file", "description", "uploaded_by", "created_at")
    readonly_fields = ("created_at",)


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "borrower",
        "principal_amount",
        "total_interest",
        "status",
        "start_date",
        "disbursement_date",
        "due_date",
        "approved_date",
    )
    list_filter = ("status", "loan_purpose", "start_date", "disbursement_date", "due_date")
    search_fields = ("id", "borrower__full_name", "borrower__reg_number")
    readonly_fields = (
        "total_interest",
        "due_date",
        "created_at",
        "updated_at",
        "last_reminder_sent",
    )
    date_hierarchy = "start_date"
    inlines = (LoanApplicationDocumentInline, LoanDisbursementInline, LoanRepaymentInline)


@admin.register(LoanApplicationDocument)
class LoanApplicationDocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "loan", "document_type", "uploaded_by", "created_at")
    list_filter = ("document_type", "created_at")
    search_fields = (
        "loan__id",
        "loan__borrower__full_name",
        "loan__borrower__reg_number",
        "uploaded_by__username",
        "description",
    )
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "created_at"


@admin.register(LoanRepayment)
class LoanRepaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "loan", "repayment_date", "principal_payment", "interest_payment", "penalty_payment", "account")
    list_filter = ("repayment_date", "account")
    search_fields = ("loan__id", "loan__borrower__full_name", "loan__borrower__reg_number")
    date_hierarchy = "repayment_date"


@admin.register(LoanDisbursement)
class LoanDisbursementAdmin(admin.ModelAdmin):
    list_display = ("id", "loan", "account", "payment_method", "disbursed_amount", "interest_amount")
    list_filter = ("payment_method", "account")
    search_fields = ("loan__id", "loan__borrower__full_name", "loan__borrower__reg_number")


@admin.register(LoanPenalty)
class LoanPenaltyAdmin(admin.ModelAdmin):
    list_display = ("id", "loan", "penalty_date", "penalty_amount", "remaining_amount", "is_paid", "is_deleted")
    list_filter = ("is_paid", "is_deleted", "penalty_date", "account")
    search_fields = ("loan__id", "loan__borrower__full_name", "reason")
    readonly_fields = ("created_at", "updated_at", "deleted_at")
    date_hierarchy = "penalty_date"


@admin.register(ChartOfAccounts)
class ChartOfAccountsAdmin(admin.ModelAdmin):
    list_display = ("account_number", "account_name", "account_type")
    list_filter = ("account_type",)
    search_fields = ("account_number", "account_name")


@admin.register(TransactionHistory)
class TransactionHistoryAdmin(admin.ModelAdmin):
    list_display = ("id", "loan", "transaction_date", "account", "transaction_type", "amount")
    list_filter = ("transaction_type", "transaction_date", "account")
    search_fields = ("loan__id", "loan__borrower__full_name", "description")
    readonly_fields = ("loan", "transaction_date", "account", "transaction_type", "amount", "description")
    date_hierarchy = "transaction_date"
