__all__ = [
    "LAMB_LOG_FORMAT_SIMPLE",
    "LAMB_LOG_FORMAT_PREFIXNO",
    "LAMB_LOG_FORMAT_VERBOSE",
    "LAMB_LOG_FORMAT_VERBOSE_PREFIXNO",
    "LAMB_LOG_FORMAT_CELERY_MAIN_SIMPLE",
    "LAMB_LOG_FORMAT_CELERY_TASK_SIMPLE",
    "LAMB_LOG_FORMAT_CELERY_MAIN_PREFIXNO",
    "LAMB_LOG_FORMAT_CELERY_TASK_PREFIXNO",
]

# api
LAMB_LOG_FORMAT_SIMPLE = (
    "[%(asctime)s, xray=%(xray)s, user_id=%(app_user_id)s: %(levelname)9s] %(message)s"  # noqa: E501
)
LAMB_LOG_FORMAT_PREFIXNO = "[%(asctime)s, xray=%(xray)s, user_id=%(app_user_id)s: %(levelname)9s, %(prefixno)04d, %(asctime)s-%(prefixno)04d] %(message)s"  # noqa: E501
LAMB_LOG_FORMAT_VERBOSE = "[%(asctime)s, xray=%(xray)s, user_id=%(app_user_id)s: %(levelname)9s, %(name)s:%(filename)s:%(lineno)4d]  %(message)s"  # noqa: E501
LAMB_LOG_FORMAT_VERBOSE_PREFIXNO = "[%(asctime)s, xray=%(xray)s, user_id=%(app_user_id)s: %(levelname)9s, %(name)s:%(filename)s:%(lineno)4d, %(prefixno)04d, %(asctime)s-%(prefixno)04d] %(message)s"  # noqa: E501

# celery
LAMB_LOG_FORMAT_CELERY_MAIN_SIMPLE = "[%(asctime)s: %(levelname)9s/%(processName)s] %(message)s"  # noqa: E501
LAMB_LOG_FORMAT_CELERY_TASK_SIMPLE = (
    "[%(asctime)s: %(levelname)9s/%(processName)s] Task %(task_name)s[%(task_id)s] %(message)s"  # noqa: E501
)
LAMB_LOG_FORMAT_CELERY_MAIN_PREFIXNO = "[%(asctime)s: %(levelname)9s/%(processName)s, %(prefixno)04d, %(asctime)s-%(prefixno)04d] %(message)s"  # noqa: E501
LAMB_LOG_FORMAT_CELERY_TASK_PREFIXNO = "[%(asctime)s: %(levelname)9s/%(processName)s] Task %(task_name)s[%(task_id)s, %(prefixno)04d, %(asctime)s-%(prefixno)04d] %(message)s"  # noqa: E501
