from django.views.generic import RedirectView

from django.urls import path, re_path, register_converter
from drf_spectacular.views import SpectacularSwaggerView, SpectacularJSONAPIView, SpectacularYAMLAPIView

from api.views import (
    profile,
    enroll,
    group,
    training,
    attendance,
    calendar,
    reference,
    self_sport_report,
    fitness_test,
    measurement,
    semester,
    analytics,
    medical_groups,
)


class NegativeIntConverter:
    regex = '-?[0-9]+'

    def to_python(self, value):
        return int(value)

    def to_url(self, value):
        return '%d' % value
register_converter(NegativeIntConverter, 'negint')


urlpatterns = [
    # Student Profile
    path("students/me", profile.get_student_info),
    path("students/me/gender", profile.change_gender),
    path("students/me/qr-presence", profile.toggle_QR_presence),
    path("students/me/history/<int:semester_id>", profile.get_history),
    path("students/me/history-with-self/<int:semester_id>", profile.get_history_with_self),
    
    # Training Enrollment
    path("trainings/<int:training_id>/enrollments", enroll.enroll),  # POST - записаться
    path("trainings/<int:training_id>/enrollments", enroll.unenroll),  # DELETE - отписаться
    path("trainings/<int:training_id>/enrollments/by-trainer", enroll.unenroll_by_trainer),  # DELETE - отмена тренером
    
    # Sport Groups
    path("sport-groups/<int:group_id>", group.group_info_view),
    path("sport-groups/selection", group.select_sport),  # POST
    path("sports", group.sports_view),
    
    # Trainings
    path("trainings/<int:training_id>", training.training_info),
    path("trainings/<int:training_id>/check-ins", training.training_checkin),  # POST
    path("trainings/<int:training_id>/check-ins", training.training_cancel_checkin),  # DELETE
    
    # Attendance
    path("attendance/suggestions", attendance.suggest_student),
    path("trainings/<int:training_id>/grades", attendance.get_grades),
    path("trainings/<int:training_id>/grades.csv", attendance.get_grades_csv),
    path("sport-groups/<int:group_id>/attendance-report", attendance.get_last_attended_dates),
    path("trainings/<int:training_id>/attendance", attendance.mark_attendance),  # POST
    path("students/<int:student_id>/attendance/hours", attendance.get_student_hours_info),
    path("students/<int:student_id>/attendance/negative-hours", attendance.get_negative_hours_info),
    path("students/<int:student_id>/attendance/comparison", attendance.get_better_than_info),
    path("students/me/history/by-date", attendance.get_student_trainings_between_dates),
    
    # Calendar & Schedule
    path("sports/<negint:sport_id>/schedule", calendar.get_schedule),
    path("students/me/schedule", calendar.get_personal_schedule),
    
    # Medical References
    path("medical-references", reference.reference_upload),  # POST
    
    # Self-Sport Reports
    path("self-sport/reports", self_sport_report.self_sport_upload),  # POST
    path("self-sport/types", self_sport_report.get_self_sport_types),
    path("self-sport/strava-activities", self_sport_report.get_strava_activity_info),
    
    # Fitness Tests
    path("fitness-tests/results", fitness_test.get_result),
    path("fitness-tests/results", fitness_test.post_student_exercises_result),  # POST
    path("fitness-tests/sessions/<int:session_id>/results", fitness_test.post_student_exercises_result),  # POST
    path("fitness-tests/exercises", fitness_test.get_exercises),
    path("fitness-tests/sessions", fitness_test.get_sessions),
    path("fitness-tests/sessions/<int:session_id>", fitness_test.get_session_info),
    path("fitness-tests/suggestions", fitness_test.suggest_fitness_test_student),
    
    # Measurements
    path("measurements", measurement.post_student_measurement),  # POST
    path("measurements/results", measurement.get_results),
    path("measurements/history", measurement.get_measurements),
    
    # Semester
    path("semesters/current", semester.get_semester),
    
    # Analytics
    path("analytics/attendance", analytics.attendance_analytics),
    
    # Medical Groups
    path("medical-groups", medical_groups.medical_groups_view),
]

# API Documentation
urlpatterns += [
    path('openapi.json', SpectacularJSONAPIView.as_view(), name='schema'),
    path('openapi.yaml', SpectacularYAMLAPIView.as_view(), name='schema-yaml'),
    path('docs', SpectacularSwaggerView.as_view(url_name='schema'), name='schema-swagger-ui'),

    # Redirects for backward compatibility
    re_path(r'swagger(?P<format>\.json)$', RedirectView.as_view(url="/api/openapi.json"), name='redirect-to-schema'),
    re_path(r'swagger(?P<format>\.yaml)$', RedirectView.as_view(url="/api/openapi.yaml"), name='redirect-to-schema-yaml'),
    re_path(r'swagger/$', RedirectView.as_view(url="/api/docs"), name='redirect-to-schema-swagger'),
    re_path(r'redoc/$', RedirectView.as_view(url="/api/docs"), name='redirect-to-schema-swagger-from-redoc'),
]