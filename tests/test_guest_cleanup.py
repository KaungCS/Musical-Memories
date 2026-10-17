import datetime
import unittest
from flask import Flask
from database import db
from models import (
    User, Entry, Calendar, CalendarMembership, Friendship, add_entry,
    get_or_create_user, get_or_create_personal_calendar, create_calendar,
    join_calendar_by_code, send_request, delete_user_data
)


class GuestCleanupTest(unittest.TestCase):
    def setUp(self):
        # in-memory so tearDown's drop_all never touches the real models.db
        self.app = Flask(__name__)
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        db.init_app(self.app)
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def add(self, user_id, calendar_id):
        add_entry(user=user_id, calendar=calendar_id, date=datetime.date(2026, 7, 9),
                  song='s', artist='a', link='l', song_image='i', location='x')

    def test_delete_user_data_removes_only_the_guest(self):
        get_or_create_user('guest_1', 'Guest')
        get_or_create_user('real', 'Real')
        guest_cal = get_or_create_personal_calendar('guest_1').id
        real_cal = get_or_create_personal_calendar('real').id

        shared = create_calendar('Shared', 'guest_1')
        shared_id = shared.id
        join_calendar_by_code('real', shared.join_code)
        self.add('guest_1', guest_cal)
        self.add('real', shared.id)   # lives in the guest's calendar, so it goes too
        self.add('real', real_cal)
        send_request('guest_1', 'real')

        delete_user_data('guest_1')

        self.assertIsNone(User.query.get('guest_1'))
        self.assertEqual(Calendar.query.filter_by(owner_id='guest_1').count(), 0)
        self.assertEqual(Entry.query.filter(Entry.calendar_id.in_([guest_cal, shared_id])).count(), 0)
        self.assertEqual(CalendarMembership.query.filter_by(calendar_id=shared_id).count(), 0)
        self.assertEqual(Friendship.query.count(), 0)
        self.assertIsNotNone(User.query.get('real'))
        self.assertEqual(Entry.query.filter_by(calendar_id=real_cal).count(), 1)


if __name__ == '__main__':
    unittest.main()
