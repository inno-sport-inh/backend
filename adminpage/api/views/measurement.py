import datetime
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from api.crud import get_ongoing_semester
from api.permissions import IsStudent, IsTrainer

from api.serializers import (
    MeasurementPostSerializer,
    MeasurementResultsSerializer,
    NotFoundSerializer,
    ErrorSerializer,
)

from sport.models import Measurement, MeasurementSession, MeasurementResult, Student


@extend_schema(
    methods=["GET"],
    responses={
        status.HTTP_200_OK: MeasurementResultsSerializer,
    }
)
@api_view(["GET"])
def get_measurements(request, **kwargs):
    measurements = Measurement.objects.all()
    result = []
    for measurement in measurements:
        result.append({
            "name": measurement.name,
            "value_unit": measurement.value_unit
        })
    return Response(result)


@extend_schema(
    methods=["GET"],
    responses={
        status.HTTP_200_OK: MeasurementResultsSerializer,
    }
)
@api_view(["GET"])
@permission_classes([IsStudent])
def get_results(request, **kwargs):
    session_qs = MeasurementSession.objects.filter(student=request.user.student)
    if not session_qs.exists():
        return Response([])

    session = session_qs.first()
    results = MeasurementResult.objects.filter(session=session)

    if not results.exists():
        return Response({"code": "There is no results"})

    grouped_by_semester = {}
    for result in results:
        result_data = {
            'measurement': result.measurement.name,
            'unit': result.measurement.value_unit,
            'value': result.value,
            'approved': result.session.approved,
            'date': result.session.date,
        }
        semester_name = result.session.semester.name
        grouped_by_semester.setdefault(semester_name, []).append(result_data)

    response = [{"semester": sem, "result": res} for sem, res in grouped_by_semester.items()]
    return Response(response)


@extend_schema(
    methods=["POST"],
    request=MeasurementPostSerializer,
    responses={
        status.HTTP_404_NOT_FOUND: NotFoundSerializer,
        status.HTTP_400_BAD_REQUEST: ErrorSerializer,
    },
)
@api_view(["POST"])
@permission_classes([IsTrainer])
def post_student_measurement(request, **kwargs):
    approved = hasattr(request.user, 'trainer')
    if approved:
        student = Student.objects.get(user_id=request.data['student_id'])
    else:
        student = request.user.student

    measurement_qs = Measurement.objects.filter(id=request.data['measurement_id'])
    if not measurement_qs.exists():
        return Response({}, status=status.HTTP_404_NOT_FOUND)

    measurement = measurement_qs.first()
    session, _ = MeasurementSession.objects.get_or_create(
        student=student,
        approved=approved,
        date=datetime.datetime.today(),
        semester=get_ongoing_semester()
    )

    result, _ = MeasurementResult.objects.get_or_create(
        measurement=measurement,
        session=session
    )
    result.value = request.data['value']
    result.save()

    return Response({'result_id': result.id})
