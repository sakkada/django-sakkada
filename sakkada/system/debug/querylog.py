from django.db import connection
from django.conf import settings
import os, datetime, logging, pprint

def get_logger():
    logger = logging.getLogger('log_sql')
    logger.setLevel(logging.DEBUG)
    logger.propagate = 0

    filename = '%s/sql_queries.%s.log' % (settings.DEV_LOG_SQL_FILEPATH, datetime.datetime.now().strftime('%Y.%m.%d'))
    handler = None
    if len(logger.handlers):
        if not logger.handlers[0].stream.name == filename:
            logger.handlers[0].close()
            logger.removeHandler(logger.handlers[0])
            handler = True
    else:
        handler = True
    handler and logger.addHandler(logging.FileHandler(filename))

    return logger

class SqlPrintingMiddleware(object):
    """
    Middleware which prints out a list of all SQL queries done
    for each view that is processed.  This is only useful for debugging.
    """
    def process_response(self, request, response):
        
        if settings.DEBUG and not request.path.startswith(settings.MEDIA_URL) and len(connection.queries) > 0:
            logger = get_logger()
            total_time = 0.0
            message = []
            message.append("\n")
            message.append("\033[34mREQUEST PATH: %s\033[0m" % request.path.encode('utf8'))
            if request.GET:
                message.append("\033[34mREQUEST GET:  %s\033[0m" % (',\n              '.join([i.encode('utf8') + '=' + j.encode('utf8') for i,j in sorted(request.GET.items())])))
            if request.POST:
                message.append("\033[34mREQUEST POST: %s\033[0m" % (',\n              '.join([i.encode('utf8') + '=' + j.encode('utf8') for i,j in sorted(request.POST.items())])))
            for query in connection.queries:
                nice_sql = query['sql'].replace('"', '')
                try:
                    nice_sql = nice_sql.encode('utf8')
                except UnicodeDecodeError:
                    pass
                sql = "\033[31m[%s]\033[0m %s" % (query['time'], nice_sql)
                total_time = total_time + float(query['time'])
                message.append(sql)
            message.append("\033[32m[%s]\033[0m - TOTAL TIME" % total_time)
            logger.info('\n'.join([str(i) for i in message]))
        return response