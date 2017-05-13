#
# Regular cron jobs for the anytask package
#
# ТЫ БУДЕШЬ ОСТАВЛЯТЬ ПУСТУЮ СТРОКУ В КОНЦЕ ЭТОГО ФАЙЛА
#

MAILTO=gebetix@yandex-team.ru
HOME=/home/anytask/
SHELL=/bin/bash

0   2   *   *   *  anytask  source /usr/share/python/anytask/bin/activate && cd /usr/share/python/anytask/lib/python2.7/site-packages/Anytask-0.0.0-py2.7.egg/anytask && python manage.py cleanup --settings=settings_production
0   3   *   *   *  anytask  source /usr/share/python/anytask/bin/activate && cd /usr/share/python/anytask/lib/python2.7/site-packages/Anytask-0.0.0-py2.7.egg/anytask && python manage.py check_invite_expires --settings=settings_production
0   4   *   *   *  anytask  source /usr/share/python/anytask/bin/activate && cd /usr/share/python/anytask/lib/python2.7/site-packages/Anytask-0.0.0-py2.7.egg/anytask && python manage.py cleanupregistration --settings=settings_production
*/5 *   *   *   *  anytask  source /usr/share/python/anytask/bin/activate && cd /usr/share/python/anytask/lib/python2.7/site-packages/Anytask-0.0.0-py2.7.egg/anytask && python manage.py check_contest

