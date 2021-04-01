# Super Simple Test Sequencer

## Install

```
pip install jot-iris
```

## Create new test sequence

This command creates new empty/template test sequence to test_definitions/ directory.

```
iris.py --create NAME_OF_TEST_SUITE
```

Modify the template at test_definitions/ to create your own sequence.

## Run sequence

```
super_simple_test_runner.py
```

## Test order

Order of the tests is defined on test_definition.py. In addition of the actual test each test case may also
define pre-, and post-tests. Pre-tests can be run on specific order, but post-tests are always triggered
right after the actual test.

TESTS = ["Second_pre", "First", "Second"]

Will run pre-test of Second test case on parallel with first test case. Order will be:
1. start pre_test of Second
2. pre_test of First
3. wait pre_test of First
4. run test of First
5. start post_test of First
6. wait pre_test of Second
7. run test of Second
8. run post_test of Second
9. wait post_test of First
10. wait post_test of Second

On the other hand without defining Second_pre, the order will be:
TESTS = ["first", "second"]

1. pre_test of First
2. wait pre_test of First
3. run test of First
4. start post_test of First
5. start pre_test of Second
6. wait pre_test of Second
7. run test of Second
8. run post_test of Second
9. wait post_test of First
10. wait post_test of Second



# More information

See video of the concept (in finnish):
https://youtu.be/x7MCSb7BLW4
