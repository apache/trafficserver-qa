'''
Import a unittest that will work
'''

import sys
if sys.version_info < (2, 7):
    try:
        from unittest2 import (
            TestLoader as TestLoader,
            TextTestRunner as TextTestRunner,
            TestCase as TestCase,
            expectedFailure,
            TestSuite as TestSuite,
            skip,
            skipIf,
            TestResult as TestResult,
            TextTestResult as TextTestResult
        )
        from unittest2.case import _id
        # pylint: enable=import-error
    except ImportError:
        raise SystemExit('You need to install unittest2 to run the tests')
else:
    from unittest import (
        TestLoader,
        TextTestRunner as TextTestRunner,
        TestCase as TestCase,
        expectedFailure,
        TestSuite,
        skip,
        skipIf,
        TestResult,
        TextTestResult
    )
    from unittest.case import _id
