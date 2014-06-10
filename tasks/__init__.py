from __future__ import print_function
from invoke import Collection

ns = Collection()

from . import prereqs
from . import assets
from . import i18n
from . import servers
from . import docs
from . import tests
from . import js_test

ns.add_collection(prereqs)
ns.add_collection(i18n)
ns.add_collection(servers)
ns.add_collection(assets)
ns.add_collection(docs)
ns.add_collection(tests)
ns.add_collection(js_test)
