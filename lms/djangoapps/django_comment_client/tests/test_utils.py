import string
import random
import collections

from django.test import TestCase

import factory
from django.contrib.auth.models import User
from student.models import UserProfile, CourseEnrollment
from django_comment_client.models import Role, Permission

import django_comment_client.models as models
import django_comment_client.utils as utils

import xmodule.modulestore.django as django


class UserFactory(factory.Factory):
    FACTORY_FOR = User
    username = 'robot'
    password = '123456'
    email = 'robot@edx.org'
    is_active = True
    is_staff = False


class CourseEnrollmentFactory(factory.Factory):
    FACTORY_FOR = CourseEnrollment
    user = factory.SubFactory(UserFactory)
    course_id = 'edX/toy/2012_Fall'


class RoleFactory(factory.Factory):
    FACTORY_FOR = Role
    name = 'Student'
    course_id = 'edX/toy/2012_Fall'


class PermissionFactory(factory.Factory):
    FACTORY_FOR = Permission
    name = 'create_comment'


class DictionaryTestCase(TestCase):
    def test_extract(self):
        d = {'cats': 'meow', 'dogs': 'woof'}
        k = ['cats', 'dogs', 'hamsters']
        expected = {'cats': 'meow', 'dogs': 'woof', 'hamsters': None}
        self.assertEqual(utils.extract(d, k), expected)

    def test_strip_none(self):
        d = {'cats': 'meow', 'dogs': 'woof', 'hamsters': None}
        expected = {'cats': 'meow', 'dogs': 'woof'}
        self.assertEqual(utils.strip_none(d), expected)

    def test_strip_blank(self):
        d = {'cats': 'meow', 'dogs': 'woof', 'hamsters': ' ', 'yetis': ''}
        expected = {'cats': 'meow', 'dogs': 'woof'}
        self.assertEqual(utils.strip_blank(d), expected)

    def test_merge_dict(self):
        d1 = {'cats': 'meow', 'dogs': 'woof'}
        d2 = {'lions': 'roar', 'ducks': 'quack'}
        expected = {'cats': 'meow', 'dogs': 'woof', 'lions': 'roar', 'ducks': 'quack'}
        self.assertEqual(utils.merge_dict(d1, d2), expected)


class AccessUtilsTestCase(TestCase):
    def setUp(self):
        self.course_id = 'edX/toy/2012_Fall'
        self.student_role = RoleFactory(name='Student', course_id=self.course_id)
        self.moderator_role = RoleFactory(name='Moderator', course_id=self.course_id)
        self.student1 = UserFactory(username='student', email='student@edx.org')
        self.student1_enrollment = CourseEnrollmentFactory(user=self.student1)
        self.student_role.users.add(self.student1)
        self.student2 = UserFactory(username='student2', email='student2@edx.org')
        self.student2_enrollment = CourseEnrollmentFactory(user=self.student2)
        self.moderator = UserFactory(username='moderator', email='staff@edx.org', is_staff=True)
        self.moderator_enrollment = CourseEnrollmentFactory(user=self.moderator)
        self.moderator_role.users.add(self.moderator)

    def test_get_role_ids(self):
        ret = utils.get_role_ids(self.course_id)
        expected = {u'Moderator': [3], u'Student': [1, 2], 'Staff': [3]}
        self.assertEqual(ret, expected)

    def test_has_forum_access(self):
        ret = utils.has_forum_access('student', self.course_id, 'Student')
        self.assertTrue(ret)

        ret = utils.has_forum_access('not_a_student', self.course_id, 'Student')
        self.assertFalse(ret)

        ret = utils.has_forum_access('student', self.course_id, 'NotARole')
        self.assertFalse(ret)
