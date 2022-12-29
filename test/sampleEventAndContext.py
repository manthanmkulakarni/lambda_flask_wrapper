
event = {
	'resource': '/test',
	'path': '/test',
	'httpMethod': 'POST',
	'headers': {
		'accept': '*/*',
		'accept-encoding': 'gzip, deflate, br',
		'accept-language': 'en-IN,en-GB;q=0.9,en;q=0.8',
		'content-type': 'text/plain;charset=UTF-8',
		'Host': 'abcd.execute-api.us-east-1.amazonaws.com',
		'origin': 'https://abcd.lambda-url.us-east-1.on.aws',
		'referer': 'https://abcd.lambda-url.us-east-1.on.aws/',
		'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.5 Safari/605.1.15',
		'X-Amzn-Trace-Id': 'Root=1-62e2488a-1d6423047bc8451d3609b868',
		'X-Forwarded-For': '123.38.117.72',
		'X-Forwarded-Port': '443',
		'X-Forwarded-Proto': 'https'
	},
	'multiValueHeaders': {
		'accept': ['*/*'],
		'accept-encoding': ['gzip, deflate, br'],
		'accept-language': ['en-IN,en-GB;q=0.9,en;q=0.8'],
		'content-type': ['text/plain;charset=UTF-8'],
		'Host': ['abcd.execute-api.us-east-1.amazonaws.com'],
		'origin': ['https://abcd.lambda-url.us-east-1.on.aws'],
		'referer': ['https://abcd.lambda-url.us-east-1.on.aws/'],
		'User-Agent': ['Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.5 Safari/605.1.15'],
		'X-Amzn-Trace-Id': ['Root=1-62e2488a-1d6423047bc8451d3609b868'],
		'X-Forwarded-For': ['123.38.117.72'],
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
		'accountId': '123456789',
		'protocol': 'HTTP/1.1',
		'stage': 'dev',
		'domainPrefix': 'abcd',
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
		'domainName': 'abcd.execute-api.us-east-1.amazonaws.com',
		'apiId': 'abcd'
	},
	'body': '{"resource":"attachmentActions","body":{"card_payload":{"inputs":{"actionName":"product_input_card","defaultInputproduct":"route"}}}}',
	'isBase64Encoded': False
}


context = {
	'function_name': 'sample_test_endpoints',
	'function_version': '$LATEST',
	'invoked_function_arn': 'arn:aws:lambda:us-east-1:123456789:function:sample_test_endpoints',
	'memory_limit_in_mb': '1024',
	'aws_request_id': '57b32d64-f72f-4bc2-8767-7d3eb43d1655',
	'log_group_name': '/aws/lambda/sample_test_endpoints',
	'log_stream_name': '2022/07/28/[$LATEST]bab90777b69765aa868e7092c6d60e4706'
}