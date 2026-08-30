from __future__ import annotations

from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.application.finance import finance_service
from app.infrastructure.database.models import (
    AcademyClassModel,
    FinancialTransactionModel,
    UserModel,
)
from app.interface.web.decorators import role_required

finance_bp = Blueprint("finance", __name__, url_prefix="/finance")


# ---------------------------------------------------------------------------
# Admin routes
# ---------------------------------------------------------------------------


@finance_bp.route("/admin/dashboard")
@login_required
@role_required("ADMIN")
def admin_dashboard():
    """Admin financial dashboard."""
    summary = finance_service.get_dashboard_summary()
    return render_template("finance/admin_dashboard.html", summary=summary)


@finance_bp.route("/admin/transactions")
@login_required
@role_required("ADMIN")
def admin_transactions():
    """List financial transactions with filters."""
    student_id = request.args.get("student_id", type=int)
    class_id = request.args.get("class_id", type=int)
    category = request.args.get("category", "")
    tx_type = request.args.get("transaction_type", "")
    payment_method = request.args.get("payment_method", "")
    start_date_str = request.args.get("start_date", "")
    end_date_str = request.args.get("end_date", "")
    page = request.args.get("page", 1, type=int)
    per_page = 20

    start_date = None
    end_date = None
    if start_date_str:
        try:
            start_date = date.fromisoformat(start_date_str)
        except ValueError:
            pass
    if end_date_str:
        try:
            end_date = date.fromisoformat(end_date_str)
        except ValueError:
            pass

    transactions = finance_service.get_transaction_report(
        student_user_id=student_id,
        class_id=class_id,
        category=category or None,
        transaction_type=tx_type or None,
        payment_method=payment_method or None,
        start_date=start_date,
        end_date=end_date,
        limit=per_page,
        offset=(page - 1) * per_page,
    )

    students = (
        UserModel.query.filter(UserModel.roles.any(name="STUDENT"))
        .order_by(UserModel.login)
        .all()
    )
    classes = AcademyClassModel.query.order_by(AcademyClassModel.title).all()

    return render_template(
        "finance/admin_transactions.html",
        transactions=transactions,
        students=students,
        classes=classes,
        filters={
            "student_id": student_id,
            "class_id": class_id,
            "category": category,
            "transaction_type": tx_type,
            "payment_method": payment_method,
            "start_date": start_date_str,
            "end_date": end_date_str,
        },
        page=page,
    )


@finance_bp.route("/admin/transaction/<int:transaction_id>")
@login_required
@role_required("ADMIN")
def admin_transaction_detail(transaction_id):
    """View transaction detail."""
    transaction = FinancialTransactionModel.query.get_or_404(transaction_id)
    return render_template(
        "finance/admin_transaction_detail.html", transaction=transaction
    )


@finance_bp.route("/admin/transaction/create", methods=["GET", "POST"])
@login_required
@role_required("ADMIN")
def admin_create_transaction():
    """Create a manual financial transaction."""
    if request.method == "POST":
        try:
            student_user_id = request.form.get("student_user_id", type=int)
            amount = request.form.get("amount", type=float)
            tx_type = request.form.get("transaction_type", "")
            category = request.form.get("category", "")
            payment_method = request.form.get("payment_method", "")
            description = request.form.get("description", "")
            reference_number = request.form.get("reference_number", "")
            class_id = request.form.get("class_id", type=int)

            if tx_type == "PAYMENT":
                finance_service.record_payment(
                    student_user_id=student_user_id,
                    amount=amount,
                    payment_method=payment_method or "CASH",
                    description=description,
                    reference_number=reference_number,
                    class_id=class_id,
                    created_by=current_user.id,
                )
            elif tx_type == "CHARGE":
                finance_service.create_charge(
                    student_user_id=student_user_id,
                    amount=amount,
                    category=category,
                    description=description,
                    reference_number=reference_number,
                    class_id=class_id,
                    created_by=current_user.id,
                )
            elif tx_type == "REFUND":
                finance_service.record_refund(
                    student_user_id=student_user_id,
                    amount=amount,
                    description=description,
                    reference_number=reference_number,
                    class_id=class_id,
                    created_by=current_user.id,
                )
            elif tx_type == "DISCOUNT":
                finance_service.apply_discount(
                    student_user_id=student_user_id,
                    amount=amount,
                    category=category,
                    description=description,
                    class_id=class_id,
                    created_by=current_user.id,
                )
            elif tx_type == "ADJUSTMENT":
                finance_service.create_adjustment(
                    student_user_id=student_user_id,
                    amount=amount,
                    category=category,
                    description=description,
                    reference_number=reference_number,
                    created_by=current_user.id,
                )

            flash("تراکنش با موفقیت ثبت شد.", "success")
            return redirect(url_for("finance.admin_transactions"))
        except finance_service.FinanceError as e:
            flash(str(e), "error")

    students = (
        UserModel.query.filter(UserModel.roles.any(name="STUDENT"))
        .order_by(UserModel.login)
        .all()
    )
    classes = AcademyClassModel.query.order_by(AcademyClassModel.title).all()

    return render_template(
        "finance/admin_create_transaction.html",
        students=students,
        classes=classes,
    )


@finance_bp.route("/admin/transaction/<int:transaction_id>/correct", methods=["POST"])
@login_required
@role_required("ADMIN")
def admin_correct_transaction(transaction_id):
    """Correct a transaction."""
    try:
        new_amount = request.form.get("new_amount", type=float)
        new_description = request.form.get("new_description", "")
        finance_service.correct_transaction(
            transaction_id,
            new_amount=new_amount,
            new_description=new_description,
            corrected_by=current_user.id,
        )
        flash("تراکنش اصلاح شد.", "success")
    except finance_service.FinanceError as e:
        flash(str(e), "error")

    return redirect(
        url_for("finance.admin_transaction_detail", transaction_id=transaction_id)
    )


@finance_bp.route("/admin/transaction/<int:transaction_id>/reverse", methods=["POST"])
@login_required
@role_required("ADMIN")
def admin_reverse_transaction(transaction_id):
    """Reverse a transaction."""
    try:
        description = request.form.get("description", "")
        finance_service.reverse_transaction(
            transaction_id,
            description=description,
            reversed_by=current_user.id,
        )
        flash("تراکنش معکوس شد.", "success")
    except finance_service.FinanceError as e:
        flash(str(e), "error")

    return redirect(url_for("finance.admin_transactions"))


@finance_bp.route("/admin/student/<int:student_user_id>/statement")
@login_required
@role_required("ADMIN")
def admin_student_statement(student_user_id):
    """View student account statement."""
    student = UserModel.query.get_or_404(student_user_id)
    balance = finance_service.get_student_balance(student_user_id)
    transactions = finance_service.get_student_statement(student_user_id)
    return render_template(
        "finance/admin_student_statement.html",
        student=student,
        balance=balance,
        transactions=transactions,
    )


@finance_bp.route("/admin/class/<int:class_id>/financial")
@login_required
@role_required("ADMIN")
def admin_class_financial(class_id):
    """View class financial summary."""
    academy_class = AcademyClassModel.query.get_or_404(class_id)
    summary = finance_service.get_class_financial_summary(class_id)
    return render_template(
        "finance/admin_class_financial.html",
        academy_class=academy_class,
        summary=summary,
    )


@finance_bp.route("/admin/reports/debt")
@login_required
@role_required("ADMIN")
def admin_debt_report():
    """View debt report."""
    report = finance_service.get_debt_report()
    students = {
        s.id: s
        for s in UserModel.query.filter(UserModel.roles.any(name="STUDENT")).all()
    }
    return render_template(
        "finance/admin_debt_report.html",
        report=report,
        students=students,
    )


@finance_bp.route("/admin/reports/credit")
@login_required
@role_required("ADMIN")
def admin_credit_report():
    """View credit report."""
    report = finance_service.get_credit_report()
    students = {
        s.id: s
        for s in UserModel.query.filter(UserModel.roles.any(name="STUDENT")).all()
    }
    return render_template(
        "finance/admin_credit_report.html",
        report=report,
        students=students,
    )


@finance_bp.route("/admin/reports/revenue")
@login_required
@role_required("ADMIN")
def admin_revenue_report():
    """View revenue report."""
    start_date_str = request.args.get("start_date", "")
    end_date_str = request.args.get("end_date", "")

    start_date = None
    end_date = None
    if start_date_str:
        try:
            start_date = date.fromisoformat(start_date_str)
        except ValueError:
            pass
    if end_date_str:
        try:
            end_date = date.fromisoformat(end_date_str)
        except ValueError:
            pass

    report = finance_service.get_revenue_report(
        start_date=start_date, end_date=end_date
    )
    return render_template(
        "finance/admin_revenue_report.html",
        report=report,
        start_date=start_date_str,
        end_date=end_date_str,
    )


# ---------------------------------------------------------------------------
# Parent routes
# ---------------------------------------------------------------------------


@finance_bp.route("/parent/overview")
@login_required
@role_required("PARENT")
def parent_overview():
    """Parent view of children's financial overview."""
    from app.infrastructure.database.models import ParentProfileModel

    parent_profile = ParentProfileModel.query.filter_by(user_id=current_user.id).first()
    if parent_profile is None:
        flash("پروفایل والد یافت نشد.", "error")
        return redirect(url_for("auth.dashboard"))

    children_data = []
    for child in parent_profile.children:
        user = UserModel.query.get(child.user_id)
        if user is None:
            continue
        balance = finance_service.get_student_balance(child.user_id)
        children_data.append(
            {
                "user": user,
                "profile": child,
                "balance": balance,
            }
        )

    return render_template("finance/parent_overview.html", children_data=children_data)


@finance_bp.route("/parent/child/<int:child_user_id>/statement")
@login_required
@role_required("PARENT")
def parent_child_statement(child_user_id):
    """Parent view of a specific child's financial statement."""
    from app.infrastructure.database.models import ParentProfileModel

    # Verify parent is linked to this child
    parent_profile = ParentProfileModel.query.filter_by(user_id=current_user.id).first()
    if parent_profile is None:
        flash("پروفایل والد یافت نشد.", "error")
        return redirect(url_for("auth.dashboard"))

    child_ids = [c.user_id for c in parent_profile.children]
    if child_user_id not in child_ids:
        flash("شما به اطلاعات مالی این دانش‌آموز دسترسی ندارید.", "error")
        return redirect(url_for("finance.parent_overview"))

    student = UserModel.query.get_or_404(child_user_id)
    balance = finance_service.get_student_balance(child_user_id)
    transactions = finance_service.get_student_statement(child_user_id)

    return render_template(
        "finance/parent_child_statement.html",
        student=student,
        balance=balance,
        transactions=transactions,
    )


# ---------------------------------------------------------------------------
# Student routes (18+ only)
# ---------------------------------------------------------------------------


@finance_bp.route("/student/my-finance")
@login_required
@role_required("STUDENT")
def student_my_finance():
    """Student financial view (18+ only)."""
    from datetime import date as date_type

    from app.infrastructure.database.models import StudentProfileModel

    profile = StudentProfileModel.query.filter_by(user_id=current_user.id).first()
    if profile is None:
        flash("پروفایل دانش‌آموزی یافت نشد.", "error")
        return redirect(url_for("auth.dashboard"))

    today = date_type.today()
    age = (
        today.year
        - profile.birth_date.year
        - (
            (today.month, today.day)
            < (profile.birth_date.month, profile.birth_date.day)
        )
    )

    if age < 18:
        flash("شما به اطلاعات مالی دسترسی ندارید (سن زیر ۱۸ سال).", "error")
        return redirect(url_for("auth.dashboard"))

    balance = finance_service.get_student_balance(current_user.id)
    transactions = finance_service.get_student_statement(current_user.id)

    return render_template(
        "finance/student_my_finance.html",
        balance=balance,
        transactions=transactions,
    )
