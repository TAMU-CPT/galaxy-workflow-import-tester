# Galaxy Published Workflow Tester

Simple python script which attempts to import + access all published workflows.

This tests for missing tools or other import errors that users could experience
and might cause them to have a negative impression of your Galaxy instance.

## Usage

```console
$ python run.py $GALAXY_URL $USER_NAME $API_KEY > report.xml
```

For your convenience as an admin, this tool produces an XUnit report that is
compatible with Jenkins.
