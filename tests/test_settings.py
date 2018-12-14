import os
ALLOWED_HOSTS = ['testserver']

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# collect verbose sqlalchemy log
LAMB_SQLALCHEMY_ECHO = False

SECRET_KEY = 'fake-key'
INSTALLED_APPS = [
    'lamb',
    'tests.images'
]

MIDDLEWARE = [
    'django.middleware.common.CommonMiddleware',
    'lamb.db.middleware.SQLAlchemyMiddleware',
    'lamb.rest.middleware.LambRestApiJsonMiddleware',
]

ROOT_URLCONF = 'tests.api.urls'

LAMB_SQLITE_TEST_DB = 'test.db'
LAMB_RESPONSE_OVERRIDE_STATUS_200 = False
LAMB_RESPONSE_APPLY_TO_APPS = [
    'tests',
]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': 'templates',
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

DATABASES = {
    'default': {
        'ENGINE':       'django.db.backends.postgresql',
        'NAME':         'test_db',
        'USER':         'postgres',
        'PASSWORD':     'postgres',
        'HOST':         'localhost',
        'CONNECT_OPTS': None,
    },
}

LAMB_STATIC_URL = '/static/'
LAMB_STATIC_FOLDER = os.path.join(BASE_DIR, 'static')

LAMB_AWS_ACCESS_KEY = 'test'
LAMB_AWS_SECRET_KEY = 'test'
LAMB_AWS_BUCKET_NAME = 'lamb_images'
LAMB_AWS_BUCKET_ZONE = 's3-ap-southeast-1'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'propagate': True,
            'level': 'WARNING'
        },
        'api': {
            'handlers': ['console'],
            'propagate': True,
            'level': 'DEBUG'
        },
        'lamb': {
            'handlers': ['console'],
            'propagate': True,
            'level': 'WARNING'
        },
        'py.warnings': {
            'handlers': ['console'],
            'propagate': True,
            'level': 'WARNING'
        }
    },
}

