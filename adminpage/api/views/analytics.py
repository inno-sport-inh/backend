from datetime import datetime, timedelta
from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    OpenApiTypes,
)
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from api.permissions import IsStaff, IsSuperUser
from sport.models import Attendance


@extend_schema(
    methods=["GET"],
    parameters=[
        OpenApiParameter(
            name='sport_id',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description="Filter by sport ID"
        ),
        OpenApiParameter(
            name='medical_group_id',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description="Filter by medical group ID"
        ),
        OpenApiParameter(
            name='days',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description="Time period in days (default: 30)",
            default=30
        ),
    ],
    responses={
        status.HTTP_200_OK: {
            "type": "object",
            "additionalProperties": {
                "type": "integer"
            },
            "example": {
                "2023-05-01": 15,
                "2023-05-02": 20
            }
        },
    },
    description="Get attendance analytics aggregated by date"
)
@api_view(["GET"])
@permission_classes([IsStaff | IsSuperUser])
def attendance_analytics(request):
    """
    GET /analytics/attendance
    Returns attendance count grouped by date for the specified period
    """
    # Get query parameters with defaults
    sport_id = request.query_params.get("sport_id")
    medical_group_id = request.query_params.get("medical_group_id")
    days = int(request.query_params.get("days", 30))
    
    # Calculate time period
    time_period = datetime.now() - timedelta(days=days)
    
    # Build query
    query = Attendance.objects.filter(
        training__start__gt=time_period
    ).select_related(
        'training__group__sport',
        'student__medical_group'
    )
    
    # Apply filters
    if sport_id:
        query = query.filter(training__group__sport__id=sport_id)
    if medical_group_id:
        query = query.filter(student__medical_group__id=medical_group_id)

    # Optimized aggregation in database
    result = (
        query.extra({'date': "date(sport_attendance.training.start)"})
        .values('date')
        .annotate(count=models.Count('id'))
        .order_by('date')
    )

    # Format response
    formatted_result = {
        entry['date'].strftime("%Y-%m-%d"): entry['count']
        for entry in result
    }
    
    return Response(formatted_result)