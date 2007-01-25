#!/usr/bin/env python
#
# generator.py - A utility to prepopulate the database with some useful stuff.
#
# Copyright (C) 2007 David Trowbridge
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#

import sys, os
os.environ['DJANGO_SETTINGS_MODULE'] = 'reviewboard.settings'
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from reviewboard.reviews.models import Quip

def add_quips():
    def create_quip(**kwargs):
        (q, c) = Quip.objects.get_or_create(**kwargs)
        if c:
            q.save()


    create_quip(place='de',
                text='You have nothing to review. Time to party!')

    create_quip(place='dm',
                text='You worked hard on these review requests. Make sure people are giving them the attention they deserve.')

    create_quip(place='dg',
                text='These requests included a group of which you are a member.  Maybe if you wait long enough, someone else will do it.')

    create_quip(place='db',
                text='These requests asked for you by name.  Doh!  Better get cracking.')

if __name__ == '__main__':
    add_quips()
