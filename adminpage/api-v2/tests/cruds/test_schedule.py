import unittest

import pytest
from datetime import time, date

from api.crud import get_sport_schedule, enroll_student
from sport.models import Schedule, Training, MedicalGroups

assertMembers = unittest.TestCase().assertCountEqual

@pytest.mark.django_db
def test_get_sport_schedule(
        student_factory,
        semester_factory,
        sport_factory,
        group_factory,
        training_class_factory,
        schedule_factory,
):
    student = student_factory("A@foo.bar").student
    start = date(2020, 1, 20)
    end = date(2020, 1, 27)
    sem = semester_factory(
        name="S20",
        start=start,
        end=end,
    )

    other_sport = sport_factory(
        name="sport",
        special=False,
    )

    sport = sport_factory(
        name="football",
        special=False,
    )

    group1 = group_factory(
        name="F-S20-01",
        capacity=30,
        sport=sport,
        semester=sem,
        allowed_medical_groups = [
            MedicalGroups.SPECIAL1,
        ]
    )

    group2 = group_factory(
        name="F-S20-02",
        capacity=30,
        sport=sport,
        semester=sem,
        allowed_medical_groups = [
            MedicalGroups.GENERAL,
        ]
    )

    schedule_start = time(14, 0, 0)
    schedule_end = time(18, 30, 0)
    training_class = training_class_factory('football field')
    schedule11 = schedule_factory(
        group=group1,
        weekday=Schedule.Weekday.MONDAY,
        start=schedule_start,
        end=schedule_end,
    )
    schedule12 = schedule_factory(
        group=group1,
        weekday=Schedule.Weekday.TUESDAY,
        start=schedule_start,
        end=schedule_end,
    )
    schedule21 = schedule_factory(
        group=group2,
        weekday=Schedule.Weekday.WEDNESDAY,
        start=schedule_start,
        end=schedule_end,
        training_class=training_class
    )
    schedule22 = schedule_factory(
        group=group2,
        weekday=Schedule.Weekday.THURSDAY,
        start=schedule_start,
        end=schedule_end,
    )

    assert get_sport_schedule(other_sport.pk) == []
    assert get_sport_schedule(other_sport.pk, student) == []
    assert get_sport_schedule(sport.pk, student) == []
    student.medical_group_id = MedicalGroups.SPECIAL1
    student.save()
    assertMembers(get_sport_schedule(sport.pk, student), [
        {
            'group_id': group1.pk,
            'group_name': group1.name,
            'current_load': 0,
            'capacity': group1.capacity,
            'weekday': schedule11.weekday,
            'start': schedule_start,
            'end': schedule_end,
            'training_class': None
        },
        {
            'group_id': group1.pk,
            'group_name': group1.name,
            'current_load': 0,
            'capacity': group1.capacity,
            'weekday': schedule12.weekday,
            'start': schedule_start,
            'end': schedule_end,
            'training_class': None
        }
    ])
    assert get_sport_schedule(other_sport.pk, student) == []
    student.medical_group_id = MedicalGroups.GENERAL
    student.save()
    enroll_student(group2, student)
    assertMembers(get_sport_schedule(sport.pk, student), [
        {
            'group_id': group2.pk,
            'group_name': group2.name,
            'current_load': 1,
            'capacity': group2.capacity,
            'weekday': schedule21.weekday,
            'start': schedule_start,
            'end': schedule_end,
            'training_class': training_class.name
        },
        {
            'group_id': group2.pk,
            'group_name': group2.name,
            'current_load': 1,
            'capacity': group2.capacity,
            'weekday': schedule22.weekday,
            'start': schedule_start,
            'end': schedule_end,
            'training_class': None
        }
    ])
