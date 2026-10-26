#!/usr/bin/env python3
"""Supply the Actions Wiki token to Git without putting it in the remote URL."""
import os
import sys

prompt = sys.argv[1].lower() if len(sys.argv) > 1 else ''
if 'username' in prompt:
    print('x-access-token')
else:
    print(os.environ['WIKI_PUSH_TOKEN'])
