# -*- coding: utf-8; Mode: Python -*-
#
# Copyright 2012 Jeffrey Finkelstein <jefrey.finkelstein@gmail.com>
#
# This file is part of Flask-Restless.
#
# Flask-Restless is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by the
# Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
#
# Flask-Restless is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more
# details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Flask-Restless. If not, see <http://www.gnu.org/licenses/>.
"""Unit tests for SQLAlchemy models which have some validation functionality
and therefore raise validation errors when requests are made to write to the
database.

Validation is not provided by Flask-Restless itself, but it must capture
validation errors and return them to the client.

"""
import re

from unittest2 import TestSuite
from unittest2 import skipUnless

from flask import json

# for SAValidation package on pypi.python.org
try:
    import savalidation as _sav
    import savalidation.validators as sav
    has_savalidation = True
except:
    has_savalidation = False

from .helpers import setUpModule
from .helpers import tearDownModule
from .helpers import TestSupport

__all__ = ['SAVTest', 'SimpleValidationTest']

#: A regular expression for email addresses.
EMAIL_REGEX = re.compile("[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^"
                         "_`{|}~-]+)*@(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a"
                         "-z0-9](?:[a-z0-9-]*[a-z0-9])")

dumps = json.dumps
loads = json.loads


class SimpleValidationTest(TestSupport):
    """Tests for validation errors raised by the SQLAlchemy's simple built-in
    validation.

    For more information about this functionality, see the documentation for
    :func:`sqlalchemy.orm.validates`.

    """

    def setUp(self):
        """Create APIs for the validated models."""
        super(SimpleValidationTest, self).setUp()
        # for the sake of brevity...
        db = self.db

        class CoolValidationError(Exception):
            pass

        # create the validated class
        # NOTE: don't name this `Person`, as in models.Person
        class Test(db.Model):
            __tablename__ = 'test'
            id = db.Column(db.Integer, primary_key=True)
            name = db.Column(db.Unicode(30), nullable=False, index=True)
            email = db.Column(db.Unicode, nullable=False)
            age = db.Column(db.Integer, nullable=False)

            @db.validates('email')
            def validate_email(self, key, string):
                if len(EMAIL_REGEX.findall(string)) != 1:
                    exception = CoolValidationError()
                    exception.errors = dict(email=('Must be in valid email'
                                                   ' format'))
                    raise exception
                return string

            @db.validates('age')
            def validate_age(self, key, number):
                if not 0 <= number <= 150:
                    exception = CoolValidationError()
                    exception.errors = dict(age='Must be between 0 and 150')
                    raise exception
                return number

            @db.validates('name')
            def validate_name(self, key, string):
                if string is None:
                    exception = CoolValidationError()
                    exception.errors = dict(name='Must not be empty')
                    raise exception
                return string
        db.create_all()
        self.manager.create_api(Test, methods=['GET', 'POST', 'PATCH'],
                                validation_exceptions=[CoolValidationError])

    def test_validations(self):
        """Test SQLAlchemy's built-in simple validations."""
        # test posting a person with a badly formatted email field
        person = dict(name='Jeffrey', email='bogus!!!email', age=1)
        response = self.app.postj('/api/test', data=dumps(person))
        self.assertEqual(response.status_code, 400)
        data = loads(response.data)
        self.assertIn('validation_errors', data)
        errors = data['validation_errors']
        self.assertIn('email', errors)
        self.assertIn('format', errors['email'].lower())

        # posting a new person with valid email format should be fine
        person = dict(name='John', email='foo@example.com', age=1)
        response = self.app.postj('/api/test', data=dumps(person))
        self.assertEqual(response.status_code, 201)
        personid = loads(response.data)['id']

        # test patching a person to with badly formatted data
        person = dict(name='Jeffrey', email='bogus!!!email', age=24)
        response = self.app.patchj('/api/test/' + str(personid),
                                   data=dumps(person))
        self.assertIn('validation_errors', data)
        errors = data['validation_errors']
        self.assertIn('email', errors)
        self.assertIn('format', errors['email'].lower())

        # patching a person with correctly formatted fields should be fine
        person = dict(email='foo@example.com')
        response = self.app.patchj('/api/test/' + str(personid),
                                   data=dumps(person))
        data = loads(response.data)
        if 'validation_errors' in data and \
                'email' in data['validation_errors']:
            self.assertNotIn('format', errors['email'].lower())


class SAVTest(TestSupport):
    """Tests for validation errors raised by the ``savalidation`` package. For
    more information about this package, see `its PyPI page
    <http://pypi.python.org/pypi/SAValidation>`_.

    """

    def setUp(self):
        """Create APIs for the validated models."""
        super(SAVTest, self).setUp()
        # for the sake of brevity...
        db = self.db

        class Test(db.Model, _sav.ValidationMixin):
            __tablename__ = 'test'
            id = db.Column(db.Integer, primary_key=True)
            name = db.Column(db.Unicode(30))
            email = db.Column(db.Unicode)
            age = db.Column(db.Integer)

            sav.validates_presence_of('name', 'email')
            sav.validates_email('email')

        db.create_all()

        exceptions = [_sav.ValidationError]
        self.manager.create_api(Test, methods=['GET', 'POST', 'PATCH'],
                                validation_exceptions=exceptions)

    def test_format_validations(self):
        """Tests that errors from validators which check if fields match a
        format specified by a regular expression are correctly captured and
        returned to the client.

        """
        # test posting a person with a badly formatted email field
        person = dict(name='Jeffrey', email='bogus!!!email', age=1)
        response = self.app.postj('/api/test', data=dumps(person))
        self.assertEqual(response.status_code, 400)
        data = loads(response.data)
        self.assertIn('validation_errors', data)
        errors = data['validation_errors']
        self.assertIn('email', errors)
        self.assertIn('email address', errors['email'].lower())

        # posting a new person with valid email format should be fine
        person = dict(name='John', email='foo@example.com', age=1)
        response = self.app.postj('/api/test', data=dumps(person))
        self.assertEqual(response.status_code, 201)
        personid = loads(response.data)['id']

        # test patching a person to with badly formatted data
        person = dict(name='Jeffrey', email='bogus!!!email', age=24)
        response = self.app.patchj('/api/test/' + str(personid),
                                   data=dumps(person))
        self.assertIn('validation_errors', data)
        errors = data['validation_errors']
        self.assertIn('email', errors)
        self.assertIn('email address', errors['email'].lower())

        # patching a person with correctly formatted fields should be fine
        person = dict(email='foo@example.com')
        response = self.app.patchj('/api/test/' + str(personid),
                                   data=dumps(person))
        data = loads(response.data)
        if 'validation_errors' in data and \
                'email' in data['validation_errors']:
            self.assertNotIn('email address', errors['email'].lower())

    def test_presence_validations(self):
        """Tests that errors from validators which check for presence are
        correctly captured and returned to the client.

        """
        # missing required name field
        person = dict(email='example@example.com')
        response = self.app.postj('/api/test', data=dumps(person))
        self.assertEqual(response.status_code, 400)
        data = loads(response.data)
        self.assertIn('validation_errors', data)
        errors = data['validation_errors']
        self.assertIn('name', errors)
        self.assertIn('enter a value', errors['name'].lower())

        # missing required email field
        person = dict(name='Jeffrey')
        response = self.app.postj('/api/test', data=dumps(person))
        self.assertEqual(response.status_code, 400)
        data = loads(response.data)
        self.assertIn('validation_errors', data)
        errors = data['validation_errors']
        self.assertIn('email', errors)
        self.assertIn('enter a value', errors['email'].lower())

        # everything required is now provided
        person = dict(name='Jeffrey', email='example@example.com', age=24)
        response = self.app.postj('/api/test', data=dumps(person))
        self.assertEqual(response.status_code, 201)
        personid = loads(response.data)['id']

        # check that the provided field values are in there
        response = self.app.getj('/api/test/' + str(personid))
        self.assertEqual(response.status_code, 200)
        data = loads(response.data)
        self.assertEqual(data['name'], 'Jeffrey')
        self.assertEqual(data['email'], 'example@example.com')


# skipUnless should be used as a decorator, but Python 2.5 doesn't have
# decorators.
SAVTest = skipUnless(has_savalidation, 'savalidation not found.')(SAVTest)


def load_tests(loader, standard_tests, pattern):
    """Returns the test suite for this module."""
    suite = TestSuite()
    suite.addTest(loader.loadTestsFromTestCase(SimpleValidationTest))
    suite.addTest(loader.loadTestsFromTestCase(SAVTest))
    return suite