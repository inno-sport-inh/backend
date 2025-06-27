from django.db import transaction
from django.utils.timezone import make_naive
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from api.crud import get_ongoing_semester
from api.permissions import IsStudent
from api.serializers import (
    ReferenceUploadSerializer,
    EmptySerializer,
    ErrorSerializer,
    error_detail,
)
from sport.models import Reference


class ReferenceErrors:
    TOO_MUCH_UPLOADS_PER_DAY = (
        3,
        "Only 1 reference upload per day is allowed"
    )


@extend_schema(
    methods=["POST"],
    request=ReferenceUploadSerializer,
    responses={
        status.HTTP_200_OK: EmptySerializer,
        status.HTTP_400_BAD_REQUEST: ErrorSerializer,
    },
)
@api_view(["POST"])
@permission_classes([IsStudent])
@parser_classes([MultiPartParser])
def reference_upload(request, **kwargs):
    serializer = ReferenceUploadSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    student = request.user
    semester = get_ongoing_semester()
    start = serializer.validated_data['start']
    end = serializer.validated_data['end']
    image = serializer.validated_data['image']

    try:
        with transaction.atomic():
            reference = serializer.save(
                semester=semester,
                student_id=student.pk,
                hours=((end - start).days // 7) * semester.number_hours_one_week_ill
            )

            uploaded_date = make_naive(reference.uploaded).date()
            upload_count = Reference.objects.filter(
                student_id=student.pk,
                uploaded__date=uploaded_date
            ).count()

            if upload_count > 1:
                raise AssertionError

    except AssertionError:
        return Response(
            status=status.HTTP_400_BAD_REQUEST,
            data=error_detail(*ReferenceErrors.TOO_MUCH_UPLOADS_PER_DAY)
        )

    return Response({})
