from argparse import Namespace
import json
import os
from shutil import rmtree
from StringIO import StringIO
from tempfile import (
    NamedTemporaryFile,
    mkdtemp,
)
from unittest import TestCase

from mock import (
    call,
    MagicMock,
    patch,
)
import yaml

from cloudweatherreport import cloud_weather_report


class TestCloudWeatherReport(TestCase):

    def test_parse_args_defaults(self):
        args = cloud_weather_report.parse_args(['aws', 'test_plan'])
        expected = Namespace(
            bundle=None, controller=['aws'], deployment=None, dryrun=False,
            exclude=None, failfast=True, log_level='INFO',
            no_destroy=False, result_output='result.html',
            skip_implicit=False, test_pattern=None, test_plan='test_plan',
            testdir=os.getcwd(), tests_yaml=None, verbose=False)
        self.assertEqual(args, expected)

    def test_parse_args_set_all_options(self):
        args = cloud_weather_report.parse_args(
            ['aws', 'gce', 'test_plan', '--result-output', 'result',
             '--testdir', '/test/dir', '--bundle', 'foo-bundle',
             '--deployment', 'depl', '--no-destroy', '--log-level', 'debug',
             '--dry-run', '--verbose', '--allow-failure', '--skip-implicit',
             '--exclude', 'skip_test', '--tests-yaml', 'test_yaml_file',
             '--test-pattern', 'tp'])
        expected = Namespace(
            bundle='foo-bundle', controller=['aws', 'gce'], deployment='depl',
            dryrun=True, exclude=['skip_test'], failfast=False,
            log_level='debug', no_destroy=True, result_output='result',
            skip_implicit=True, test_pattern='tp', test_plan='test_plan',
            testdir='/test/dir', tests_yaml='test_yaml_file', verbose=True)
        self.assertEqual(args, expected)

    def test_run_bundle_test(self):
        io_output = StringIO()
        test_plan = self.make_tst_plan()
        args = Namespace()
        with patch(
                'cloudweatherreport.cloud_weather_report.StringIO',
                autospec=True, return_value=io_output) as mock_ntf:
            with patch('cloudweatherreport.cloud_weather_report.tester.main',
                       autospec=True, side_effect=self.fake_tester_main
                       ) as mock_tm:
                output = cloud_weather_report.run_bundle_test(
                    args, 'foo', test_plan)
        self.assertEqual(output, 'test passed')
        call = Namespace(environment='foo', output=io_output, reporter='json',
                         testdir='git', tests=['test1', 'test2'])
        mock_tm.assert_called_once_with(call)
        mock_ntf.assert_called_once_with()

    def test_run_bundle_test_no_test_plan(self):
        io_output = StringIO()
        test_plan = None
        args = Namespace(testdir=None)
        with patch(
                'cloudweatherreport.cloud_weather_report.StringIO',
                autospec=True, return_value=io_output) as mock_ntf:
            with patch('cloudweatherreport.cloud_weather_report.tester.main',
                       autospec=True, side_effect=self.fake_tester_main
                       ) as mock_tm:
                output = cloud_weather_report.run_bundle_test(
                    args, 'foo', test_plan)
        self.assertEqual(output, 'test passed')
        call = Namespace(environment='foo', output=io_output, reporter='json',
                         testdir=None, tests=None)
        mock_tm.assert_called_once_with(call)
        mock_ntf.assert_called_once_with()

    def test_main(self):
        run_bundle_test_p = patch(
            'cloudweatherreport.cloud_weather_report.run_bundle_test',
            autospec=True, return_value=self.make_results())
        juju_client_p = patch(
            'cloudweatherreport.cloud_weather_report.jujuclient',
            autospec=True)
        with NamedTemporaryFile() as html_output:
            with NamedTemporaryFile() as json_output:
                with NamedTemporaryFile() as test_plan_file:
                    test_plan = self.make_tst_plan_file(test_plan_file.name)
                    args = Namespace(controller=['aws'],
                                     result_output=html_output.name,
                                     test_plan=test_plan_file.name,
                                     testdir='git')
                    get_filenames_p = patch(
                        'cloudweatherreport.cloud_weather_report.'
                        'get_filenames', autospec=True, return_value=(
                            html_output.name, json_output.name))
                    with run_bundle_test_p as mock_rbt:
                        with get_filenames_p as mock_gf:
                            with juju_client_p as mock_jc:
                                (mock_jc.Environment.connect.return_value.
                                 info.return_value) = {"ProviderType": "ec2"}
                                cloud_weather_report.main(args)
                html_content = html_output.read()
                json_content = json.loads(json_output.read())
            self.assertRegexpMatches(html_content, '<title>git</title>')
            self.assertEqual(json_content["bundle"]["name"], 'git')
            self.assertEqual(json_content["results"][0]["provider_name"],
                             'Amazon Web Services')
        mock_rbt.assert_called_once_with(args=args, env='aws',
                                         test_plan=test_plan)
        mock_gf.assert_called_once_with('git')

    def test_main_multi_clouds(self):
        run_bundle_test_p = patch(
            'cloudweatherreport.cloud_weather_report.run_bundle_test',
            autospec=True, return_value=self.make_results())
        juju_client_p = patch(
            'cloudweatherreport.cloud_weather_report.jujuclient',
            autospec=True)
        with NamedTemporaryFile() as test_plan_file:
            with NamedTemporaryFile() as html_output:
                with NamedTemporaryFile() as json_output:
                    test_plan = self.make_tst_plan_file(test_plan_file.name)
                    args = Namespace(controller=['aws', 'gce'],
                                     result_output="result.html",
                                     test_plan=test_plan_file.name,
                                     testdir=None)
                    get_filenames_p = patch(
                        'cloudweatherreport.cloud_weather_report.'
                        'get_filenames', autospec=True, return_value=(
                            html_output.name, json_output.name))
                    with run_bundle_test_p as mock_rbt:
                        with get_filenames_p as mock_gf:
                            with juju_client_p as mock_jc:
                                (mock_jc.Environment.connect.return_value.
                                 info.return_value) = {"ProviderType": "ec2"}
                                cloud_weather_report.main(args)
                    json_content = json.loads(json_output.read())
        calls = [call(args=args, env='aws', test_plan=test_plan),
                 call(args=args, env='gce', test_plan=test_plan)]
        self.assertEqual(mock_rbt.mock_calls, calls)
        mock_gf.assert_called_once_with('git')
        self.assertEqual(json_content["bundle"]["name"], 'git')

    def test_run_actions(self):
        content = """
            tests:
                - foo-test
                - bar-test
            benchmark:
                unit_1:
                    - action1
                    - action2
                unit_2: action
            """
        test_plan = yaml.load(content)
        mock_client = MagicMock()
        with patch('cloudweatherreport.cloud_weather_report.run_action',
                   autospec=True, side_effect=[3, 2, 1]) as mock_cr:
            result = cloud_weather_report.run_actions(test_plan, mock_client)
        calls = [call(mock_client, 'unit_1', 'action1'),
                 call(mock_client, 'unit_1', 'action2'),
                 call(mock_client, 'unit_2', 'action')]
        self.assertEqual(mock_cr.mock_calls, calls)
        self.assertEqual(result, [3, 2, 1])

    def test_get_filenames(self):
        tempdir = mkdtemp()
        with patch('cloudweatherreport.cloud_weather_report.run_action'):
            h_file, j_file = cloud_weather_report.get_filenames('git')
        rmtree(tempdir)
        self.assertTrue(h_file.startswith('results/git-') and
                        h_file.endswith('.html'))
        self.assertTrue(j_file.startswith('results/git-') and
                        j_file.endswith('.json'))

    def fake_tester_main(self, args):
        args.output.write('test passed')

    def make_tst_plan_file(self, filename):
        test_plan = self.make_tst_plan()
        content = yaml.dump(test_plan)
        with open(filename, 'w') as yaml_file:
            yaml_file.write(content)
        return yaml.load(content)

    def make_tst_plan(self):
        return {'tests': ['test1', 'test2'], 'bundle': 'git'}

    def make_results(self):
        return """{
                    'tests': [
                        {'returncode': 0,
                         'test': 'charm-proof',
                         'output': 'foo',
                         'duration': 1.55,
                         'suite': 'git',
                         },
                        {'returncode': 0,
                         'test': '00-setup',
                         'output': 'foo',
                         'duration': 2.55,
                         'suite': 'git'},
                        {'returncode': 1,
                         'test': '10-actions',
                         'duration': 3.55,
                         'suite': 'git',
                         }
                    ],
            }"""
