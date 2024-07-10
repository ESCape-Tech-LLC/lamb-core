LAMB_LOG_FORMAT_SIMPLE = "[%(asctime)s, xray=%(xray)s, user_id=%(app_user_id)s: %(levelname)9s] %(message)s"
LAMB_LOG_FORMAT_PREFIXNO = "[%(asctime)s, xray=%(xray)s, user_id=%(app_user_id)s: %(levelname)9s, %(prefixno)04d, %(asctime)s-%(prefixno)04d] %(message)s"
LAMB_LOG_FORMAT_VERBOSE = "[%(asctime)s, xray=%(xray)s, user_id=%(app_user_id)s: %(levelname)9s, %(name)s:%(filename)s:%(lineno)4d]  %(message)s"
LAMB_LOG_FORMAT_VERBOSE_PREFIXNO = "[%(asctime)s, xray=%(xray)s, user_id=%(app_user_id)s: %(levelname)9s, %(name)s:%(filename)s:%(lineno)4d, %(prefixno)04d, %(asctime)s-%(prefixno)04d] %(message)s"
