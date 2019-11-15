#!/usr/bin/env python
# coding: utf-8

import yaml

block_stack = []

def calc_current_pair():
    current_object = block_stack[-1]
    is_seq = type(current_object) == list
    return current_object, is_seq
    

def append_impl(new_co, current_name, populate):
    if not block_stack:
        block_stack.append({} if current_name else [])
        
    current_object, is_seq = calc_current_pair()
    
    if is_seq:
        if populate:
            current_object.extend(new_co)
        else:
            current_object.append(new_co)
    else:
        if populate:
            current_object.update(new_co)
        else:
            current_object[current_name] = new_co

class Block:
    def __init__(self, is_sequence, append_name=None):
        self.is_sequence = is_sequence
        self.current_name = None
        self.append_name = append_name
        
    def __enter__(self):
        def make_new(name):
            new_co = [] if self.is_sequence else {}
            append_impl(new_co, name, False)
            return new_co
        
        if self.append_name:
            current_object, is_seq = calc_current_pair()
            assert not is_seq
            
            if self.append_name in current_object:
                new_co = current_object[self.append_name]
            else:
                new_co = make_new(self.append_name)
        else:
            new_co = make_new(self.current_name)
        
        block_stack.append(new_co)
        self.current_name = None

        return None
    
    def __exit__(self, type, value, traceback):
        if type:
            raise

        block_stack.pop()

        return True
    
    def __call__(self, name):
        self.current_name = name
        return self
    
class When:
    def __init__(self, condition):
        self.condition = condition
    
    def __enter__(self):
        current_object, is_seq = calc_current_pair()
        
        # :REFACTOR:
        new_co = [] if is_seq else {}
        block_stack.append(new_co)

        return None
    
    def __exit__(self, type, value, traceback):
        # :REFACTOR:
        if type:
            raise

        condition_block, is_seq = calc_current_pair()
        block_stack.pop()
        
        for item in condition_block:
            if is_seq:
                name = None
            else:
                name = item
                item = condition_block[item]

            if "when" in item:
                condition, nested_when = self.condition, item["when"]
                item["when"] = "(%(condition)s) and (%(nested_when)s)" % locals()
            else:
                item["when"] = self.condition
            append_impl(item, name, False)

        return True


mapping  = Block(False)
sequence = Block(True)

def make_custom_sequence(name):
    return Block(True, name)

tasks = make_custom_sequence("tasks")
handlers = make_custom_sequence("handlers")

def append_by_args(args, is_yaml, populate=False):
    ln = len(args)
    if ln == 1:
        current_name, new_co = None, args[0]
    else:
        current_name, new_co = args
        
    if is_yaml:
        new_co = yaml.load(new_co)
    append_impl(new_co, current_name, populate)
    

def append(*args):
    append_by_args(args, False)

def append_yaml(*args):
    append_by_args(args, True)

def populate_yaml(*args):
    append_by_args(args, True, populate=True)

book_globals = {
    "mapping":  mapping,
    "sequence": sequence,
    "append":   append,
    "append_yaml":   append_yaml,
    "populate_yaml": populate_yaml,
    "when": When,
    "tasks": tasks,
    "handlers": handlers,
}

#__all__ = book_globals.keys()

def run_pybook_file(f):
    # :TRICKY: supposed to be empty
    assert not block_stack

    exec(f.read(), book_globals)
    return block_stack.pop()

def run_pybook(fname):
    with open(fname) as f:
        return run_pybook_file(f)

def main():
    import sys
    fname = sys.argv[1]

    try:
        result = run_pybook(fname)
    except Exception as e:
        raise
    import pprint
    pprint.pprint(result)
    
if __name__ == '__main__':
    main()