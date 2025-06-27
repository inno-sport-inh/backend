import csv
import enum
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, NotFound
from rest_framework.response import Response
from django.views.decorators.cache import cache_page
from django.utils.dateparse import parse_date
from django.db import models

from api.crud import Training, \
    get_students_grades, mark_hours, get_student_last_attended_dates, \
    get_student_hours, get_negative_hours, better_than, get_email_name_like_students_filtered_by_group
from api.permissions import IsStaff, IsStudent, IsTrainer, IsSuperUser
from api.serializers import SuggestionQuerySerializer, SuggestionSerializer, \
    NotFoundSerializer, InbuiltErrorSerializer, \
    TrainingGradesSerializer, AttendanceMarkSerializer, error_detail, \
    BadGradeReportGradeSerializer, BadGradeReport, LastAttendedDatesSerializer, HoursInfoSerializer, \
    HoursInfoFullSerializer, AttendanceSerializer, ErrorSerializer
from api.serializers.attendance import BetterThanInfoSerializer
from sport.models import Group, Student, Attendance

User = get_user_model()


class AttendanceErrors:
    TRAINING_NOT_EDITABLE = (
        2,
        f"Training not editable before it or after "
        f"{settings.TRAINING_EDITABLE_INTERVAL.days} days")
    OUTBOUND_GRADES = (
        3, "Some students received negative marks or more than maximum")


class DateError(enum.Enum):
    OUT_OF_RANGE = 1
    INCORRECT_FORMAT = 2
    BOTH_DATES_REQUIRED = 3
    START_BEFORE_END = 4


def is_training_group(group, trainer):
    if not group.trainers.filter(pk=trainer.pk).exists():
        raise PermissionDenied(
            detail="You are not a teacher of this group"
        )


def compose_bad_grade_report(email: str, hours: float) -> dict:
    return {
        "email": email,
        "hours": hours,
    }


# ======================
# Student Suggestions
# ======================
@extend_schema(
    methods=["GET"],
    parameters=[SuggestionQuerySerializer],
    responses={
        status.HTTP_200_OK: SuggestionSerializer(many=True),
    },
    description="Suggest students for attendance marking"
)
@api_view(["GET"])
@permission_classes([IsTrainer | IsSuperUser])
def suggest_student(request):
    serializer = SuggestionQuerySerializer(data=request.query_params)
    serializer.is_valid(raise_exception=True)

    suggested_students = get_email_name_like_students_filtered_by_group(
        serializer.validated_data["term"],
        group=serializer.validated_data["group_id"]
    )
    return Response([
        {
            "value": f"{student['id']}_"
                     f"{student['full_name']}_"
                     f"{student['email']}_"
                     f"{student['medical_group__name']}",
            "label": f"{student['full_name']} "
                     f"({student['email']})",
        }
        for student in suggested_students
    ])


# ======================
# Training Grades
# ======================
@extend_schema(
    methods=["GET"],
    responses={
        status.HTTP_200_OK: TrainingGradesSerializer,
        status.HTTP_404_NOT_FOUND: NotFoundSerializer,
        status.HTTP_403_FORBIDDEN: InbuiltErrorSerializer,
    },
    description="Get grades for a specific training"
)
@api_view(["GET"])
@permission_classes([IsTrainer | IsSuperUser])
def get_grades(request, training_id):
    trainer = request.user
    training = get_object_or_404(
        Training.objects.select_related("group"),
        pk=training_id
    )

    if not trainer.is_superuser:
        is_training_group(training.group, trainer)

    return Response({
        "group_id": training.group_id,
        "group_name": training.group.to_frontend_name(),
        "start": training.start,
        "grades": get_students_grades(training_id),
        "academic_duration": training.academic_duration,
    })


@extend_schema(
    methods=["GET"],
    responses={
        (status.HTTP_200_OK, 'text/csv'): OpenApiTypes.BINARY,
        status.HTTP_404_NOT_FOUND: NotFoundSerializer,
        status.HTTP_403_FORBIDDEN: InbuiltErrorSerializer,
    },
    description="Export training grades to CSV"
)
@api_view(["GET"])
@permission_classes([IsTrainer | IsSuperUser])
def get_grades_csv(request, training_id):
    trainer = request.user
    training = get_object_or_404(
        Training.objects.select_related("group"),
        pk=training_id
    )

    if not trainer.is_superuser:
        is_training_group(training.group, trainer)

    grades = get_students_grades(training_id)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="grades_training_{training_id}.csv"'

    writer = csv.DictWriter(response, ["full_name", "email", "hours", "med_group"], extrasaction="ignore")
    writer.writeheader()
    writer.writerows(grades)

    return response


# ======================
# Attendance Reports
# ======================
@extend_schema(
    methods=["GET"],
    responses={
        status.HTTP_200_OK: LastAttendedDatesSerializer,
        status.HTTP_404_NOT_FOUND: NotFoundSerializer,
        status.HTTP_403_FORBIDDEN: InbuiltErrorSerializer,
    },
    description="Get last attended dates for students in a group"
)
@api_view(["GET"])
@permission_classes([IsTrainer | IsSuperUser])
def get_last_attended_dates(request, group_id):
    trainer = request.user
    group = get_object_or_404(Group, pk=group_id)

    if not trainer.is_superuser:
        is_training_group(group, trainer)

    return Response({
        "last_attended_dates": get_student_last_attended_dates(group_id)
    })


# ======================
# Student Hours Info
# ======================
@extend_schema(
    methods=["GET"],
    responses={
        status.HTTP_200_OK: HoursInfoFullSerializer,
        status.HTTP_404_NOT_FOUND: NotFoundSerializer,
        status.HTTP_403_FORBIDDEN: InbuiltErrorSerializer,
    },
    description="Get negative hours info for a student"
)
@api_view(["GET"])
@permission_classes([IsStudent | IsStaff | IsSuperUser])
def get_negative_hours_info(request, student_id):
    return Response({"final_hours": get_negative_hours(student_id)})


@extend_schema(
    methods=["GET"],
    responses={
        status.HTTP_200_OK: HoursInfoSerializer,
        status.HTTP_404_NOT_FOUND: NotFoundSerializer,
        status.HTTP_403_FORBIDDEN: InbuiltErrorSerializer,
    },
    description="Get student hours information"
)
@api_view(["GET"])
@permission_classes([IsStudent | IsStaff | IsSuperUser])
def get_student_hours_info(request, student_id):
    return Response(get_student_hours(student_id))


@extend_schema(
    methods=["GET"],
    responses={
        status.HTTP_200_OK: BetterThanInfoSerializer,
        status.HTTP_404_NOT_FOUND: NotFoundSerializer,
        status.HTTP_403_FORBIDDEN: InbuiltErrorSerializer,
    },
    description="Get student comparison information"
)
@api_view(["GET"])
@permission_classes([IsStudent | IsStaff | IsSuperUser])
@cache_page(60 * 60 * 24)
def get_better_than_info(request, student_id):
    return Response(better_than(student_id))


# ======================
# Attendance Marking
# ======================
@extend_schema(
    methods=["POST"],
    request=AttendanceMarkSerializer,
    responses={
        status.HTTP_200_OK: BadGradeReportGradeSerializer(many=True),
        status.HTTP_400_BAD_REQUEST: BadGradeReport(),
        status.HTTP_403_FORBIDDEN: InbuiltErrorSerializer,
    },
    description="Mark attendance for students in a training"
)
@api_view(["POST"])
@permission_classes([IsTrainer | IsSuperUser])
def mark_attendance(request):
    serializer = AttendanceMarkSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    trainer = request.user
    training = get_object_or_404(
        Training.objects.select_related("group"),
        pk=serializer.validated_data["training_id"]
    )

    if not trainer.is_superuser:
        is_training_group(training.group, trainer)

    now = timezone.now()
    if not training.start <= now <= training.start + settings.TRAINING_EDITABLE_INTERVAL:
        return Response(
            status=status.HTTP_400_BAD_REQUEST,
            data=error_detail(*AttendanceErrors.TRAINING_NOT_EDITABLE)
        )

    id_to_hours = {
        item["student_id"]: item["hours"]
        for item in serializer.validated_data["students_hours"]
    }

    students = User.objects.filter(
        pk__in=id_to_hours.keys()
    ).only("email")

    negative_mark = []
    overflow_mark = []
    hours_to_mark = []
    max_hours = training.academic_duration

    for student in students:
        hours_put = id_to_hours[student.pk]
        if hours_put < 0:
            negative_mark.append(compose_bad_grade_report(student.email, hours_put))
        elif hours_put > max_hours:
            overflow_mark.append(compose_bad_grade_report(student.email, hours_put))
        elif str(Student.objects.get(user=student).student_status) != 'Normal':
            continue
        else:
            hours_to_mark.append((student, hours_put))

    if negative_mark or overflow_mark:
        return Response(
            status=status.HTTP_400_BAD_REQUEST,
            data={
                **error_detail(*AttendanceErrors.OUTBOUND_GRADES),
                "negative_marks": negative_mark,
                "overflow_marks": overflow_mark,
            }
        )
    
    mark_data = [(x[0].pk, x[1]) for x in hours_to_mark]
    mark_hours(training, mark_data)
    return Response([
        compose_bad_grade_report(x[0].email, x[1])
        for x in hours_to_mark
    ])


# ======================
# Student Training History
# ======================
@extend_schema(
    methods=["GET"],
    responses={
        status.HTTP_200_OK: AttendanceSerializer(many=True),
        status.HTTP_400_BAD_REQUEST: ErrorSerializer,
    },
    parameters=[
        OpenApiParameter(
            name='date_start',
            type=OpenApiTypes.DATE,
            location=OpenApiParameter.QUERY,
            description='Start date (YYYY-MM-DD)',
            required=True,
        ),
        OpenApiParameter(
            name='date_end',
            type=OpenApiTypes.DATE,
            location=OpenApiParameter.QUERY,
            description='End date (YYYY-MM-DD)',
            required=True,
        ),
    ],
    description="Get student trainings between dates"
)
@api_view(["GET"])
@permission_classes([IsStudent])
def get_student_trainings_between_dates(request):
    student = request.user.student
    date_start = request.query_params.get('date_start')
    date_end = request.query_params.get('date_end')

    if not date_start or not date_end:
        return Response(
            status=status.HTTP_400_BAD_REQUEST,
            data=error_detail(
                DateError.BOTH_DATES_REQUIRED.value,
                "Both date_start and date_end are required"
            )
        )

    try:
        date_start = parse_date(date_start)
        date_end = parse_date(date_end)
    except (ValueError, TypeError):
        return Response(
            status=status.HTTP_400_BAD_REQUEST,
            data=error_detail(
                DateError.INCORRECT_FORMAT.value,
                "Invalid date format. Use YYYY-MM-DD"
            )
        )

    if not date_start or not date_end:
        return Response(
            status=status.HTTP_400_BAD_REQUEST,
            data=error_detail(
                DateError.OUT_OF_RANGE.value,
                "One of the dates is invalid"
            )
        )

    if date_start > date_end:
        return Response(
            status=status.HTTP_400_BAD_REQUEST,
            data=error_detail(
                DateError.START_BEFORE_END.value,
                "date_end should be greater than date_start"
            )
        )

    attendances = Attendance.objects.filter(
        student=student,
        training__start__gte=date_start,
        training__start__lte=date_end + timedelta(days=1)
    ).select_related(
        'training', 'training__training_class', 
        'training__group', 'training__group__sport'
    ).prefetch_related(
        'training__group__trainers__user'
    )

    return Response([
        {
            'hours': a.hours,
            'training_id': a.training.pk,
            'date': a.training.start.strftime('%Y-%m-%d'),
            'training_class': a.training.training_class.name if a.training.training_class else '',
            'group_id': a.training.group.pk,
            'group_name': a.training.group.to_frontend_name(),
            'trainers_emails': [t.user.email for t in a.training.group.trainers.all()],
        } for a in attendances
    ])