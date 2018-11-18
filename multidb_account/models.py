import uuid
import os
from .education.models import *
from .promocode.models import *
from .help_center.models import *


def get_file_path(instance, filename, path=None):
    ext = filename.split('.')[-1]
    filename = "%s.%s" % (uuid.uuid4(), ext)
    return os.path.join(path or 'images/', filename)
