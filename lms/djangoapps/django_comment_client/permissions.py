from .models import Role, Permission
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from student.models import CourseEnrollment

import logging


@receiver(post_save, sender=CourseEnrollment)
def assign_default_role(sender, instance, **kwargs):
    if instance.user.is_staff:
        role = Role.objects.get(course_id=instance.course_id, name="Moderator")
    else:
        role = Role.objects.get(course_id=instance.course_id, name="Student")

    logging.info("assign_default_role: adding %s as %s" % (instance.user, role))
    instance.user.roles.add(role)

def has_permission(user, permission, course_id=None):
    # if user.permissions.filter(name=permission).exists():
    #     return True
    for role in user.roles.filter(course_id=course_id):
        if role.has_permission(permission):
            return True
    return False


CONDITIONS = ['is_open', 'is_author']
def check_condition(user, condition, course_id, data):
    def check_open(user, condition, course_id, data):
        try:
            return data and not data['content']['closed']
        except KeyError:
            return False

    def check_author(user, condition, course_id, data):
        try:
            return data and data['content']['user_id'] == str(user.id)
        except KeyError:
            return False

    handlers = {
        'is_open'      : check_open,
        'is_author'    : check_author,
    }

    return handlers[condition](user, condition, course_id, data)


def check_conditions_permissions(user, permissions, course_id, **kwargs):
    """
    Accepts a list of permissions and proceed if any of the permission is valid.
    Note that ["can_view", "can_edit"] will proceed if the user has either
    "can_view" or "can_edit" permission. To use AND operator in between, wrap them in 
    a list. 
    """

    def test(user, per, operator="or"):
        if isinstance(per, basestring):
            if per in CONDITIONS:
                return check_condition(user, per, course_id, kwargs)
            return has_permission(user, per, course_id=course_id)
        elif isinstance(per, list) and operator in ["and", "or"]:
            results = [test(user, x, operator="and") for x in per]
            if operator == "or":
                return True in results
            elif operator == "and":
                return not False in results

    return test(user, permissions, operator="or")


VIEW_PERMISSIONS = {
    'update_thread'     :       ['edit_content', ['update_thread', 'is_open', 'is_author']],
    'create_comment'    :       [["create_comment", "is_open"]],
    'delete_thread'     :       ['delete_thread'],
    'update_comment'    :       ['edit_content', ['update_comment', 'is_open', 'is_author']],
    'endorse_comment'   :       ['endorse_comment'],
    'openclose_thread'  :       ['openclose_thread'],
    'create_sub_comment':       [['create_sub_comment', 'is_open']],
    'delete_comment'    :       ['delete_comment'],
    'vote_for_comment'  :       [['vote', 'is_open']],
    'undo_vote_for_comment':    [['unvote', 'is_open']],
    'vote_for_thread'   :       [['vote', 'is_open']],
    'undo_vote_for_thread':     [['unvote', 'is_open']],
    'follow_thread'     :       ['follow_thread'],
    'follow_commentable':       ['follow_commentable'], 
    'follow_user'       :       ['follow_user'],
    'unfollow_thread'   :       ['unfollow_thread'],
    'unfollow_commentable':     ['unfollow_commentable'],
    'unfollow_user'     :       ['unfollow_user'],
    'create_thread'     :       ['create_thread'],
    'update_moderator_status' : ['manage_moderator'],
}


def check_permissions_by_view(user, course_id, content, name):
    # import pdb; pdb.set_trace()
    try:
        p = VIEW_PERMISSIONS[name]
    except KeyError:
        logging.warning("Permission for view named %s does not exist in permissions.py" % name)
    return check_conditions_permissions(user, p, course_id, content=content)
