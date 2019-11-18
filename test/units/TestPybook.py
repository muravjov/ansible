#!/usr/bin/env python
# coding: utf-8

import unittest
import yaml
from ansible.utils import pybook
import pprint

import io

def check_text(text, supposed_res):
    f = io.StringIO(text)
    res = pybook.run_pybook_file(f)
    
    assert res == supposed_res, pprint.pprint(res)

class TestPybook(unittest.TestCase):

    def test_list(self):
        text = u"""
with mapping:
    pass
"""
        check_text(text, [{}])

    def test_map(self):
        text = u"""
with sequence("key"):
    pass
"""
        check_text(text, {"key": []})

    def test_append(self):
        text = u"""
with sequence("key"):
    append(True)
"""
        check_text(text, {"key": [True]})

    def test_populate_yaml(self):
        text = u"""
populate_yaml('''
---
  - name: create user
    user: name=user shell=/bin/bash
''')
"""
        check_text(text, [{
            "name": "create user",
            "user": "name=user shell=/bin/bash"
        }])

    def test_when_mapping(self):
        text = u"""
with mapping:
    append("command", "cmd1")

with when("condition1"):
    with mapping:
        append("command", "cmd2")
        append("when",    "condition2")

with mapping:
    append("command", "cmd3")

"""
        check_text(text, [
            {'command': 'cmd1'},
            {'command': 'cmd2', 'when': '(condition1) and (condition2)'},
            {'command': 'cmd3'}
        ])

    def test_when_tasks(self):
        text = u"""
with mapping:
    append("hosts", "hosts")

    with tasks:
        with mapping:
            append("command", "cmd1")

    with when("condition1"):
        with tasks:
            with mapping:
                append("command", "cmd2")
                append("when",    "condition2")

        with handlers:
            with mapping:
                append("name", "reload")

    with tasks:
        with mapping:
            append("command", "cmd3")
"""
        check_text(text, [
            {'handlers': [{'name': 'reload', 'when': 'condition1'}],
             'hosts': 'hosts',
             'tasks': [{'command': 'cmd1'},
                       {'command': 'cmd2', 'when': '(condition1) and (condition2)'},
                       {'command': 'cmd3'}]}
        ])
