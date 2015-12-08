import json
import os
from shutil import rmtree
from tempfile import (
    NamedTemporaryFile,
    mkdtemp
)
from unittest import TestCase

from cloudweatherreport.reporter import Reporter


class TestReporter(TestCase):

    def test_generate_html(self):
        r = Reporter(None, None, None)
        with NamedTemporaryFile() as html_file:
            html_output = r.generate_html(
                json_content=self.make_json(), output_file=html_file.name,
                past_results=[])
            content = html_file.read()
        self.assertRegexpMatches(html_output, '1.55')
        self.assertRegexpMatches(html_output, '3.55')
        self.assertRegexpMatches(content, '1.55')
        self.assertRegexpMatches(content, '3.55')

    def test_generate_json(self):
        results = self.make_results()
        reporter = Reporter(bundle='git', results=results, options=None)
        with NamedTemporaryFile() as json_file:
            json_result = reporter.generate_json(output_file=json_file.name)
            json_result = json.loads(json_result)
            content = json_file.read()
        for result in json_result["results"]:
            self.assertItemsEqual(
                result.keys(),
                ['info', 'test_outcome', 'tests', 'provider_name'])
            self.assertIn(result["provider_name"], ['aws', 'joyent'])
            for test in result["tests"]:
                self.assertIn(
                    test["name"], ['charm-proof', '00-setup', '10-actions'])
                self.assertItemsEqual(
                    test.keys(),
                    ['duration', 'output', 'suite', 'name', 'result'])
        self.assertIn('"name": "charm-proof"', content)

    def test_generate(self):
        results = self.make_results()
        reporter = Reporter(bundle='git', results=results, options=None)
        with NamedTemporaryFile() as json_file:
            with NamedTemporaryFile() as html_file:
                reporter.generate(
                    html_filename=html_file.name, json_filename=json_file.name)
                json_content = json_file.read()
                html_content = html_file.read()
        json_content = json.loads(json_content)
        self.assertIn('charm-proof', html_content)
        self.assertEqual(json_content["bundle"]["name"], 'git')

    def test_get_test_outcome(self):
        r = Reporter(None, None, None)
        results = [r.pass_str, r.pass_str]
        self.assertEqual(r.get_test_outcome(results), r.all_passed_str)
        results = [r.pass_str, r.fail_str]
        self.assertEqual(r.get_test_outcome(results), r.some_failed_str)
        results = [r.fail_str, r.fail_str]
        self.assertEqual(r.get_test_outcome(results), r.all_failed_str)

    def test_get_past_test_results(self):
        temp = mkdtemp()
        files = [os.path.join(temp, 'git-2015-12-02T22:22:21-result.json'),
                 os.path.join(temp, 'git-2015-12-02T22:22:21-result.html'),
                 os.path.join(temp, 'git-2015-12-02T22:22:22-result.json'),
                 os.path.join(temp, 'foo-2015-12-02T22:22:23-result.json'),
                 os.path.join(temp, 'git-2015-12-02T22:22:25-result.json')]
        for f in files:
            with open(f, 'w') as fp:
                fp.write(self.make_json())
        r = Reporter('git', None, None)
        results, past_files = r.get_past_test_results(filename=files[0])
        self.assertItemsEqual(past_files, [files[2], files[4]])
        json_test_result = json.loads(self.make_json())
        self.assertItemsEqual(results, [json_test_result, json_test_result])
        rmtree(temp)

    def make_results(self):
        return [
            {
                'provider_name': 'aws',
                'info': {"name": "ec2"},
                'action_results': [{'repo': '/tmp/a'}, {'users': 'the dude'}],
                'test_results': {
                    'tests': [
                        {'returncode': 0,
                         'test': 'charm-proof',
                         'output': 'The dude abides.',
                         'duration': 1.55,
                         'suite': 'git',
                         },
                        {'returncode': 0,
                         'test': '00-setup',
                         'output': 'nice marmot.',
                         'duration': 2.55,
                         'suite': 'git'},
                        {'returncode': 1,
                         'test': '10-actions',
                         'output': 'Calm down your being very undude.',
                         'duration': 3.55,
                         'suite': 'git',
                         }
                    ],
                },
            },
            {
                'provider_name': 'joyent',
                'info': {"name": "joyent"},
                'action_results': [{'repo': '/tmp/a'}, {'users': 'the dude'}],
                'test_results': {
                    'tests': [
                        {'returncode': 0,
                         'test': 'charm-proof',
                         'output': 'foo',
                         'duration': 1,
                         'suite': 'git',
                         },
                        {'returncode': 0,
                         'test': '00-setup',
                         'output': 'foo',
                         'duration': 2,
                         'suite': 'git'},
                        {'returncode': 1,
                         'test': '10-actions',
                         'output': 'foo',
                         'duration': 3,
                         'suite': 'git',
                         }
                    ],
                },
            }]

    def make_json(self):
        return """{
            "version": 1,
            "date": "2015-12-02T22:22:22",
            "results": [
                {
                    "tests": [
                        {
                            "duration": 1.55,
                            "name": "charm-proof",
                            "result": "PASS"
                        },
                        {
                            "duration": 2.55,
                            "name": "00-setup",
                            "result": "PASS"
                        },
                        {
                            "duration": 3.55,
                            "name": "10-actions",
                            "result": "PASS"
                        }
                    ],
                    "provider_name": "Amazon Web Services",
                    "test_outcome": "All Passed",
                     "info": {
                        "ServerUUID": "0caecc18-b694-4e4c-81e7-a0551bcb7258",
                        "ProviderType": "ec2",
                        "UUID": "0caecc18-b694-4e4c-81e7-a0551bcb7258",
                        "DefaultSeries": "trusty",
                        "Name": "aws"
                    }
                },
                {
                    "tests": [
                        {
                            "duration": 1,
                            "name": "charm-proof",
                            "result": "PASS"
                        },
                        {
                            "duration": 2,
                            "name": "00-setup",
                            "result": "PASS"
                        },
                        {
                            "duration": 3,
                            "name": "10-actions",
                            "result": "FAIL"
                        }
                    ],
                    "provider_name": "Joyent",
                    "test_outcome": "Some Failed",
                    "info": {
                        "ServerUUID": "0caecc18-b694-4e4c-81e7-a0551bcb7258",
                        "ProviderType": "joyent",
                        "UUID": "0caecc18-b694-4e4c-81e7-a0551bcb7258",
                        "DefaultSeries": "trusty",
                        "Name": "joyent"
                    }
                }
            ],
            "bundle": {
                "services": null,
                "name": "git",
                "relations": null,
                "machines": null
            }
        }"""
