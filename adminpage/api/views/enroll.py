from django.db import transaction, InternalError, IntegrityError
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from api.crud import (
    unenroll_student,
    enroll_student, 
    get_ongoing_semester,
)
from api.permissions import IsStudent, IsTrainer, SportSelected
from api.serializers import (
    EnrollSerializer,
    error_detail,
    EmptySerializer,
    NotFoundSerializer,
    ErrorSerializer, 
    UnenrollStudentSerializer,
)
from api.views.attendance import is_training_group
from sport.models import Group, Student, Enroll


class EnrollErrors:
    GROUP_IS_FULL = (2, "Group is full")
    TOO_MUCH_GROUPS = (3, "Maximum group limit reached")
    DOUBLE_ENROLL = (4, "Already enrolled in this group")
    INCONSISTENT_UNENROLL = (5, "Not enrolled in this group")
    MEDICAL_DISALLOWANCE = (6, "Medical group restriction")
    NOT_ENROLLED = (7, "Student not enrolled in this group")
    SPORT_ERROR = (8, "Group sport mismatch")
    SEMESTER_ERROR = (9, "Invalid semester for group")
    QR_ERROR = (10, "QR code requirement not met")


@extend_schema(
    methods=["POST"],
    request=EnrollSerializer,
    responses={
        status.HTTP_200_OK: EmptySerializer,
        status.HTTP_404_NOT_FOUND: NotFoundSerializer,
        status.HTTP_400_BAD_REQUEST: ErrorSerializer,
    },
)
@api_view(["POST"])
@permission_classes([IsStudent, SportSelected])
@transaction.atomic
def enroll_student_to_group(request):
    serializer = EnrollSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    group = get_object_or_404(Group, pk=serializer.validated_data["group_id"])
    student = request.user.student

    if student.sport != group.sport:
        return error_response(EnrollErrors.SPORT_ERROR)
    
    if Enroll.objects.filter(group=group, student=student).exists():
        return error_response(EnrollErrors.DOUBLE_ENROLL)
    
    if Group.objects.filter(semester=get_ongoing_semester(), enrolls__student=student).exists():
        return error_response(EnrollErrors.TOO_MUCH_GROUPS)
    
    if group.semester.id != get_ongoing_semester().id:
        return error_response(EnrollErrors.SEMESTER_ERROR)
    
    if not group.allowed_medical_groups.filter(id=student.medical_group.id).exists():
        return error_response(EnrollErrors.MEDICAL_DISALLOWANCE)

    try:
        enroll_student(group, student)
    except IntegrityError:
        return error_response(EnrollErrors.DOUBLE_ENROLL)
    except InternalError as e:
        if "too much groups" in str(e):
            return error_response(EnrollErrors.TOO_MUCH_GROUPS)
        return error_response(EnrollErrors.GROUP_IS_FULL)

    return Response({})


@extend_schema(
    methods=["POST"],
    request=EnrollSerializer,
    responses={
        status.HTTP_200_OK: EmptySerializer,
        status.HTTP_404_NOT_FOUND: NotFoundSerializer,
        status.HTTP_400_BAD_REQUEST: ErrorSerializer,
    },
)
@api_view(["POST"])
@permission_classes([IsStudent])
@transaction.atomic
def unenroll_student_from_group(request):
    serializer = EnrollSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    group = get_object_or_404(Group, pk=serializer.validated_data["group_id"])
    student = request.user.student

    if unenroll_student(group, student) == 0:
        return error_response(EnrollErrors.INCONSISTENT_UNENROLL)
    
    return Response({})


@extend_schema(
    methods=["POST"],
    request=UnenrollStudentSerializer,
    responses={
        status.HTTP_200_OK: EmptySerializer,
        status.HTTP_404_NOT_FOUND: NotFoundSerializer,
        status.HTTP_400_BAD_REQUEST: ErrorSerializer,
    },
)
@api_view(["POST"])
@permission_classes([IsTrainer])
@transaction.atomic
def trainer_remove_student(request):
    serializer = UnenrollStudentSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    group = get_object_or_404(Group, pk=serializer.validated_data["group_id"])
    is_training_group(group, request.user)

    student = get_object_or_404(Student, pk=serializer.validated_data["student_id"])

    if unenroll_student(group, student) == 0:
        return error_response(EnrollErrors.NOT_ENROLLED)
    
    return Response({})


def error_response(error):
    return Response(
        status=status.HTTP_400_BAD_REQUEST,
        data=error_detail(*error)
    )