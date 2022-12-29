import base64
import io
import json
import os
import sys
from werkzeug.datastructures import Headers, iter_multi_items, MultiDict
from werkzeug.wrappers import Response
from werkzeug.urls import url_encode, url_unquote, url_unquote_plus
from werkzeug.http import HTTP_STATUS_CODES

class FlaskLambdaWrapper:
    def __init__(self):
        self.TEXT_MIME_TYPES = [
            "application/json",
            "application/javascript",
            "application/xml",
            "application/vnd.api+json",
            "image/svg+xml",
        ]



    @staticmethod
    def get_body_bytes(event, body):
        """
            Args:
            event (dict): event object used by AWS Lambda function
            body (str/byte): HTTP request body
        """
        if event.get("isBase64Encoded", False):
            body = base64.b64decode(body)
        if isinstance(body, str):
            body = body.encode("utf-8")
        return body

    @staticmethod
    def is_alb_event(event):
        """
            Args:
            event (dict): event object used by AWS Lambda function
        """
        return event.get("requestContext", {}).get("elb")

    @staticmethod
    def get_script_name(headers, request_context):
        """
            Args:
            headers (dict): HTTP header
            request_context (dict): context object used by AWS Lambda function
        """
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

    @staticmethod
    def group_headers(headers):
        """
            Args:
            headers (dict): HTTP header
        """
        new_headers = {}

        for key in headers.keys():
            new_headers[key] = headers.get_all(key)

        return new_headers

    @staticmethod
    def all_casings(input_string):
        """
            yeilds lower and upper case permutation of a given string 
            refer http://stackoverflow.com/questions/6792803/finding-all-possible-case-permutations-in-python

            Args:
            input_string (str): string of character whoes permutaion is to be generated
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

    @staticmethod
    def context_object_2_dict(context_obj):
        """
            Args:
            context_obj (dict): Lambda context object
        """
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
    
    @staticmethod
    def make_lambda_response(response):
        """
            Args:
            response (dict): Response Dictionary from generate_response method of this class
                             refer for more infomation https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html
        """

        if "multiValueHeaders" in response:
            return {
                "statusCode":response["statusCode"],
                "body":response["body"],
                "isBase64Encoded":response["isBase64Encoded"],
                "multiValueHeaders":response["multiValueHeaders"]
            }
            

        return {
            "statusCode":response["statusCode"],
            "body":response["body"],
            "isBase64Encoded":response["isBase64Encoded"],
            "headers":response["headers"]
        }
    
    def encode_query_string(self, event):
        """
            Args:
            event (dict): event object used by AWS Lambda function
        """
        params = event.get("multiValueQueryStringParameters")
        if not params:
            params = event.get("queryStringParameters")
        if not params:
            params = event.get("query")
        if not params:
            params = ""
        if self.is_alb_event(event):
            params = MultiDict(
                (url_unquote_plus(k), url_unquote_plus(v))
                for k, v in iter_multi_items(params)
            )
        return url_encode(params)

    def split_headers(self, headers):
        """
            Args:
            headers (dict): HTTP header
        """
        new_headers = {}

        for key in headers.keys():
            values = headers.get_all(key)
            if len(values) > 1:
                for value, casing in zip(values, self.all_casings(key)):
                    new_headers[casing] = value
            elif len(values) == 1:
                new_headers[key] = values[0]

        return new_headers

    def build_environ(self, event,context_obj):
        """
            Builds WSGI compatable environ dict object using AWS Lambda specific event and context_obj

            Args:
            event (dict): event object used by AWS Lambda function
            context (dict): context object used by AWS Lambda function

        """
        body = event.get("body", {})
        body = json.dumps(body) if body else ""
        body = self.get_body_bytes(event, body)

        context = self.context_object_2_dict(context_obj)
        

        

        if "multiValueHeaders" in event:
            headers = Headers(event["multiValueHeaders"])
        else:
            headers = Headers(event["headers"])

        script_name = self.get_script_name(headers, event)

        """
            AWS Lambda proxy payload format refer https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-develop-integrations-lambda.html
        """
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

    def generate_response(self, response, event):
        """
            This function build the response object that need to returned from Lambda function
            Args:
            response (dict): WSGI Response Object
            event (dict): Lambda event object
        """
        returndict = {"statusCode": response.status_code}

        if "multiValueHeaders" in event:
            returndict["multiValueHeaders"] = self.group_headers(response.headers)
        else:
            returndict["headers"] = self.split_headers(response.headers)

        if self.is_alb_event(event):
            # If the request comes from ALB we need to add a status description
            returndict["statusDescription"] = "%d %s" % (
                response.status_code,
                HTTP_STATUS_CODES[response.status_code],
            )

        if response.data:
            mimetype = response.mimetype or "text/plain"
            if (
                mimetype.startswith("text/") or mimetype in self.TEXT_MIME_TYPES
            ) and not response.headers.get("Content-Encoding", ""):
                returndict["body"] = response.get_data(as_text=True)
                returndict["isBase64Encoded"] = False
            else:
                returndict["body"] = base64.b64encode(response.data).decode("utf-8")
                returndict["isBase64Encoded"] = True

        return returndict

    def get_response(self, app, event, context):
        """
            This function builds the environment dict object used by WSGI and gets the flask response based on it

            Args:
            app (instance of Flask App)
            event (dict): event object used by AWS Lambda function
                          for more information on event object refer https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-concepts.html#gettingstarted-concepts-event
            context (dict): context object used by AWS Lambda function
                            for more infomation on context object refer https://docs.aws.amazon.com/lambda/latest/dg/python-context.html

        """
        environ = self.build_environ(event, context)
        response = Response.from_app(app, environ)
        return response


    def flask_lambda_listner(self, app, event, context):
        """
            This is the main method which is used to handle all the requests coming to AWS Lambda function

            Args:
            app (instance of Flask App)
            event (dict): event object used by AWS Lambda function
                          for more information on event object refer https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-concepts.html#gettingstarted-concepts-event
            context (dict): context object used by AWS Lambda function
                            for more infomation on context object refer https://docs.aws.amazon.com/lambda/latest/dg/python-context.html

        """

        # get response from flask endpoints
        res = self.get_response(app, event, context)
  
        res_dict = self.generate_response(res,event)

        return self.make_lambda_response(res_dict)
