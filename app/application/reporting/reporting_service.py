"""Reporting and Analytics Service.

Provides centralized reporting across all modules.
Uses database-level aggregation where appropriate.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import case, func

from app.extensions import db
from app.infrastructure.database.models import (
    AcademyClassModel,
    ActivityModel,
    ActivitySubmissionModel,
    AssessmentModel,
    AssessmentResultModel,
    AttendanceModel,
    CourseModel,
    EnrollmentModel,
    FinancialTransactionModel,
    NotificationDeliveryModel,
    NotificationModel,
    SessionModel,
    StudentProfileModel,
    UserModel,
)


class ReportingService:
    """Centralized reporting service for academy analytics."""

    @staticmethod
    def get_admin_overview() -> dict:
        """Get comprehensive admin dashboard overview."""
        session = db.session

        # Students
        total_students = (
            session.query(func.count(UserModel.id))
            .filter(UserModel.roles.any(name="STUDENT"))
            .scalar()
            or 0
        )

        active_students = (
            session.query(func.count(EnrollmentModel.student_user_id.distinct()))
            .filter(EnrollmentModel.status == "APPROVED")
            .scalar()
            or 0
        )

        # Teachers
        total_teachers = (
            session.query(func.count(UserModel.id))
            .filter(UserModel.roles.any(name="TEACHER"))
            .scalar()
            or 0
        )

        # Classes
        total_classes = session.query(func.count(AcademyClassModel.id)).scalar() or 0
        active_classes = (
            session.query(func.count(AcademyClassModel.id))
            .filter(AcademyClassModel.status == "ACTIVE")
            .scalar()
            or 0
        )

        # Sessions
        today = date.today()
        total_sessions = session.query(func.count(SessionModel.id)).scalar() or 0
        upcoming_sessions = (
            session.query(func.count(SessionModel.id))
            .filter(
                SessionModel.scheduled_date >= today, SessionModel.status == "SCHEDULED"
            )
            .scalar()
            or 0
        )

        # Enrollments
        total_enrollments = session.query(func.count(EnrollmentModel.id)).scalar() or 0
        pending_enrollments = (
            session.query(func.count(EnrollmentModel.id))
            .filter(EnrollmentModel.status == "PENDING")
            .scalar()
            or 0
        )

        # Assessments
        total_assessments = session.query(func.count(AssessmentModel.id)).scalar() or 0
        graded_assessments = (
            session.query(func.count(AssessmentModel.id))
            .filter(AssessmentModel.status == "GRADED")
            .scalar()
            or 0
        )

        # Finance
        total_revenue = session.query(
            func.coalesce(func.sum(FinancialTransactionModel.amount), 0)
        ).filter(
            FinancialTransactionModel.transaction_type == "PAYMENT",
            FinancialTransactionModel.status == "ACTIVE",
        ).scalar() or Decimal("0")

        total_debt = session.query(
            func.coalesce(func.sum(FinancialTransactionModel.amount), 0)
        ).filter(
            FinancialTransactionModel.transaction_type == "CHARGE",
            FinancialTransactionModel.status == "ACTIVE",
        ).scalar() or Decimal("0")

        # Notifications
        total_notifications = (
            session.query(func.count(NotificationModel.id)).scalar() or 0
        )
        failed_notifications = (
            session.query(func.count(NotificationModel.id))
            .filter(NotificationModel.status == "FAILED")
            .scalar()
            or 0
        )

        # Attendance
        total_attendance = session.query(func.count(AttendanceModel.id)).scalar() or 0
        present_count = (
            session.query(func.count(AttendanceModel.id))
            .filter(AttendanceModel.status == "PRESENT")
            .scalar()
            or 0
        )

        attendance_percentage = (
            round(present_count / total_attendance * 100, 1)
            if total_attendance > 0
            else 0
        )

        return {
            "students": {
                "total": total_students,
                "active": active_students,
            },
            "teachers": {
                "total": total_teachers,
            },
            "classes": {
                "total": total_classes,
                "active": active_classes,
            },
            "sessions": {
                "total": total_sessions,
                "upcoming": upcoming_sessions,
            },
            "enrollments": {
                "total": total_enrollments,
                "pending": pending_enrollments,
            },
            "assessments": {
                "total": total_assessments,
                "graded": graded_assessments,
            },
            "finance": {
                # Gross figures (unscoped, un-netted): collected cash vs
                # billed charges. Named honestly — see net_revenue in the
                # finance reports for the reconciled figure.
                "gross_collected": Decimal(str(total_revenue)),
                "gross_billed": Decimal(str(total_debt)),
            },
            "notifications": {
                "total": total_notifications,
                "failed": failed_notifications,
            },
            "attendance": {
                "percentage": attendance_percentage,
                "total": total_attendance,
                "present": present_count,
            },
        }

    @staticmethod
    def get_student_report(student_user_id: int) -> dict:
        """Get comprehensive report for an individual student."""
        session = db.session

        # Profile
        student = session.get(UserModel, student_user_id)
        if not student:
            return {"error": "Student not found"}

        profile = (
            session.query(StudentProfileModel)
            .filter_by(user_id=student_user_id)
            .first()
        )

        # Enrollments
        enrollments = (
            session.query(EnrollmentModel)
            .filter_by(student_user_id=student_user_id)
            .all()
        )

        enrollment_stats = {
            "total": len(enrollments),
            "approved": sum(1 for e in enrollments if e.status == "APPROVED"),
            "pending": sum(1 for e in enrollments if e.status == "PENDING"),
            "cancelled": sum(1 for e in enrollments if e.status == "CANCELLED"),
        }

        # Classes
        approved_enrollment_class_ids = [
            e.class_id for e in enrollments if e.status == "APPROVED"
        ]

        current_classes = (
            session.query(AcademyClassModel)
            .filter(
                AcademyClassModel.id.in_(approved_enrollment_class_ids),
                AcademyClassModel.status == "ACTIVE",
            )
            .all()
            if approved_enrollment_class_ids
            else []
        )

        # Attendance
        attendance_records = (
            session.query(AttendanceModel)
            .join(EnrollmentModel, AttendanceModel.enrollment_id == EnrollmentModel.id)
            .filter(EnrollmentModel.student_user_id == student_user_id)
            .all()
        )

        attendance_stats = {
            "total": len(attendance_records),
            "present": sum(1 for a in attendance_records if a.status == "PRESENT"),
            "absent": sum(1 for a in attendance_records if a.status == "ABSENT"),
            "late": sum(1 for a in attendance_records if a.status == "LATE"),
            "excused": sum(1 for a in attendance_records if a.status == "EXCUSED"),
        }

        attendance_stats["percentage"] = (
            round(attendance_stats["present"] / attendance_stats["total"] * 100, 1)
            if attendance_stats["total"] > 0
            else 0
        )

        # Activities/Submissions
        submissions = (
            session.query(ActivitySubmissionModel)
            .filter_by(student_user_id=student_user_id)
            .all()
        )

        activity_stats = {
            "total_submitted": len(submissions),
            "graded": sum(1 for s in submissions if s.status == "GRADED"),
            "pending": sum(1 for s in submissions if s.status == "SUBMITTED"),
            "late": sum(1 for s in submissions if s.status == "LATE"),
        }

        # Assessments
        assessment_results = (
            session.query(AssessmentResultModel)
            .filter_by(student_user_id=student_user_id)
            .all()
        )

        assessment_stats = {
            "total": len(assessment_results),
            "passed": sum(1 for r in assessment_results if r.pass_fail == "PASS"),
            "failed": sum(1 for r in assessment_results if r.pass_fail == "FAIL"),
            "absent": sum(
                1 for r in assessment_results if r.presence_status == "ABSENT"
            ),
        }

        scores = [float(r.score) for r in assessment_results if r.score is not None]
        assessment_stats["average_score"] = (
            round(sum(scores) / len(scores), 1) if scores else 0
        )
        assessment_stats["pass_rate"] = (
            round(assessment_stats["passed"] / assessment_stats["total"] * 100, 1)
            if assessment_stats["total"] > 0
            else 0
        )

        # Finance
        transactions = (
            session.query(FinancialTransactionModel)
            .filter_by(student_user_id=student_user_id, status="ACTIVE")
            .all()
        )

        finance_stats = {
            "total_payments": sum(
                (t.amount for t in transactions if t.transaction_type == "PAYMENT"),
                Decimal("0"),
            ),
            "total_charges": sum(
                (t.amount for t in transactions if t.transaction_type == "CHARGE"),
                Decimal("0"),
            ),
            "total_discounts": sum(
                (t.amount for t in transactions if t.transaction_type == "DISCOUNT"),
                Decimal("0"),
            ),
            "total_refunds": sum(
                (t.amount for t in transactions if t.transaction_type == "REFUND"),
                Decimal("0"),
            ),
        }

        # Canonical balance (same formula as the ledger): includes signed
        # ADJUSTMENT/REVERSAL rows, which the per-type buckets above omit.
        from app.application.finance import finance_service as _finance_service

        finance_stats["balance"] = _finance_service.get_student_balance(
            student_user_id
        )

        return {
            "student": student,
            "profile": profile,
            "enrollments": enrollment_stats,
            "current_classes": current_classes,
            "attendance": attendance_stats,
            "activities": activity_stats,
            "assessments": assessment_stats,
            "finance": finance_stats,
        }

    @staticmethod
    def get_class_report(class_id: int) -> dict:
        """Get comprehensive report for a class."""
        session = db.session

        class_obj = session.get(AcademyClassModel, class_id)
        if not class_obj:
            return {"error": "Class not found"}

        # Enrollment stats
        enrollments = session.query(EnrollmentModel).filter_by(class_id=class_id).all()
        enrollment_stats = {
            "total": len(enrollments),
            "approved": sum(1 for e in enrollments if e.status == "APPROVED"),
            "pending": sum(1 for e in enrollments if e.status == "PENDING"),
            "cancelled": sum(1 for e in enrollments if e.status == "CANCELLED"),
        }

        # Sessions
        sessions = session.query(SessionModel).filter_by(class_id=class_id).all()
        session_stats = {
            "total": len(sessions),
            "completed": sum(1 for s in sessions if s.status == "COMPLETED"),
            "scheduled": sum(1 for s in sessions if s.status == "SCHEDULED"),
            "cancelled": sum(1 for s in sessions if s.status == "CANCELLED"),
        }

        # Attendance
        enrollment_ids = [e.id for e in enrollments]
        if enrollment_ids:
            attendance_records = (
                session.query(AttendanceModel)
                .filter(AttendanceModel.enrollment_id.in_(enrollment_ids))
                .all()
            )
        else:
            attendance_records = []

        attendance_stats = {
            "total": len(attendance_records),
            "present": sum(1 for a in attendance_records if a.status == "PRESENT"),
            "absent": sum(1 for a in attendance_records if a.status == "ABSENT"),
            "late": sum(1 for a in attendance_records if a.status == "LATE"),
            "excused": sum(1 for a in attendance_records if a.status == "EXCUSED"),
        }

        attendance_stats["percentage"] = (
            round(attendance_stats["present"] / attendance_stats["total"] * 100, 1)
            if attendance_stats["total"] > 0
            else 0
        )

        # Activities
        activities = session.query(ActivityModel).filter_by(class_id=class_id).all()
        activity_stats = {
            "total": len(activities),
            "active": sum(1 for a in activities if a.is_active),
        }

        # Assessments
        assessments = session.query(AssessmentModel).filter_by(class_id=class_id).all()
        assessment_stats = {
            "total": len(assessments),
            "graded": sum(1 for a in assessments if a.status == "GRADED"),
        }

        # Finance
        finance_stats = {
            "total_tuition": float(class_obj.tuition) if class_obj.tuition else 0,
            "enrolled_count": enrollment_stats["approved"],
            "capacity": class_obj.capacity,
            "occupancy_rate": (
                round(enrollment_stats["approved"] / class_obj.capacity * 100, 1)
                if class_obj.capacity > 0
                else 0
            ),
        }

        # Teacher
        teacher = None
        if class_obj.teacher_user_id:
            teacher = session.get(UserModel, class_obj.teacher_user_id)

        return {
            "class": class_obj,
            "teacher": teacher,
            "enrollments": enrollment_stats,
            "sessions": session_stats,
            "attendance": attendance_stats,
            "activities": activity_stats,
            "assessments": assessment_stats,
            "finance": finance_stats,
        }

    @staticmethod
    def get_course_report(course_id: int) -> dict:
        """Get comprehensive report for a course."""
        session = db.session

        course = session.get(CourseModel, course_id)
        if not course:
            return {"error": "Course not found"}

        # Classes
        classes = session.query(AcademyClassModel).filter_by(course_id=course_id).all()
        class_stats = {
            "total": len(classes),
            "active": sum(1 for c in classes if c.status == "ACTIVE"),
            "completed": sum(1 for c in classes if c.status == "COMPLETED"),
            "cancelled": sum(1 for c in classes if c.status == "CANCELLED"),
        }

        # Enrollments across all classes
        class_ids = [c.id for c in classes]
        if class_ids:
            total_enrollments = (
                session.query(func.count(EnrollmentModel.id))
                .filter(EnrollmentModel.class_id.in_(class_ids))
                .scalar()
                or 0
            )

            active_enrollments = (
                session.query(func.count(EnrollmentModel.id))
                .filter(
                    EnrollmentModel.class_id.in_(class_ids),
                    EnrollmentModel.status == "APPROVED",
                )
                .scalar()
                or 0
            )
        else:
            total_enrollments = 0
            active_enrollments = 0

        # Activities
        if class_ids:
            activities = (
                session.query(ActivityModel)
                .filter(ActivityModel.class_id.in_(class_ids))
                .all()
            )
            activity_stats = {
                "total": len(activities),
                "active": sum(1 for a in activities if a.is_active),
            }
        else:
            activity_stats = {"total": 0, "active": 0}

        return {
            "course": course,
            "classes": class_stats,
            "enrollments": {
                "total": total_enrollments,
                "active": active_enrollments,
            },
            "activities": activity_stats,
        }

    @staticmethod
    def get_attendance_report(
        class_id: int | None = None,
        student_user_id: int | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict:
        """Get attendance report with optional filters."""
        session = db.session

        query = session.query(AttendanceModel)

        # Apply filters
        if class_id:
            enrollment_ids = [
                e.id
                for e in session.query(EnrollmentModel.id)
                .filter_by(class_id=class_id)
                .all()
            ]
            if enrollment_ids:
                query = query.filter(AttendanceModel.enrollment_id.in_(enrollment_ids))
            else:
                return {
                    "total": 0,
                    "present": 0,
                    "absent": 0,
                    "late": 0,
                    "excused": 0,
                    "percentage": 0,
                    "trend": [],
                }

        if student_user_id:
            enrollment_ids = [
                e.id
                for e in session.query(EnrollmentModel.id)
                .filter_by(student_user_id=student_user_id)
                .all()
            ]
            if enrollment_ids:
                query = query.filter(AttendanceModel.enrollment_id.in_(enrollment_ids))
            else:
                return {
                    "total": 0,
                    "present": 0,
                    "absent": 0,
                    "late": 0,
                    "excused": 0,
                    "percentage": 0,
                    "trend": [],
                }

        if start_date or end_date:
            query = query.join(
                SessionModel, AttendanceModel.session_id == SessionModel.id
            )

        if start_date:
            query = query.filter(SessionModel.scheduled_date >= start_date)

        if end_date:
            query = query.filter(SessionModel.scheduled_date <= end_date)

        records = query.all()

        stats = {
            "total": len(records),
            "present": sum(1 for r in records if r.status == "PRESENT"),
            "absent": sum(1 for r in records if r.status == "ABSENT"),
            "late": sum(1 for r in records if r.status == "LATE"),
            "excused": sum(1 for r in records if r.status == "EXCUSED"),
        }

        stats["percentage"] = (
            round(stats["present"] / stats["total"] * 100, 1)
            if stats["total"] > 0
            else 0
        )

        return stats

    @staticmethod
    def get_attendance_alerts(threshold: float = 70.0) -> list[dict]:
        """Get students with attendance below threshold."""
        session = db.session

        # Get all students with attendance
        students_with_attendance = (
            session.query(
                EnrollmentModel.student_user_id,
                func.count(AttendanceModel.id).label("total"),
                func.sum(case((AttendanceModel.status == "PRESENT", 1), else_=0)).label(
                    "present"
                ),
            )
            .join(AttendanceModel, AttendanceModel.enrollment_id == EnrollmentModel.id)
            .group_by(EnrollmentModel.student_user_id)
            .all()
        )

        alerts = []
        for student_id, total, present in students_with_attendance:
            if total and total > 0:
                percentage = round((present or 0) / total * 100, 1)
                if percentage < threshold:
                    student = session.get(UserModel, student_id)
                    if student:
                        alerts.append(
                            {
                                "student_id": student_id,
                                "student_name": f"{student.student_profile.first_name} {student.student_profile.last_name}"
                                if student.student_profile
                                else student.login,
                                "attendance_percentage": percentage,
                                "total_sessions": total,
                                "present_sessions": present or 0,
                            }
                        )

        return sorted(alerts, key=lambda x: x["attendance_percentage"])

    @staticmethod
    def get_assessment_report(assessment_id: int) -> dict:
        """Get comprehensive report for an assessment."""
        session = db.session

        assessment = session.get(AssessmentModel, assessment_id)
        if not assessment:
            return {"error": "Assessment not found"}

        # Get results
        results = (
            session.query(AssessmentResultModel)
            .filter_by(assessment_id=assessment_id)
            .all()
        )

        # Get eligible enrollments
        eligible_count = (
            session.query(func.count(EnrollmentModel.id))
            .filter(
                EnrollmentModel.class_id == assessment.class_id,
                EnrollmentModel.status == "APPROVED",
            )
            .scalar()
            or 0
        )

        scores = [float(r.score) for r in results if r.score is not None]

        stats = {
            "eligible": eligible_count,
            "submitted": len(results),
            "missing": eligible_count - len(results),
            "average": round(sum(scores) / len(scores), 1) if scores else 0,
            "min": min(scores) if scores else 0,
            "max": max(scores) if scores else 0,
            "passed": sum(1 for r in results if r.pass_fail == "PASS"),
            "failed": sum(1 for r in results if r.pass_fail == "FAIL"),
            "pass_rate": (
                round(
                    sum(1 for r in results if r.pass_fail == "PASS")
                    / len(results)
                    * 100,
                    1,
                )
                if results
                else 0
            ),
        }

        # Score distribution (buckets: 0-19, 20-39, 40-59, 60-79, 80-100)
        distribution = {
            "0-19": 0,
            "20-39": 0,
            "40-59": 0,
            "60-79": 0,
            "80-100": 0,
        }

        for score in scores:
            if score < 20:
                distribution["0-19"] += 1
            elif score < 40:
                distribution["20-39"] += 1
            elif score < 60:
                distribution["40-59"] += 1
            elif score < 80:
                distribution["60-79"] += 1
            else:
                distribution["80-100"] += 1

        stats["score_distribution"] = distribution

        return {
            "assessment": assessment,
            "stats": stats,
            "results": results,
        }

    @staticmethod
    def get_activity_report(class_id: int | None = None) -> dict:
        """Get activity/homework report."""
        session = db.session

        query = session.query(ActivityModel)
        if class_id:
            query = query.filter_by(class_id=class_id)

        activities = query.all()
        activity_ids = [a.id for a in activities]

        if not activity_ids:
            return {
                "total_activities": 0,
                "total_submissions": 0,
                "completion_rate": 0,
                "late_submissions": 0,
                "missing_submissions": 0,
            }

        # Get submissions
        submissions = (
            session.query(ActivitySubmissionModel)
            .filter(ActivitySubmissionModel.activity_id.in_(activity_ids))
            .all()
        )

        # Group by activity and get latest version per student
        activity_submissions: dict[int, dict] = {}
        for sub in submissions:
            key = (sub.activity_id, sub.student_user_id)
            if (
                key not in activity_submissions
                or sub.version > activity_submissions[key].version
            ):
                activity_submissions[key] = sub

        unique_submissions = list(activity_submissions.values())

        # Calculate expected submissions
        total_expected = 0
        for activity in activities:
            enrolled_count = (
                session.query(func.count(EnrollmentModel.id))
                .filter(
                    EnrollmentModel.class_id == activity.class_id,
                    EnrollmentModel.status == "APPROVED",
                )
                .scalar()
                or 0
                if activity.class_id
                else 0
            )
            total_expected += enrolled_count

        stats = {
            "total_activities": len(activities),
            "total_submissions": len(unique_submissions),
            "completion_rate": (
                round(len(unique_submissions) / total_expected * 100, 1)
                if total_expected > 0
                else 0
            ),
            "late_submissions": sum(
                1 for s in unique_submissions if s.status == "LATE"
            ),
            "graded_submissions": sum(
                1 for s in unique_submissions if s.status == "GRADED"
            ),
        }

        # Average grade
        graded_scores = [
            float(s.score) for s in unique_submissions if s.score is not None
        ]
        stats["average_grade"] = (
            round(sum(graded_scores) / len(graded_scores), 1) if graded_scores else 0
        )

        return stats

    @staticmethod
    def get_finance_report(
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict:
        """Get finance report with optional date filters."""
        session = db.session

        query = session.query(FinancialTransactionModel).filter(
            FinancialTransactionModel.status == "ACTIVE"
        )

        if start_date:
            query = query.filter(
                FinancialTransactionModel.created_at
                >= datetime.combine(start_date, datetime.min.time())
            )

        if end_date:
            query = query.filter(
                FinancialTransactionModel.created_at
                <= datetime.combine(end_date, datetime.max.time())
            )

        transactions = query.all()

        def _sum_type(tx_type: str) -> Decimal:
            return sum(
                (t.amount for t in transactions if t.transaction_type == tx_type),
                Decimal("0"),
            )

        def _signed_reversals() -> Decimal:
            # REVERSAL rows are stored signed; sum them directly.
            return sum(
                (t.amount for t in transactions if t.transaction_type == "REVERSAL"),
                Decimal("0"),
            )

        stats = {
            "total_payments": _sum_type("PAYMENT"),
            "total_charges": _sum_type("CHARGE"),
            "total_discounts": _sum_type("DISCOUNT"),
            "total_refunds": _sum_type("REFUND"),
        }

        # Canonical net collected cash: payments minus refunds plus signed
        # reversals. Discounts and charges are reported as separate lines,
        # not folded into cash collected. Matches the finance-service
        # revenue report definition.
        stats["net_revenue"] = (
            stats["total_payments"]
            - stats["total_refunds"]
            + _signed_reversals()
        )

        # Debt by student (using signed amounts: PAYMENT/DISCOUNT positive, CHARGE/REFUND negative)
        debt_query = (
            session.query(
                FinancialTransactionModel.student_user_id,
                func.sum(
                    case(
                        (
                            FinancialTransactionModel.transaction_type.in_(
                                ("PAYMENT", "DISCOUNT")
                            ),
                            FinancialTransactionModel.amount,
                        ),
                        (
                            FinancialTransactionModel.transaction_type.in_(
                                ("CHARGE", "REFUND")
                            ),
                            -FinancialTransactionModel.amount,
                        ),
                        else_=FinancialTransactionModel.amount,
                    )
                ).label("balance"),
            )
            .filter(FinancialTransactionModel.status == "ACTIVE")
            .group_by(FinancialTransactionModel.student_user_id)
            .having(
                func.sum(
                    case(
                        (
                            FinancialTransactionModel.transaction_type.in_(
                                ("PAYMENT", "DISCOUNT")
                            ),
                            FinancialTransactionModel.amount,
                        ),
                        (
                            FinancialTransactionModel.transaction_type.in_(
                                ("CHARGE", "REFUND")
                            ),
                            -FinancialTransactionModel.amount,
                        ),
                        else_=FinancialTransactionModel.amount,
                    )
                )
                < 0
            )
        )

        student_balances = []
        for student_id, balance in debt_query.all():
            if balance < 0:
                student = session.get(UserModel, student_id)
                if student:
                    student_balances.append(
                        {
                            "student_id": student_id,
                            "student_name": f"{student.student_profile.first_name} {student.student_profile.last_name}"
                            if student.student_profile
                            else student.login,
                            "balance": Decimal(str(balance)),
                        }
                    )

        stats["debt_by_student"] = sorted(student_balances, key=lambda x: x["balance"])

        return stats

    @staticmethod
    def get_enrollment_report(
        class_id: int | None = None,
        course_id: int | None = None,
    ) -> dict:
        """Get enrollment report with optional filters."""
        session = db.session

        query = session.query(EnrollmentModel)

        if class_id:
            query = query.filter_by(class_id=class_id)
        elif course_id:
            class_ids = [
                c.id
                for c in session.query(AcademyClassModel.id)
                .filter_by(course_id=course_id)
                .all()
            ]
            if class_ids:
                query = query.filter(EnrollmentModel.class_id.in_(class_ids))
            else:
                return {
                    "total": 0,
                    "pending": 0,
                    "approved": 0,
                    "rejected": 0,
                    "cancelled": 0,
                    "approval_rate": 0,
                }

        enrollments = query.all()

        stats = {
            "total": len(enrollments),
            "pending": sum(1 for e in enrollments if e.status == "PENDING"),
            "approved": sum(1 for e in enrollments if e.status == "APPROVED"),
            "rejected": sum(1 for e in enrollments if e.status == "REJECTED"),
            "cancelled": sum(1 for e in enrollments if e.status == "CANCELLED"),
        }

        decided = stats["approved"] + stats["rejected"]
        stats["approval_rate"] = (
            round(stats["approved"] / decided * 100, 1) if decided > 0 else 0
        )

        return stats

    @staticmethod
    def get_teacher_report(teacher_user_id: int) -> dict:
        """Get report for a teacher."""
        session = db.session

        teacher = session.get(UserModel, teacher_user_id)
        if not teacher:
            return {"error": "Teacher not found"}

        # Assigned classes
        classes = (
            session.query(AcademyClassModel)
            .filter_by(teacher_user_id=teacher_user_id)
            .all()
        )

        class_ids = [c.id for c in classes]

        # Students
        total_students = 0
        if class_ids:
            total_students = (
                session.query(func.count(EnrollmentModel.student_user_id.distinct()))
                .filter(
                    EnrollmentModel.class_id.in_(class_ids),
                    EnrollmentModel.status == "APPROVED",
                )
                .scalar()
                or 0
            )

        # Sessions
        total_sessions = 0
        completed_sessions = 0
        if class_ids:
            total_sessions = (
                session.query(func.count(SessionModel.id))
                .filter(SessionModel.class_id.in_(class_ids))
                .scalar()
                or 0
            )

            completed_sessions = (
                session.query(func.count(SessionModel.id))
                .filter(
                    SessionModel.class_id.in_(class_ids),
                    SessionModel.status == "COMPLETED",
                )
                .scalar()
                or 0
            )

        # Activities
        total_activities = 0
        if class_ids:
            total_activities = (
                session.query(func.count(ActivityModel.id))
                .filter(ActivityModel.class_id.in_(class_ids))
                .scalar()
                or 0
            )

        # Assessments
        total_assessments = 0
        if class_ids:
            total_assessments = (
                session.query(func.count(AssessmentModel.id))
                .filter(AssessmentModel.class_id.in_(class_ids))
                .scalar()
                or 0
            )

        return {
            "teacher": teacher,
            "classes": {
                "total": len(classes),
                "active": sum(1 for c in classes if c.status == "ACTIVE"),
            },
            "students": {
                "total": total_students,
            },
            "sessions": {
                "total": total_sessions,
                "completed": completed_sessions,
            },
            "activities": {
                "total": total_activities,
            },
            "assessments": {
                "total": total_assessments,
            },
        }

    @staticmethod
    def get_operational_report() -> dict:
        """Get operational report for admin."""
        session = db.session

        today = date.today()

        # Today's classes
        today_classes = (
            session.query(AcademyClassModel)
            .join(SessionModel, SessionModel.class_id == AcademyClassModel.id)
            .filter(
                SessionModel.scheduled_date == today, SessionModel.status == "SCHEDULED"
            )
            .all()
        )

        # Upcoming sessions (next 7 days)
        next_week = today + timedelta(days=7)
        upcoming_sessions = (
            session.query(SessionModel)
            .filter(
                SessionModel.scheduled_date >= today,
                SessionModel.scheduled_date <= next_week,
                SessionModel.status == "SCHEDULED",
            )
            .count()
        )

        # Pending enrollment requests
        pending_enrollments = (
            session.query(func.count(EnrollmentModel.id))
            .filter(EnrollmentModel.status == "PENDING")
            .scalar()
            or 0
        )

        # Sessions without attendance
        sessions_without_attendance = (
            session.query(func.count(SessionModel.id))
            .filter(
                SessionModel.status == "COMPLETED",
            )
            .filter(
                ~SessionModel.id.in_(
                    session.query(AttendanceModel.session_id).distinct()
                )
            )
            .scalar()
            or 0
        )

        # Failed notifications
        failed_notifications = (
            session.query(func.count(NotificationModel.id))
            .filter(NotificationModel.status == "FAILED")
            .scalar()
            or 0
        )

        # Unpaid balances (students with negative signed balance).
        # Signed CASE mirrors the canonical ledger balance: CHARGE/REFUND
        # debit, PAYMENT/DISCOUNT credit, REVERSAL/ADJUSTMENT stored signed.
        # A raw SUM(amount) would be wrong because debits and credits are
        # both stored positive.
        unpaid_balances = (
            session.query(
                FinancialTransactionModel.student_user_id,
                func.sum(
                    case(
                        (
                            FinancialTransactionModel.transaction_type == "PAYMENT",
                            FinancialTransactionModel.amount,
                        ),
                        (
                            FinancialTransactionModel.transaction_type == "DISCOUNT",
                            FinancialTransactionModel.amount,
                        ),
                        (
                            FinancialTransactionModel.transaction_type == "CHARGE",
                            -FinancialTransactionModel.amount,
                        ),
                        (
                            FinancialTransactionModel.transaction_type == "REFUND",
                            -FinancialTransactionModel.amount,
                        ),
                        else_=FinancialTransactionModel.amount,
                    )
                ).label("balance"),
            )
            .filter(FinancialTransactionModel.status == "ACTIVE")
            .group_by(FinancialTransactionModel.student_user_id)
            .having(
                func.sum(
                    case(
                        (
                            FinancialTransactionModel.transaction_type == "PAYMENT",
                            FinancialTransactionModel.amount,
                        ),
                        (
                            FinancialTransactionModel.transaction_type == "DISCOUNT",
                            FinancialTransactionModel.amount,
                        ),
                        (
                            FinancialTransactionModel.transaction_type == "CHARGE",
                            -FinancialTransactionModel.amount,
                        ),
                        (
                            FinancialTransactionModel.transaction_type == "REFUND",
                            -FinancialTransactionModel.amount,
                        ),
                        else_=FinancialTransactionModel.amount,
                    )
                )
                < 0
            )
            .count()
        )

        return {
            "today_classes": [
                {
                    "id": c.id,
                    "title": c.title,
                    "course": c.course.title if c.course else "",
                }
                for c in today_classes
            ],
            "upcoming_sessions": upcoming_sessions,
            "pending_enrollments": pending_enrollments,
            "sessions_without_attendance": sessions_without_attendance,
            "failed_notifications": failed_notifications,
            "unpaid_balances": unpaid_balances,
        }

    @staticmethod
    def get_notification_report() -> dict:
        """Get notification statistics."""
        session = db.session

        total = session.query(func.count(NotificationModel.id)).scalar() or 0
        sent = (
            session.query(func.count(NotificationModel.id))
            .filter(NotificationModel.status == "SENT")
            .scalar()
            or 0
        )
        failed = (
            session.query(func.count(NotificationModel.id))
            .filter(NotificationModel.status == "FAILED")
            .scalar()
            or 0
        )
        pending = (
            session.query(func.count(NotificationModel.id))
            .filter(NotificationModel.status == "PENDING")
            .scalar()
            or 0
        )

        # Delivery stats
        deliveries = (
            session.query(
                NotificationDeliveryModel.channel,
                func.count(NotificationDeliveryModel.id).label("total"),
                func.sum(
                    case((NotificationDeliveryModel.status == "DELIVERED", 1), else_=0)
                ).label("delivered"),
            )
            .group_by(NotificationDeliveryModel.channel)
            .all()
        )

        channel_stats = []
        for channel, channel_total, delivered in deliveries:
            channel_stats.append(
                {
                    "channel": channel,
                    "total": channel_total,
                    "delivered": delivered or 0,
                    "success_rate": round((delivered or 0) / channel_total * 100, 1)
                    if channel_total > 0
                    else 0,
                }
            )

        return {
            "total": total,
            "sent": sent,
            "failed": failed,
            "pending": pending,
            "success_rate": round(sent / total * 100, 1) if total > 0 else 0,
            "channels": channel_stats,
        }
