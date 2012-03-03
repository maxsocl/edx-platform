import os.path

from lxml import etree

from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.auth.models import User

import mitxmako.middleware as middleware
from student.models import UserTestGroup

import random
import sys
import datetime

import json

middleware.MakoMiddleware()

def group_from_value(groups, v):
    ''' Given group: (('a',0.3),('b',0.4),('c',0.3)) And random value
    in [0,1], return the associated group (in the above case, return
    'a' if v<0.3, 'b' if 0.3<=v<0.7, and 'c' if v>0.7
'''
    sum = 0
    for (g,p) in groups:
        sum = sum + p
        if sum > v:
            return g
    return g # For round-off errors

class Command(BaseCommand):
    help =  \
''' Assign users to test groups. Takes a list
of groups: 
a:0.3,b:0.4,c:0.3 file.txt "Testing something"
Will assign each user to group a, b, or c with
probability 0.3, 0.4, 0.3. Probabilities must 
add up to 1. 

Will log what happened to file.txt.
'''
    def handle(self, *args, **options):
        if len(args) != 3:
            print "Invalid number of options"
            sys.exit(-1)

        # Extract groups from string
        group_strs = [x.split(':') for x in args[0].split(',')]
        groups = [(group,float(value)) for group,value in group_strs]
        print "Groups", groups

        ## Confirm group probabilities add up to 1
        total = sum(zip(*groups)[1])
        print "Total:", total
        if abs(total-1)>0.01:
            print "Total not 1"
            sys.exit(-1)

        ## Confirm groups don't already exist
        for group in dict(groups):
            if UserTestGroup.objects.filter(name=group).count() != 0:
                print group, "already exists!"
                sys.exit(-1)

        group_objects = {}

        ## Create groups
        for group in dict(groups):
            utg = UserTestGroup()
            utg.name=group
            utg.description = json.dumps({"description":args[2]}, 
                                         {"time":datetime.datetime.utcnow().isoformat()})
            group_objects[group]=utg
            group_objects[group].save()

        ## Assign groups
        users = list(User.objects.all())
        for user in users:
            v = random.uniform(0,1)
            group = group_from_value(groups,v)
            group_objects[group].users.add(user)

        ## Save groups
        for group in group_objects:
            group_objects[group].save()
