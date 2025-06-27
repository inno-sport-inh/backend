from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from api.crud.crud_attendance import (
    toggle_has_QR,
    get_detailed_hours, get_detailed_hours_and_self,
)
from api.crud import (
    unenroll_student,
    enroll_student, get_ongoing_semester,
)
from api.permissions import IsStudent, IsStaff, IsTrainer, SportSelected
from api.serializers import (
    get_error_serializer,
    TrainingHourSerializer, EmptySerializer,
    HasQRSerializer, EnrollSerializer, error_detail,
    NotFoundSerializer, ErrorSerializer, UnenrollStudentSerializer,
)
from api.serializers.profile import GenderSerializer
from api.serializers.student import StudentSerializer
from sport.models import Semester, Student, Group, Enroll


class EnrollErrors:
    GROUP_IS_FULL = (2, "Group you chosen is full")
    TOO_MUCH_GROUPS = (3, "You have enrolled to too much groups")
    DOUBLE_ENROLL = (4, "You can't enroll to a group "
                        "you have already enrolled to"
                     )
    INCONSISTENT_UNENROLL = (5, "You are not enrolled to the group")
    MEDICAL_DISALLOWANCE = (6, "You can't enroll to the group "
                               "due to your medical group")
    NOT_ENROLLED = (7, "Requested student is not enrolled into this group")
    SPORT_ERROR = (8, "Requested group doesn't belong to requested student's sport")
    SEMESTER_ERROR = (9, "Requested group does't belong to current semester")
    QR_ERROR = (10, "Requested group has QR requirement")


class ProfileViewSet(viewsets.ViewSet):
    """
    ViewSet for profile-related operations
    """
    permission_classes = [IsStudent]

    @extend_schema(
        methods=["GET"],
        responses={
            status.HTTP_200_OK: StudentSerializer(),
        }
    )
    @action(detail=False, methods=['get'], url_path='student')
    def student_info(self, request):
        """
        Get info about current student.
        """
        student: Student = request.user.student
        serializer = StudentSerializer(student)
        return Response(serializer.data)

    @extend_schema(
        methods=["POST"],
        request=None,
        responses={
            status.HTTP_200_OK: HasQRSerializer,
        }
    )
    @action(detail=False, methods=['post'], url_path='toggle-qr')
    def toggle_qr_presence(self, request):
        """
        Toggles has_QR status
        """
        student = request.user.student
        toggle_has_QR(student)
        serializer = HasQRSerializer(student)
        return Response(serializer.data)

    @extend_schema(
        methods=["POST"],
        request=GenderSerializer,
        responses={
            status.HTTP_200_OK: EmptySerializer,
        }
    )
    @action(detail=False, methods=['post'], url_path='change-gender', permission_classes=[IsStaff])
    def change_gender(self, request):
        """
        Change student gender (staff only)
        """
        serializer = GenderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        student = Student.objects.get(user_id=serializer.validated_data['student_id'])
        student.gender = serializer.validated_data['gender']
        student.save()

        return Response({})

    @extend_schema(
        methods=["GET"],
        parameters=[
            OpenApiParameter(
                name='semester_id',
                description='Semester ID',
                required=True,
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
            ),
        ],
        responses={
            status.HTTP_200_OK: TrainingHourSerializer(many=True),
        }
    )
    @action(detail=False, methods=['get'], url_path='history/(?P<semester_id>[^/.]+)')
    def history(self, request, semester_id=None):
        """
        Get student training history for a semester
        """
        student = request.user.student
        semester = Semester.objects.get(id=semester_id)
        hours = get_detailed_hours(student, semester)
        serializer = TrainingHourSerializer(hours, many=True)
        return Response(serializer.data)

    @extend_schema(
        methods=["GET"],
        parameters=[
            OpenApiParameter(
                name='semester_id',
                description='Semester ID',
                required=True,
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
            ),
        ],
        responses={
            status.HTTP_200_OK: TrainingHourSerializer(many=True),
        }
    )
    @action(detail=False, methods=['get'], url_path='history-with-self/(?P<semester_id>[^/.]+)')
    def history_with_self(self, request, semester_id=None):
        """
        Get student training history with self sport for a semester
        """
        student = request.user.student
        semester = Semester.objects.get(id=semester_id)
        hours = get_detailed_hours_and_self(student, semester)
        serializer = TrainingHourSerializer(hours, many=True)
        return Response(serializer.data)


class EnrollmentViewSet(viewsets.ViewSet):
    """
    ViewSet for enrollment-related operations
    """
    permission_classes = [IsStudent, SportSelected]

    @extend_schema(
        methods=["POST"],
        request=EnrollSerializer,
        responses={
            status.HTTP_200_OK: EmptySerializer,
            status.HTTP_404_NOT_FOUND: NotFoundSerializer,
            status.HTTP_400_BAD_REQUEST: ErrorSerializer,
        }
    )
    @action(detail=False, methods=['post'])
    @transaction.atomic
    def enroll(self, request):
        """
        Enroll student in a group
        
        Error codes:
        2 - Group you chosen is full
        3 - You have too much secondary groups
        4 - You can't enroll to a group you have already enrolled to
        6 - Enroll with insufficient medical group
        8 - Requested group doesn't belong to requested student's sport
        9 - Requested group doesn't belong to current semester
        """
        serializer = EnrollSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        group = get_object_or_404(
            Group,
            pk=serializer.validated_data["group_id"]
        )
        student = request.user.student
        
        # Validate sport match
        if student.sport != group.sport:
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data=error_detail(*EnrollErrors.SPORT_ERROR)
            )
        
        # Check for double enrollment
        if Enroll.objects.filter(group=group, student=student).exists():
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data=error_detail(*EnrollErrors.DOUBLE_ENROLL)
            )
        
        # Check enrollment limit
        if Group.objects.filter(semester=get_ongoing_semester(), enrolls__student=student).exists():
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data=error_detail(*EnrollErrors.TOO_MUCH_GROUPS)
            )
        
        # Validate semester
        if group.semester.id != get_ongoing_semester().id:
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data=error_detail(*EnrollErrors.SEMESTER_ERROR)
            )
        
        # Check medical group allowance
        if not group.allowed_medical_groups.filter(id=student.medical_group.id).exists():
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data=error_detail(*EnrollErrors.MEDICAL_DISALLOWANCE)
            )
        
        # Perform enrollment
        try:
            enroll_student(student, group)
            return Response({})
        except Exception as e:
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data=error_detail(1, str(e))
            )

    @extend_schema(
        methods=["POST"],
        responses={
            status.HTTP_200_OK: EmptySerializer,
        }
    )
    @action(detail=False, methods=['post'])
    def unenroll(self, request):
        """
        Unenroll student from a group
        """
        # TODO: Implement unenrollment logic based on api/views/enroll.py
        return Response({})

    @extend_schema(
        methods=["POST"],
        responses={
            status.HTTP_200_OK: EmptySerializer,
        }
    )
    @action(detail=False, methods=['post'], url_path='unenroll-by-trainer', permission_classes=[IsTrainer])
    def unenroll_by_trainer(self, request):
        """
        Unenroll student by trainer (trainer only)
        """
        # TODO: Implement trainer unenrollment logic based on api/views/enroll.py
        return Response({})


class GroupViewSet(viewsets.ViewSet):
    """
    ViewSet for group-related operations
    """

    @extend_schema(
        methods=["GET"],
        responses={
            status.HTTP_200_OK: EmptySerializer,  # TODO: Replace with proper serializer
        }
    )
    def retrieve(self, request, pk=None):
        """
        Get group information
        """
        # TODO: Implement group info logic
        return Response({})

    @extend_schema(
        methods=["GET"],
        responses={
            status.HTTP_200_OK: EmptySerializer,  # TODO: Replace with proper serializer
        }
    )
    @action(detail=False, methods=['get'], url_path='sports')
    def sports(self, request):
        """
        Get list of available sports
        """
        # TODO: Implement sports list logic
        return Response({})

    @extend_schema(
        methods=["POST"],
        responses={
            status.HTTP_200_OK: EmptySerializer,
        }
    )
    @action(detail=False, methods=['post'], url_path='select-sport')
    def select_sport(self, request):
        """
        Select sport for student
        """
        # TODO: Implement sport selection logic
        return Response({})


class TrainingViewSet(viewsets.ViewSet):
    """
    ViewSet for training-related operations
    """

    @extend_schema(
        methods=["GET"],
        responses={
            status.HTTP_200_OK: EmptySerializer,  # TODO: Replace with proper serializer
        }
    )
    def retrieve(self, request, pk=None):
        """
        Get training information
        """
        # TODO: Implement training info logic
        return Response({})

    @extend_schema(
        methods=["POST"],
        responses={
            status.HTTP_200_OK: EmptySerializer,
        }
    )
    @action(detail=True, methods=['post'], url_path='check-in')
    def check_in(self, request, pk=None):
        """
        Check in to training
        """
        # TODO: Implement check-in logic
        return Response({})

    @extend_schema(
        methods=["POST"],
        responses={
            status.HTTP_200_OK: EmptySerializer,
        }
    )
    @action(detail=True, methods=['post'], url_path='cancel-check-in')
    def cancel_check_in(self, request, pk=None):
        """
        Cancel check-in to training
        """
        # TODO: Implement cancel check-in logic
        return Response({})


class AttendanceViewSet(viewsets.ViewSet):
    """
    ViewSet for attendance-related operations
    """

    @extend_schema(
        methods=["POST"],
        responses={
            status.HTTP_200_OK: EmptySerializer,
        }
    )
    @action(detail=False, methods=['post'])
    def mark(self, request):
        """
        Mark attendance for a student
        """
        # TODO: Implement attendance marking logic
        return Response({})

    @extend_schema(
        methods=["GET"],
        responses={
            status.HTTP_200_OK: EmptySerializer,  # TODO: Replace with proper serializer
        }
    )
    @action(detail=False, methods=['get'], url_path='suggest-student')
    def suggest_student(self, request):
        """
        Suggest student for attendance
        """
        # TODO: Implement student suggestion logic
        return Response({})

    @extend_schema(
        methods=["GET"],
        responses={
            status.HTTP_200_OK: EmptySerializer,  # TODO: Replace with proper serializer
        }
    )
    @action(detail=False, methods=['get'], url_path='training/(?P<training_id>[^/.]+)/grades')
    def grades(self, request, training_id=None):
        """
        Get grades for a training
        """
        # TODO: Implement grades logic
        return Response({})

    @extend_schema(
        methods=["GET"],
        responses={
            status.HTTP_200_OK: EmptySerializer,  # TODO: Replace with proper serializer
        }
    )
    @action(detail=False, methods=['get'], url_path='student/(?P<student_id>[^/.]+)/hours')
    def student_hours(self, request, student_id=None):
        """
        Get student hours information
        """
        # TODO: Implement student hours logic
        return Response({})


class CalendarViewSet(viewsets.ViewSet):
    """
    ViewSet for calendar-related operations
    """

    @extend_schema(
        methods=["GET"],
        responses={
            status.HTTP_200_OK: EmptySerializer,  # TODO: Replace with proper serializer
        }
    )
    @action(detail=False, methods=['get'], url_path='sport/(?P<sport_id>[^/.]+)/schedule')
    def schedule(self, request, sport_id=None):
        """
        Get schedule for a sport
        """
        # TODO: Implement schedule logic
        return Response({})

    @extend_schema(
        methods=["GET"],
        responses={
            status.HTTP_200_OK: EmptySerializer,  # TODO: Replace with proper serializer
        }
    )
    @action(detail=False, methods=['get'], url_path='trainings')
    def personal_schedule(self, request):
        """
        Get personal training schedule
        """
        # TODO: Implement personal schedule logic
        return Response({})


class ReferenceViewSet(viewsets.ViewSet):
    """
    ViewSet for reference-related operations
    """

    @extend_schema(
        methods=["POST"],
        responses={
            status.HTTP_200_OK: EmptySerializer,
        }
    )
    @action(detail=False, methods=['post'], url_path='upload')
    def upload(self, request):
        """
        Upload reference document
        """
        # TODO: Implement reference upload logic
        return Response({})


class SelfSportViewSet(viewsets.ViewSet):
    """
    ViewSet for self sport report operations
    """

    @extend_schema(
        methods=["POST"],
        responses={
            status.HTTP_200_OK: EmptySerializer,
        }
    )
    @action(detail=False, methods=['post'], url_path='upload')
    def upload(self, request):
        """
        Upload self sport report
        """
        # TODO: Implement self sport upload logic
        return Response({})

    @extend_schema(
        methods=["GET"],
        responses={
            status.HTTP_200_OK: EmptySerializer,  # TODO: Replace with proper serializer
        }
    )
    @action(detail=False, methods=['get'], url_path='types')
    def types(self, request):
        """
        Get available self sport types
        """
        # TODO: Implement self sport types logic
        return Response({})

    @extend_schema(
        methods=["GET"],
        responses={
            status.HTTP_200_OK: EmptySerializer,  # TODO: Replace with proper serializer
        }
    )
    @action(detail=False, methods=['get'], url_path='strava-parsing')
    def strava_parsing(self, request):
        """
        Parse Strava activity information
        """
        # TODO: Implement Strava parsing logic
        return Response({})


class FitnessTestViewSet(viewsets.ViewSet):
    """
    ViewSet for fitness test operations
    """

    @extend_schema(
        methods=["GET"],
        responses={
            status.HTTP_200_OK: EmptySerializer,  # TODO: Replace with proper serializer
        }
    )
    @action(detail=False, methods=['get'], url_path='result')
    def result(self, request):
        """
        Get fitness test result
        """
        # TODO: Implement fitness test result logic
        return Response({})

    @extend_schema(
        methods=["POST"],
        responses={
            status.HTTP_200_OK: EmptySerializer,
        }
    )
    @action(detail=False, methods=['post'], url_path='upload')
    def upload(self, request):
        """
        Upload fitness test results
        """
        # TODO: Implement fitness test upload logic
        return Response({})

    @extend_schema(
        methods=["GET"],
        responses={
            status.HTTP_200_OK: EmptySerializer,  # TODO: Replace with proper serializer
        }
    )
    @action(detail=False, methods=['get'], url_path='exercises')
    def exercises(self, request):
        """
        Get available exercises
        """
        # TODO: Implement exercises logic
        return Response({})

    @extend_schema(
        methods=["GET"],
        responses={
            status.HTTP_200_OK: EmptySerializer,  # TODO: Replace with proper serializer
        }
    )
    @action(detail=False, methods=['get'], url_path='sessions')
    def sessions(self, request):
        """
        Get fitness test sessions
        """
        # TODO: Implement sessions logic
        return Response({})


class MeasurementViewSet(viewsets.ViewSet):
    """
    ViewSet for measurement operations
    """

    @extend_schema(
        methods=["POST"],
        responses={
            status.HTTP_200_OK: EmptySerializer,
        }
    )
    @action(detail=False, methods=['post'], url_path='student-measurement')
    def student_measurement(self, request):
        """
        Post student measurement
        """
        # TODO: Implement student measurement logic
        return Response({})

    @extend_schema(
        methods=["GET"],
        responses={
            status.HTTP_200_OK: EmptySerializer,  # TODO: Replace with proper serializer
        }
    )
    @action(detail=False, methods=['get'], url_path='results')
    def results(self, request):
        """
        Get measurement results
        """
        # TODO: Implement measurement results logic
        return Response({})

    @extend_schema(
        methods=["GET"],
        responses={
            status.HTTP_200_OK: EmptySerializer,  # TODO: Replace with proper serializer
        }
    )
    @action(detail=False, methods=['get'], url_path='measurements')
    def measurements(self, request):
        """
        Get available measurements
        """
        # TODO: Implement measurements logic
        return Response({})


class SemesterViewSet(viewsets.ViewSet):
    """
    ViewSet for semester operations
    """

    @extend_schema(
        methods=["GET"],
        responses={
            status.HTTP_200_OK: EmptySerializer,  # TODO: Replace with proper serializer
        }
    )
    def list(self, request):
        """
        Get current semester information
        """
        # TODO: Implement semester logic
        return Response({})


class AnalyticsViewSet(viewsets.ViewSet):
    """
    ViewSet for analytics operations
    """

    @extend_schema(
        methods=["GET"],
        responses={
            status.HTTP_200_OK: EmptySerializer,  # TODO: Replace with proper serializer
        }
    )
    @action(detail=False, methods=['get'], url_path='attendance')
    def attendance(self, request):
        """
        Get attendance analytics
        """
        # TODO: Implement attendance analytics logic
        return Response({})


class MedicalGroupsViewSet(viewsets.ViewSet):
    """
    ViewSet for medical groups operations
    """

    @extend_schema(
        methods=["GET"],
        responses={
            status.HTTP_200_OK: EmptySerializer,  # TODO: Replace with proper serializer
        }
    )
    def list(self, request):
        """
        Get medical groups information
        """
        # TODO: Implement medical groups logic
        return Response({})
