#!/usr/bin/env python
import os
import time
import datetime
import logging
import subprocess

logging.basicConfig(level=logging.INFO)
log = logging.getLogger('dl')
NOW = datetime.datetime.now()
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))


class Timer:
    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, *args):
        self.end = time.time()
        self.interval = self.end - self.start


class XUnitReportBuilder(object):
    XUNIT_TPL = """<?xml version="1.0" encoding="UTF-8"?>
    <testsuite name="{suite_name}" tests="{total}" errors="{errors}" failures="{failures}" skip="{skips}">
{test_cases}
    </testsuite>
    """

    TESTCASE_TPL = """        <testcase classname="{classname}" name="{name}" {time}>
{error}
        </testcase>"""

    ERROR_TPL = """            <error type="{test_name}" message="{errorMessage}">{errorDetails}
            </error>"""

    def __init__(self, suite_name):
        self.xunit_data = {
            'total': 0, 'errors': 0, 'failures': 0, 'skips': 0
        }
        self.test_cases = []
        self.suite_name = suite_name

    def ok(self, classname, test_name, time=0):
        self.xunit_data['total'] += 1
        self.__add_test(test_name, classname, errors="", time=time)

    def error(self, classname, test_name, errorMessage, errorDetails="", time=0):
        self.xunit_data['total'] += 1
        self.__add_test(test_name, classname, errors=self.ERROR_TPL.format(
            errorMessage=errorMessage, errorDetails=errorDetails, test_name=test_name), time=time)

    def failure(self, classname, test_name, errorMessage, errorDetails="", time=0):
        self.xunit_data['total'] += 1
        self.__add_test(test_name, classname, errors=self.ERROR_TPL.format(
            errorMessage=errorMessage, errorDetails=errorDetails, test_name=test_name), time=time)

    def skip(self, classname, test_name, time=0):
        self.xunit_data['skips'] += 1
        self.xunit_data['total'] += 1
        self.__add_test(test_name, classname, errors="            <skipped />", time=time)

    def __add_test(self, name, classname, errors, time=0):
        t = 'time="%s"' % time
        self.test_cases.append(
            self.TESTCASE_TPL.format(name=name, error=errors, classname=classname, time=t))

    def serialize(self):
        self.xunit_data['test_cases'] = '\n'.join(self.test_cases)
        self.xunit_data['suite_name'] = self.suite_name
        return self.XUNIT_TPL.format(**self.xunit_data)

    def timedCommand(self, classname, testname, errormessage, test_file, command, shell=False, cwd=None, cache=True):
        if os.path.exists(test_file) and cache:
            self.skip(classname, testname)
        else:
            try:
                if not cwd:
                    cwd = SCRIPT_DIR
                with Timer() as t:
                    # If it's a shell command we automatically join things
                    # to make our timedCommand calls completely uniform
                    log.info(' '.join(command))
                    if shell:
                        command = ' '.join(command)

                    subprocess.check_call(command, shell=shell, cwd=cwd)
                self.ok(classname, testname, time=t.interval)
            except subprocess.CalledProcessError as cpe:
                self.failure(classname, testname, errormessage, errorDetails=str(cpe), time=t.interval)
