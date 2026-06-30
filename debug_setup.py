import sys
import traceback

sys.path.insert(0, './')

try:
    import setup_answers
    setup_answers.main()
except Exception as e:
    print('CAUGHT EXCEPTION:', repr(e))
    traceback.print_exc()
