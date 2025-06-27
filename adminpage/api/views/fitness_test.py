from collections import defaultdict
from django.db.models import Q
from drf_spectacular.utils import extend_schema
from rest_framework import status, serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from api.permissions import IsTrainer, IsStudent, IsSuperUser
from api.serializers import (
    NotFoundSerializer,
    ErrorSerializer, 
    SuggestionSerializer,
)
from api.crud import (
    get_exercises_crud, 
    post_student_exercises_result_crud,
    get_email_name_like_students, 
    get_ongoing_semester, 
    get_score, 
    get_max_score
)
from api.serializers.attendance import SuggestionQueryFTSerializer
from api.serializers.fitness_test import (
    FitnessTestExerciseSerializer,
    FitnessTestSessionSerializer,
    FitnessTestSessionWithResult, 
    FitnessTestStudentResult,
    FitnessTestUpload
)
from api.serializers.semester import SemesterInSerializer
from sport.models import (
    FitnessTestSession, 
    FitnessTestResult, 
    FitnessTestExercise, 
    Semester, 
    Student
)


# ======================
# Exercise Endpoints
# ======================
@extend_schema(
    methods=["GET"],
    description='Get fitness test exercises for semester',
    parameters=[SemesterInSerializer],
    responses={
        status.HTTP_200_OK: FitnessTestExerciseSerializer(many=True),
    }
)
@api_view(["GET"])
def get_fitness_exercises(request):
    serializer = SemesterInSerializer(data=request.query_params)
    serializer.is_valid(raise_exception=True)
    semester_id = serializer.validated_data.get('semester_id', get_ongoing_semester())
    exercises = get_exercises_crud(semester_id)
    return Response(FitnessTestExerciseSerializer(exercises, many=True).data)


# ======================
# Session Endpoints  
# ======================
@extend_schema(
    methods=["GET"],
    description='Get fitness test sessions',
    parameters=[SemesterInSerializer],
    responses={
        status.HTTP_200_OK: FitnessTestSessionSerializer(many=True)
    }
)
@api_view(["GET"])
@permission_classes([IsTrainer | IsSuperUser])
def get_fitness_sessions(request):
    serializer = SemesterInSerializer(data=request.query_params)
    serializer.is_valid(raise_exception=True)
    semester_id = serializer.validated_data.get('semester_id')
    
    sessions = (FitnessTestSession.objects.all() if semester_id is None
               else FitnessTestSession.objects.filter(semester_id=semester_id))
               
    return Response(FitnessTestSessionSerializer(sessions, many=True).data)


@extend_schema(
    methods=["GET"],
    responses={
        status.HTTP_200_OK: FitnessTestSessionWithResult()
    }
)
@api_view(["GET"])
@permission_classes([IsTrainer | IsSuperUser])
def get_fitness_session_details(request, session_id):
    results_dict = defaultdict(list)
    for result in FitnessTestResult.objects.filter(session_id=session_id):
        results_dict[result.exercise.id].append(result)

    return Response(FitnessTestSessionWithResult({
        'session': FitnessTestSession.objects.get(id=session_id),
        'exercises': FitnessTestExercise.objects.filter(
            id__in=FitnessTestResult.objects.filter(
                session_id=session_id
            ).values_list('exercise').distinct()
        ),
        'results': results_dict
    }).data)


# ======================  
# Student Results
# ======================
@extend_schema(
    methods=["GET"],
    responses={
        status.HTTP_200_OK: FitnessTestStudentResult(many=True)
    }
)
@api_view(["GET"])
@permission_classes([IsStudent])
def get_student_fitness_results(request):
    student = request.user.student
    results = FitnessTestResult.objects.filter(student=student)
    
    if not results.exists():
        return Response(status=status.HTTP_404_NOT_FOUND)

    data = []
    for semester_data in results.values('exercise__semester_id', 'session__retake').distinct():
        semester_id = semester_data['exercise__semester_id']
        retake = semester_data['session__retake']
        semester = Semester.objects.get(id=semester_id)
        
        result_list = []
        total_score = 0
        passed_all = True
        
        for result in results.filter(exercise__semester_id=semester_id, session__retake=retake):
            score = get_score(student, result)
            max_score = get_max_score(student, result)
            
            result_list.append({
                'exercise': result.exercise.exercise_name,
                'unit': result.exercise.value_unit,
                'value': (result.value if result.exercise.select is None
                         else result.exercise.select.split(',')[result.value]),
                'score': score,
                'max_score': max_score,
            })
            
            passed_all = passed_all and score >= result.exercise.threshold
            total_score += score

        # Special case for current semester and medical group 0
        current_semester = (semester_id == get_ongoing_semester().id)
        medical_exempt = (student.medical_group == 0)
        
        passed = (passed_all and total_score >= semester.points_fitness_test
                 if not (current_semester and medical_exempt and result_list)
                 else True)

        data.append({
            'semester': semester.name,
            'retake': retake,
            'grade': passed,
            'total_score': total_score,
            'details': result_list,
        })

    return Response(data=data, status=status.HTTP_200_OK)


# ======================
# Result Submission
# ======================
class PostStudentExerciseResult(serializers.Serializer):
    result = serializers.CharField(default='ok')
    session_id = serializers.IntegerField()


@extend_schema(
    methods=["POST"],
    request=FitnessTestUpload(),
    responses={
        status.HTTP_200_OK: PostStudentExerciseResult(),
        status.HTTP_404_NOT_FOUND: NotFoundSerializer(),
        status.HTTP_400_BAD_REQUEST: ErrorSerializer(),
    },
)
@api_view(["POST"])
@permission_classes([IsTrainer | IsSuperUser])
def submit_fitness_results(request, session_id=None):
    if not request.user.has_perm('sport.change_fitness_test'):
        return Response(status=status.HTTP_403_FORBIDDEN)

    serializer = FitnessTestUpload(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        semester = Semester.objects.get(id=serializer.validated_data['semester_id'])
    except Semester.DoesNotExist:
        return Response(
            status=status.HTTP_404_NOT_FOUND,
            data=NotFoundSerializer({'detail': 'Semester not found'})
        )

    session = post_student_exercises_result_crud(
        semester,
        serializer.validated_data['retake'],
        serializer.validated_data['results'],
        session_id,
        request.user
    )
    return Response(PostStudentExerciseResult({'session_id': session}).data)


# ======================
# Student Suggestions
# ======================
@extend_schema(
    methods=["GET"],
    parameters=[SuggestionQueryFTSerializer],
    responses={
        status.HTTP_200_OK: SuggestionSerializer(many=True),
    }
)
@api_view(["GET"])
@permission_classes([IsTrainer | IsSuperUser])
def suggest_fitness_students(request):
    serializer = SuggestionQueryFTSerializer(data=request.query_params)
    serializer.is_valid(raise_exception=True)

    suggested_students = get_email_name_like_students(
        serializer.validated_data["term"],
        requirement=(~Q(fitnesstestresult__exercise__semester=get_ongoing_semester()))
    )

    return Response([{
        "value": f"{student['id']}_{student['full_name']}_"
                f"{student['email']}_{student['medical_group__name']}_"
                f"{student['gender']}",
        "label": f"{student['full_name']} ({student['email']})",
    } for student in suggested_students])