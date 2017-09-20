# Copyright 2014-2017 Canonical Limited.
#
# This file is part of charms.reactive.
#
# charms.reactive is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3 as
# published by the Free Software Foundation.
#
# charm-helpers is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with charm-helpers.  If not, see <http://www.gnu.org/licenses/>.

import sys
import mock
import tempfile
import unittest
from pathlib import Path

from charmhelpers.core import unitdata
from charms.reactive import context, Endpoint, is_flag_set, clear_flag
from charms.reactive.bus import discover, dispatch, Handler


class TestEndpoint(unittest.TestCase):
    def setUp(self):
        tests_dir = Path(__file__).parent

        tf = tempfile.NamedTemporaryFile(delete=False)
        tf.close()
        self.test_db = Path(tf.name)
        unitdata._KV = self.kv = unitdata.Storage(str(self.test_db))

        self.log_p = mock.patch('charmhelpers.core.hookenv.log')
        self.log_p.start()

        self.charm_dir = str(tests_dir / 'data')
        self.charm_dir_p = mock.patch('charmhelpers.core.hookenv.charm_dir')
        mcharm_dir = self.charm_dir_p.start()
        mcharm_dir.side_effect = lambda: self.charm_dir

        self.hook_name = 'upgrade-charm'
        self.hook_name_p = mock.patch('charmhelpers.core.hookenv.hook_name')
        mhook_name = self.hook_name_p.start()
        mhook_name.side_effect = lambda: self.hook_name

        self.local_unit_p = mock.patch('charmhelpers.core.hookenv.local_unit',
                                       mock.MagicMock(return_value='local/0'))
        self.local_unit_p.start()

        self.relations = {
            'test-endpoint': [
                {
                    'local/0': {'key': 'value'},
                    'unit/0': {'foo': 'yes'},
                    'unit/1': {},
                },
                {
                    'local/0': {},
                    'unit/0': {'bar': '[1, 2]'},
                    'unit/1': {'foo': 'no'},
                },
            ],
        }

        def _rel(rid):
            rn, ri = rid.split(':')
            return self.relations[rn][int(ri)]

        self.rel_ids_p = mock.patch('charmhelpers.core.hookenv.relation_ids')
        rel_ids_m = self.rel_ids_p.start()
        rel_ids_m.side_effect = lambda endpoint: [
            '{}:{}'.format(endpoint, i) for i in range(
                len(self.relations.get(endpoint, [])))]
        self.rel_units_p = mock.patch('charmhelpers.core.hookenv.related_units')
        rel_units_m = self.rel_units_p.start()
        rel_units_m.side_effect = lambda rid: [key for key in _rel(rid).keys()
                                               if not key.startswith('local')]
        self.rel_get_p = mock.patch('charmhelpers.core.hookenv.relation_get')
        rel_get_m = self.rel_get_p.start()
        rel_get_m.side_effect = lambda unit, rid: _rel(rid)[unit]

        self.rel_set_p = mock.patch('charmhelpers.core.hookenv.relation_set')
        self.relation_set = self.rel_set_p.start()

        self.data_changed_p = mock.patch('charms.reactive.altrelations.data_changed')
        self.data_changed = self.data_changed_p.start()

        self.atexit_p = mock.patch('charmhelpers.core.hookenv.atexit')
        self.atexit = self.atexit_p.start()

        self.sysm_p = mock.patch.dict(sys.modules)
        self.sysm_p.start()

        discover()

    def tearDown(self):
        self.log_p.stop()
        self.charm_dir_p.stop()
        self.hook_name_p.stop()
        self.local_unit_p.stop()
        self.rel_ids_p.stop()
        self.rel_units_p.stop()
        self.rel_get_p.stop()
        self.rel_set_p.stop()
        self.data_changed_p.stop()
        self.atexit_p.stop()
        self.test_db.unlink()
        self.sysm_p.stop()
        Handler._HANDLERS.clear()

    def test_from_name(self):
        ep = Endpoint.from_name('foo')
        self.assertIsInstance(ep, Endpoint)
        self.assertEqual(ep.relation_name, 'foo')
        assert not ep.joined

    def test_from_flag(self):
        self.assertIsNone(Endpoint.from_flag('foo'))
        self.assertIsNone(Endpoint.from_flag('foo.bar.qux'))

        ep = Endpoint.from_flag('relations.foo.qux')
        self.assertIsInstance(ep, Endpoint)
        self.assertEqual(ep.relation_name, 'foo')
        assert not ep.joined

    def test_startup(self):
        assert not is_flag_set('relations.test-endpoint.joined')
        assert not is_flag_set('relations.test-endpoint.changed')
        assert not is_flag_set('relations.test-endpoint.changed.foo')

        self.data_changed.return_value = True
        Endpoint._startup()
        assert context.endpoints.test_endpoint is not None
        assert context.endpoints.test_endpoint.relation_name == 'test-endpoint'
        assert context.endpoints.test_endpoint.joined
        assert is_flag_set('relations.test-endpoint.joined')
        assert is_flag_set('relations.test-endpoint.changed')
        assert is_flag_set('relations.test-endpoint.changed.foo')
        assert context.endpoints.test_endpoint2 is not None
        assert context.endpoints.test_endpoint2.relation_name == 'test-endpoint2'
        assert not context.endpoints.test_endpoint2.joined
        assert not is_flag_set('relations.test-endpoint2.joined')
        assert not is_flag_set('relations.test-endpoint2.changed')
        assert not is_flag_set('relations.test-endpoint2.changed.foo')
        self.assertEqual(self.atexit.call_args_list, [
            mock.call(context.endpoints.test_endpoint.relations[0]._flush_data),
            mock.call(context.endpoints.test_endpoint.relations[1]._flush_data),
        ])

        # already joined, not relation hook
        clear_flag('relations.test-endpoint.changed')
        clear_flag('relations.test-endpoint.changed.foo')
        Endpoint._startup()
        assert not is_flag_set('relations.test-endpoint.changed')
        assert not is_flag_set('relations.test-endpoint.changed.foo')

        # relation hook
        self.hook_name = 'test-endpoint-relation-joined'
        clear_flag('relations.test-endpoint.changed')
        clear_flag('relations.test-endpoint.changed.foo')
        Endpoint._startup()
        assert is_flag_set('relations.test-endpoint.changed')
        assert is_flag_set('relations.test-endpoint.changed.foo')

        # not already joined
        self.hook_name = 'upgrade-charm'
        clear_flag('relations.test-endpoint.joined')
        clear_flag('relations.test-endpoint.changed')
        clear_flag('relations.test-endpoint.changed.foo')
        Endpoint._startup()
        assert is_flag_set('relations.test-endpoint.changed')
        assert is_flag_set('relations.test-endpoint.changed.foo')

        # data not changed
        self.data_changed.return_value = False
        clear_flag('relations.test-endpoint.joined')
        clear_flag('relations.test-endpoint.changed')
        clear_flag('relations.test-endpoint.changed.foo')
        Endpoint._startup()
        assert not is_flag_set('relations.test-endpoint.changed')
        assert not is_flag_set('relations.test-endpoint.changed.foo')

    def test_collections(self):
        Endpoint._startup()
        tep = context.endpoints.test_endpoint

        self.assertEqual(len(tep.relations), 2)
        self.assertEqual(len(tep.relations[0].units), 2)
        self.assertEqual(len(tep.relations[1].units), 2)
        self.assertEqual(len(tep.all_units), 4)
        self.assertEqual([u.unit_name for r in tep.relations for u in r.units],
                         ['unit/0', 'unit/1', 'unit/0', 'unit/1'])
        self.assertEqual([u.unit_name for u in tep.all_units],
                         ['unit/0', 'unit/1', 'unit/0', 'unit/1'])

    def test_receive(self):
        Endpoint._startup()
        tep = context.endpoints.test_endpoint

        self.assertEqual(tep.all_units.receive, {'foo': 'yes',
                                                 'bar': '[1, 2]'})
        self.assertEqual(tep.all_units.json_receive, {'foo': 'yes',
                                                      'bar': [1, 2]})
        self.assertEqual(tep.relations[0].units.receive, {'foo': 'yes'})
        self.assertEqual(tep.relations[1].units.receive, {'foo': 'no',
                                                          'bar': '[1, 2]'})
        self.assertEqual(tep.relations[0].units.json_receive, {'foo': 'yes'})
        self.assertEqual(tep.relations[1].units.json_receive, {'foo': 'no',
                                                               'bar': [1, 2]})
        self.assertEqual(tep.relations[0].units[0].receive, {'foo': 'yes'})
        self.assertEqual(tep.relations[0].units[1].receive, {})
        self.assertEqual(tep.relations[1].units[0].receive, {'bar': '[1, 2]'})
        self.assertEqual(tep.relations[1].units[1].receive, {'foo': 'no'})
        self.assertEqual(tep.relations[0].units[0].json_receive, {'foo': 'yes'})
        self.assertEqual(tep.relations[0].units[1].json_receive, {})
        self.assertEqual(tep.relations[1].units[0].json_receive, {'bar': [1, 2]})
        self.assertEqual(tep.relations[1].units[1].json_receive, {'foo': 'no'})

        self.assertEqual(tep.all_units.receive['bar'], '[1, 2]')
        self.assertEqual(tep.all_units.receive.get('bar'), '[1, 2]')
        self.assertEqual(tep.all_units.json_receive['bar'], [1, 2])
        self.assertEqual(tep.all_units.json_receive.get('bar'), [1, 2])
        self.assertIsNone(tep.all_units.receive['none'])
        self.assertEqual(tep.all_units.receive.get('none', 'default'), 'default')
        self.assertIsNone(tep.all_units.json_receive['none'])
        self.assertEqual(tep.all_units.json_receive.get('none', 'default'), 'default')

        assert not tep.all_units.receive.writeable
        assert not tep.all_units.json_receive.writeable

        with self.assertRaises(ValueError):
            tep.all_units.receive['foo'] = 'nope'

        with self.assertRaises(ValueError):
            tep.relations[0].units.receive['foo'] = 'nope'

        with self.assertRaises(ValueError):
            tep.relations[0].units[0].receive['foo'] = 'nope'

        with self.assertRaises(ValueError):
            tep.all_units.json_receive['foo'] = 'nope'

        with self.assertRaises(ValueError):
            tep.relations[0].units.json_receive['foo'] = 'nope'

        with self.assertRaises(ValueError):
            tep.relations[0].units[0].json_receive['foo'] = 'nope'

    def test_send(self):
        Endpoint._startup()
        tep = context.endpoints.test_endpoint
        rel = tep.relations[0]

        self.assertEqual(rel.send, {'key': 'value'})
        rel._flush_data()
        assert not self.relation_set.called

        rel.send['key'] = 'new-value'
        rel._flush_data()
        self.relation_set.assert_called_once_with('test-endpoint:0', {'key': 'new-value'})

        self.relation_set.reset_mock()
        rel.json_send['key'] = {'new': 'complex'}
        rel._flush_data()
        self.relation_set.assert_called_once_with('test-endpoint:0', {'key': '{"new": "complex"}'})

    def test_handlers(self):
        Handler._HANDLERS = {k: h for k, h in Handler._HANDLERS.items()
                             if hasattr(h, '_action') and
                             h._action.__qualname__.startswith('TestAltRequires.')}
        assert Handler._HANDLERS
        preds = [h._predicates[0].args[0][0] for h in Handler.get_handlers()]
        for pred in preds:
            self.assertRegex(pred, r'^relations.test-endpoint.')

        self.data_changed.return_value = False
        Endpoint._startup()
        tep = context.endpoints.test_endpoint

        self.assertCountEqual(tep.invocations, [])
        dispatch()
        self.assertCountEqual(tep.invocations, [
            'joined: test-endpoint',
        ])

        tep.invocations.clear()
        clear_flag('relations.test-endpoint.joined')
        clear_flag('relations.test-endpoint.changed')
        clear_flag('relations.test-endpoint.changed.foo')
        clear_flag('relations.test-endpoint2.joined')
        clear_flag('relations.test-endpoint2.changed')
        clear_flag('relations.test-endpoint2.changed.foo')
        self.data_changed.return_value = True
        Endpoint._startup()
        dispatch()
        self.assertCountEqual(tep.invocations, [
            'joined: test-endpoint',
            'changed: test-endpoint',
            'changed.foo: test-endpoint',
        ])

        tep.invocations.clear()
        clear_flag('relations.test-endpoint.joined')
        clear_flag('relations.test-endpoint.changed')
        clear_flag('relations.test-endpoint.changed.foo')
        clear_flag('relations.test-endpoint2.joined')
        clear_flag('relations.test-endpoint2.changed')
        clear_flag('relations.test-endpoint2.changed.foo')
        self.relations['test-endpoint2'] = [
            {
                'unit/0': {'foo': 'yes'},
                'unit/1': {},
            },
            {
                'unit/0': {},
                'unit/1': {'foo': 'no'},
            },
        ]
        Endpoint._startup()
        dispatch()
        self.assertCountEqual(tep.invocations, [
            'joined: test-endpoint',
            'joined: test-endpoint2',
            'changed: test-endpoint',
            'changed: test-endpoint2',
            'changed.foo: test-endpoint',
            'changed.foo: test-endpoint2',
        ])