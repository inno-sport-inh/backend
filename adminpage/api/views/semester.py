from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from api.crud import get_semester_crud
from api.serializers import NotFoundSerializer
from api.serializers.semester import SemesterSerializer


@extend_schema(
    methods=["GET"],
    tags=["Schedule & Organization"],
    summary="Get semester information",
    description="Retrieve semester information. Use 'current=true' to get only current semester.",
    parameters=[
        OpenApiParameter(name='current', type=OpenApiTypes.BOOL, description='Get only current semester'),
    ],
    responses={
        status.HTTP_200_OK: SemesterSerializer(many=True),
        status.HTTP_404_NOT_FOUND: NotFoundSerializer(),
    }
)
@api_view(['GET'])
def get_semester(request, **kwargs):
    current = request.query_params.get('current', False)
    current = True if current == 'true' else False

    data = [SemesterSerializer(elem).data for elem in get_semester_crud(current)]
    if len(data):
        return Response(status=status.HTTP_200_OK, data=data)
    else:
        return Response(status=status.HTTP_404_NOT_FOUND, data=NotFoundSerializer().data)
