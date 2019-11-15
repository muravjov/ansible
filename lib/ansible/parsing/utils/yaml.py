# (c) 2012-2014, Michael DeHaan <michael.dehaan@gmail.com>
# Copyright: (c) 2017, Ansible Project
# Copyright: (c) 2018, Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import json

from yaml import YAMLError

from ansible.errors import AnsibleParserError
from ansible.errors.yaml_strings import YAML_SYNTAX_ERROR
from ansible.module_utils._text import to_native, to_text
from ansible.parsing.yaml.loader import AnsibleLoader
from ansible.parsing.yaml.objects import AnsibleBaseYAMLObject
from ansible.parsing.ajson import AnsibleJSONDecoder


__all__ = ('from_yaml',)


def _handle_error(json_exc, yaml_exc, file_name, show_content):
    '''
    Optionally constructs an object (AnsibleBaseYAMLObject) to encapsulate the
    file name/position where a YAML exception occurred, and raises an AnsibleParserError
    to display the syntax exception information.
    '''

    # if the YAML exception contains a problem mark, use it to construct
    # an object the error class can use to display the faulty line
    err_obj = None
    if hasattr(yaml_exc, 'problem_mark'):
        err_obj = AnsibleBaseYAMLObject()
        err_obj.ansible_pos = (file_name, yaml_exc.problem_mark.line + 1, yaml_exc.problem_mark.column + 1)

    err_msg = 'We were unable to read either as JSON nor YAML, these are the errors we got from each:\n' \
              'JSON: %s\n\n' % to_text(json_exc) + YAML_SYNTAX_ERROR % getattr(yaml_exc, 'problem', '')

    raise AnsibleParserError(to_native(err_msg), obj=err_obj, show_content=show_content, orig_exc=yaml_exc)


def _safe_load(stream, file_name=None, vault_secrets=None):
    ''' Implements yaml.safe_load(), except using our custom loader class. '''

    loader = AnsibleLoader(stream, file_name, vault_secrets)
    try:
        return loader.get_single_data()
    finally:
        try:
            loader.dispose()
        except AttributeError:
            pass  # older versions of yaml don't have dispose function, ignore


from ansible.utils.display import Display
display = Display()

import pprint
from ansible.parsing.vault import VaultLib, is_encrypted
from ansible.utils import pybook
import re

def from_yaml(data, file_name='<string>', show_content=True, vault_secrets=None, json_only=False):
    '''
    Creates a python datastructure from the given data, which can be either
    a JSON or YAML string.
    '''
    new_data = None

    try:
        # in case we have to deal with vaults
        AnsibleJSONDecoder.set_secrets(vault_secrets)

        # we first try to load this data as JSON.
        # Fixes issues with extra vars json strings not being parsed correctly by the yaml parser
        new_data = json.loads(data, cls=AnsibleJSONDecoder)
    except Exception as json_exc:

        if json_only:
            raise AnsibleParserError(to_native(json_exc), orig_exc=json_exc)

        # must not be JSON, let the rest try
        
        plain_data = data
        if is_encrypted(data):
            vault = VaultLib(vault_secrets=vault_secrets)
            plain_data = vault.decrypt(data)
        
        if re.match("#!.*python", plain_data):
            new_data = pybook.run_pybook(file_name)
        else:
            try:
                new_data = _safe_load(data, file_name=file_name, vault_secrets=vault_secrets)
            except YAMLError as yaml_exc:
                _handle_error(json_exc, yaml_exc, file_name, show_content)

    if display.verbosity >= 3:
        display.display("""Structure of file "%s":\n%s\n""" % (file_name, pprint.pformat(new_data)), color='yellow')

    return new_data
