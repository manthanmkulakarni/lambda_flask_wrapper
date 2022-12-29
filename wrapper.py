import base64
import io
import json
import os
import sys
from werkzeug.datastructures import Headers, iter_multi_items, MultiDict
from werkzeug.wrappers import Response
from werkzeug.urls import url_encode, url_unquote, url_unquote_plus
from werkzeug.http import HTTP_STATUS_CODES


TEXT_MIME_TYPES = [
    "application/json",
    "application/javascript",
    "application/xml",
    "application/vnd.api+json",
    "image/svg+xml",
]


def get_response(app,event,context):
    environ = buildEnviron(event, context)

    response = Response.from_app(app, environ)
    print(response)
    return response

def get_body_bytes(event, body):
    if event.get("isBase64Encoded", False):
        body = base64.b64decode(body)
    if isinstance(body, str):
        body = body.encode("utf-8")
    return body

def encode_query_string(event):
    params = event.get("multiValueQueryStringParameters")
    if not params:
        params = event.get("queryStringParameters")
    if not params:
        params = event.get("query")
    if not params:
        params = ""
    if is_alb_event(event):
        params = MultiDict(
            (url_unquote_plus(k), url_unquote_plus(v))
            for k, v in iter_multi_items(params)
        )
    return url_encode(params)

def is_alb_event(event):
    return event.get("requestContext", {}).get("elb")

def get_script_name(headers, request_context):
    strip_stage_path = os.environ.get("STRIP_STAGE_PATH", "").lower().strip() in [
        "yes",
        "y",
        "true",
        "t",
        "1",
    ]

    if "amazonaws.com" in headers.get("Host", "") and not strip_stage_path:
        script_name = "/{}".format(request_context.get("stage", ""))
    else:
        script_name = ""
    return script_name

def group_headers(headers):
    new_headers = {}

    for key in headers.keys():
        new_headers[key] = headers.get_all(key)

    return new_headers

def all_casings(input_string):
    """
    Permute all casings of a given string.
    A pretty algoritm, via @Amber
    http://stackoverflow.com/questions/6792803/finding-all-possible-case-permutations-in-python
    """
    if not input_string:
        yield ""
    else:
        first = input_string[:1]
        if first.lower() == first.upper():
            for sub_casing in all_casings(input_string[1:]):
                yield first + sub_casing
        else:
            for sub_casing in all_casings(input_string[1:]):
                yield first.lower() + sub_casing
                yield first.upper() + sub_casing

def split_headers(headers):
    """
    If there are multiple occurrences of headers, create case-mutated variations
    in order to pass them through APIGW. This is a hack that's currently
    needed. See: https://github.com/logandk/serverless-wsgi/issues/11
    Source: https://github.com/Miserlou/Zappa/blob/master/zappa/middleware.py
    """
    new_headers = {}

    for key in headers.keys():
        values = headers.get_all(key)
        if len(values) > 1:
            for value, casing in zip(values, all_casings(key)):
                new_headers[casing] = value
        elif len(values) == 1:
            new_headers[key] = values[0]

    return new_headers

def generate_response(response, event):
    returndict = {"statusCode": response.status_code}

    if "multiValueHeaders" in event:
        returndict["multiValueHeaders"] = group_headers(response.headers)
    else:
        returndict["headers"] = split_headers(response.headers)

    if is_alb_event(event):
        # If the request comes from ALB we need to add a status description
        returndict["statusDescription"] = "%d %s" % (
            response.status_code,
            HTTP_STATUS_CODES[response.status_code],
        )

    if response.data:
        mimetype = response.mimetype or "text/plain"
        if (
            mimetype.startswith("text/") or mimetype in TEXT_MIME_TYPES
        ) and not response.headers.get("Content-Encoding", ""):
            returndict["body"] = response.get_data(as_text=True)
            returndict["isBase64Encoded"] = False
        else:
            returndict["body"] = base64.b64encode(response.data).decode("utf-8")
            returndict["isBase64Encoded"] = True

    return returndict

def contextObj2Dict(context_obj):
    context_dict = {
        "function_name":context_obj.function_name,
        "function_version":context_obj.function_version,
        "invoked_function_arn":context_obj.invoked_function_arn,
        "memory_limit_in_mb":context_obj.memory_limit_in_mb,
        "aws_request_id":context_obj.aws_request_id,
        "log_group_name":context_obj.log_group_name,
        "log_stream_name":context_obj.log_stream_name
    }
    return context_dict

def buildEnviron(event,context_obj):
    body = event.get("body", {})
    body = json.dumps(body) if body else ""
    body = get_body_bytes(event, body)

    context = contextObj2Dict(context_obj)
    

     

    if "multiValueHeaders" in event:
        headers = Headers(event["multiValueHeaders"])
    else:
        headers = Headers(event["headers"])

    script_name = get_script_name(headers, event)

    if "version" in event and event["version"] == "2.0":
        path_info = event["rawPath"]
        environ = {
            "CONTENT_LENGTH": str(len(body)),
            "CONTENT_TYPE": headers.get("Content-Type", ""),
            "PATH_INFO": url_unquote(path_info),
            "QUERY_STRING": event.get("rawQueryString", ""),
            "REMOTE_ADDR": event.get("requestContext", {})
            .get("http", {})
            .get("sourceIp", ""),
            "REMOTE_USER": event.get("requestContext", {})
            .get("authorizer", {})
            .get("principalId", ""),
            "REQUEST_METHOD": event.get("requestContext", {})
            .get("http", {})
            .get("method", ""),
            "SCRIPT_NAME": script_name,
            "SERVER_NAME": headers.get("Host", "lambda"),
            "SERVER_PORT": headers.get("X-Forwarded-Port", "80"),
            "SERVER_PROTOCOL": "HTTP/1.1",
            "wsgi.errors": sys.stderr,
            "wsgi.input": io.BytesIO(body),
            "wsgi.multiprocess": False,
            "wsgi.multithread": False,
            "wsgi.run_once": False,
            "wsgi.url_scheme": headers.get("X-Forwarded-Proto", "http"),
            "wsgi.version": (1, 0),
            "serverless.authorizer": event.get("requestContext", {}).get("authorizer"),
            "serverless.event": event,
            "serverless.context": context,
        }

    elif "version" in event and event["version"] == "1.0":
        path_info = event["path"]
        environ = {
            "CONTENT_LENGTH": str(len(body)),
            "CONTENT_TYPE": headers.get("Content-Type", ""),
            "PATH_INFO": url_unquote(path_info),
            "QUERY_STRING": encode_query_string(event),
            "REMOTE_ADDR": event.get("requestContext", {})
            .get("identity", {})
            .get("sourceIp", ""),
            "REMOTE_USER": event.get("requestContext", {})
            .get("authorizer", {})
            .get("principalId", ""),
            "REQUEST_METHOD": event.get("httpMethod", {}),
            "SCRIPT_NAME": script_name,
            "SERVER_NAME": headers.get("Host", "lambda"),
            "SERVER_PORT": headers.get("X-Forwarded-Port", "80"),
            "SERVER_PROTOCOL": "HTTP/1.1",
            "wsgi.errors": sys.stderr,
            "wsgi.input": io.BytesIO(body),
            "wsgi.multiprocess": False,
            "wsgi.multithread": False,
            "wsgi.run_once": False,
            "wsgi.url_scheme": headers.get("X-Forwarded-Proto", "http"),
            "wsgi.version": (1, 0),
            "serverless.authorizer": event.get("requestContext", {}).get("authorizer"),
            "serverless.event": event,
            "serverless.context": context,
        }
    else:
        path_info = event["path"]
        environ = {
            "CONTENT_LENGTH": str(len(body)),
            "CONTENT_TYPE": headers.get("Content-Type", ""),
            "PATH_INFO": url_unquote(path_info),
            "QUERY_STRING": encode_query_string(event),
            "REMOTE_ADDR": event.get("requestContext", {})
            .get("identity", {})
            .get("sourceIp", ""),
            "REMOTE_USER": event.get("requestContext", {})
            .get("authorizer", {})
            .get("principalId", ""),
            "REQUEST_METHOD": event.get("httpMethod", {}),
            "SCRIPT_NAME": script_name,
            "SERVER_NAME": headers.get("Host", "lambda"),
            "SERVER_PORT": headers.get("X-Forwarded-Port", "80"),
            "SERVER_PROTOCOL": "HTTP/1.1",
            "wsgi.errors": sys.stderr,
            "wsgi.input": io.BytesIO(body),
            "wsgi.multiprocess": False,
            "wsgi.multithread": False,
            "wsgi.run_once": False,
            "wsgi.url_scheme": headers.get("X-Forwarded-Proto", "http"),
            "wsgi.version": (1, 0),
            "serverless.authorizer": event.get("requestContext", {}).get("authorizer"),
            "serverless.event": event,
            "serverless.context": context,
        }

    return environ

#sample event and context object

event = {
	'resource': '/test',
	'path': '/test',
	'httpMethod': 'POST',
	'headers': {
		'accept': '*/*',
		'accept-encoding': 'gzip, deflate, br',
		'accept-language': 'en-IN,en-GB;q=0.9,en;q=0.8',
		'content-type': 'text/plain;charset=UTF-8',
		'Host': 'upta0b047e.execute-api.us-east-1.amazonaws.com',
		'origin': 'https://ysdgs5ydsijgallnwtzfn3p2hi0uprdo.lambda-url.us-east-1.on.aws',
		'referer': 'https://ysdgs5ydsijgallnwtzfn3p2hi0uprdo.lambda-url.us-east-1.on.aws/',
		'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.5 Safari/605.1.15',
		'X-Amzn-Trace-Id': 'Root=1-62e2488a-1d6423047bc8451d3609b868',
		'X-Forwarded-For': '173.38.117.72',
		'X-Forwarded-Port': '443',
		'X-Forwarded-Proto': 'https'
	},
	'multiValueHeaders': {
		'accept': ['*/*'],
		'accept-encoding': ['gzip, deflate, br'],
		'accept-language': ['en-IN,en-GB;q=0.9,en;q=0.8'],
		'content-type': ['text/plain;charset=UTF-8'],
		'Host': ['upta0b047e.execute-api.us-east-1.amazonaws.com'],
		'origin': ['https://ysdgs5ydsijgallnwtzfn3p2hi0uprdo.lambda-url.us-east-1.on.aws'],
		'referer': ['https://ysdgs5ydsijgallnwtzfn3p2hi0uprdo.lambda-url.us-east-1.on.aws/'],
		'User-Agent': ['Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.5 Safari/605.1.15'],
		'X-Amzn-Trace-Id': ['Root=1-62e2488a-1d6423047bc8451d3609b868'],
		'X-Forwarded-For': ['173.38.117.72'],
		'X-Forwarded-Port': ['443'],
		'X-Forwarded-Proto': ['https']
	},
	'queryStringParameters': None,
	'multiValueQueryStringParameters': None,
	'pathParameters': None,
	'stageVariables': None,
	'requestContext': {
		'resourceId': 'cgj1l3',
		'resourcePath': '/webclient/chathandler',
		'httpMethod': 'POST',
		'extendedRequestId': 'V-BFrGQAoAMFitw=',
		'requestTime': '28/Jul/2022:08:27:54 +0000',
		'path': '/dev/test',
		'accountId': '368590688524',
		'protocol': 'HTTP/1.1',
		'stage': 'dev',
		'domainPrefix': 'upta0b047e',
		'requestTimeEpoch': 1658996874507,
		'requestId': '0f0ad3b0-53b7-4db2-8e77-47112aab283f',
		'identity': {
			'cognitoIdentityPoolId': None,
			'accountId': None,
			'cognitoIdentityId': None,
			'caller': None,
			'sourceIp': '173.38.117.72',
			'principalOrgId': None,
			'accessKey': None,
			'cognitoAuthenticationType': None,
			'cognitoAuthenticationProvider': None,
			'userArn': None,
			'userAgent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.5 Safari/605.1.15',
			'user': None
		},
		'domainName': 'upta0b047e.execute-api.us-east-1.amazonaws.com',
		'apiId': 'upta0b047e'
	},
	'body': '{"resource":"attachmentActions","body":{"card_payload":{"inputs":{"actionName":"product_input_card","defaultInputproduct":"route"}}}}',
	'isBase64Encoded': False
}


context = {
	'function_name': 'influtive_test_endpoints',
	'function_version': '$LATEST',
	'invoked_function_arn': 'arn:aws:lambda:us-east-1:368590688524:function:influtive_test_endpoints',
	'memory_limit_in_mb': '1024',
	'aws_request_id': '57b32d64-f72f-4bc2-8767-7d3eb51d11c5',
	'log_group_name': '/aws/lambda/influtive_test_endpoints',
	'log_stream_name': '2022/07/28/[$LATEST]bab90777b69642868e7092c6d60e4706'
}