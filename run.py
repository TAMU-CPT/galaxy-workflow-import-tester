#!/usr/bin/env python
import argparse
import re
from xunit import XUnitReportBuilder, Timer
import bioblend
from bioblend import galaxy


def our_workflows(gx, username):
    for wf in gx.workflows.get_workflows():
        if wf['owner'] == username:
            yield wf


def fetch_pub_ids(xunit, galaxy_url):
    url = galaxy_url.rstrip('/') + '/workflow/list_published'

    xunit.timedCommand('galaxy', 'fetch_ids', 'Download failed', 'ids.txt', [
        'curl', url,
        '|',
        'egrep', '-o', '\'encode_id": "[a-f0-9]+\'',
        '|',
        'sed',
        '\'s/encode_id": "//g\'',
        '>', 'ids.txt'
    ], shell=True, cache=False)

    with open('ids.txt', 'r') as handle:
        public_workflow_ids = [x.strip() for x in handle.readlines()]
    return public_workflow_ids


def clean_workflows(gx, username, xunit):
    # Clean out old workflows
    for wf in our_workflows(gx, username):
        try:
            with Timer() as t:
                gx.workflows.delete_workflow(wf['id'])
            xunit.ok('galaxy', 'delete_old_workflows.%s' % wf['id'], time=t.interval)
        except bioblend.ConnectionError as cbe:
            xunit.failure('galaxy', 'delete_old_workflows.%s' % wf['id'], 'Failed to remove previous workflow', errorDetails=str(cbe) + '\n' + wf['id'], time=t.interval)
    xunit.ok('galaxy', 'delete_old_workflows')


def import_workflows(gx, xunit, public_workflow_ids):
    # Now we can import all workflows
    for i in public_workflow_ids:
        try:
            with Timer() as t:
                gx.workflows.import_shared_workflow(i)
            xunit.ok('galaxy', 'import_workflow.%s' % i, time=t.interval)
        except Exception as e:
            xunit.failure('galaxy', 'import_workflow.%s' % i, "Failed to import workflow %s" % i, errorDetails=str(e), time=t.interval)
    xunit.ok('galaxy', 'import_workflow')


def main(galaxy_url, username, api_key):
    xunit = XUnitReportBuilder('workflow_checker')
    gx = galaxy.GalaxyInstance(galaxy_url, api_key)

    public_workflow_ids = fetch_pub_ids(xunit, galaxy_url)
    clean_workflows(gx, username, xunit)
    import_workflows(gx, xunit, public_workflow_ids)

    # With workflows imported, we can now try testing all of them
    for wf in our_workflows(gx, username):
        wf['name'] = wf['name'].replace('imported: ', '')
        wf_test_name_nice = 'check_validity.' + re.sub('^[A-Za-z0-9_-]', '', wf['name'].replace(' ', '_').replace('.', '-'))
        try:
            with Timer() as t:
                gx.workflows.export_workflow_json(wf['id'])
            xunit.ok('galaxy', wf_test_name_nice, time=t.interval)
        except bioblend.ConnectionError as cbe:
            message = None
            if 'Workflow cannot be exported due to missing tools.' in cbe.body:
                message = "Missing Tools in {name}"
            else:
                message = 'Other Error in {name}'

            message = message.format(**wf)

            xunit.failure('galaxy', wf_test_name_nice, message, errorDetails=str(cbe), time=t.interval)
    return xunit


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('galaxy_url')
    parser.add_argument('username')
    parser.add_argument('api_key')
    args = parser.parse_args()

    xunit = main(**vars(args))
    print(xunit.serialize())
