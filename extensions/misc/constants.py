TRANSLATE_API = "https://clients5.google.com/translate_a/single"
TRANSLATE_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36"}

LANGUAGE_CODES = {
    "af",
    "sq",
    "am",
    "ar",
    "hy",
    "az",
    "eu",
    "be",
    "bn",
    "bs",
    "bg",
    "ca",
    "ceb",
    "ny",
    "zh-cn",
    "zh-tw",
    "co",
    "hr",
    "cs",
    "da",
    "nl",
    "en",
    "eo",
    "et",
    "tl",
    "fi",
    "fr",
    "fy",
    "gl",
    "ka",
    "de",
    "el",
    "gu",
    "ht",
    "ha",
    "haw",
    "iw",
    "he",
    "hi",
    "hmn",
    "hu",
    "is",
    "ig",
    "id",
    "ga",
    "it",
    "ja",
    "jw",
    "kn",
    "kk",
    "km",
    "ko",
    "ku",
    "ky",
    "lo",
    "la",
    "lv",
    "lt",
    "lb",
    "mk",
    "mg",
    "ms",
    "ml",
    "mt",
    "mi",
    "mr",
    "mn",
    "my",
    "ne",
    "no",
    "or",
    "ps",
    "fa",
    "pl",
    "pt",
    "pa",
    "ro",
    "ru",
    "sm",
    "gd",
    "sr",
    "st",
    "sn",
    "sd",
    "si",
    "sk",
    "sl",
    "so",
    "es",
    "su",
    "sw",
    "sv",
    "tg",
    "ta",
    "te",
    "th",
    "tr",
    "uk",
    "ur",
    "ug",
    "uz",
    "vi",
    "cy",
    "xh",
    "yi",
    "yo",
    "zu",
}

TRANSLATION_FLAG_MAP = {
    "\U0001f1ec\U0001f1e7": "en",
    "\U0001f3f4\U000e0067\U000e0062\U000e0065\U000e006e\U000e0067\U000e007f": "en",
    "\U0001f1ee\U0001f1f3": "hi",
}

HTTP_STATUS_CODES: dict[int, tuple[str, str]] = {
    100: (
        "Continue",
        "The server has received the request headers and the client should proceed to send the request body.",
    ),
    101: (
        "Switching Protocols",
        "The requester has asked the server to switch protocols and the server has agreed to do so.",
    ),
    102: (
        "Processing",
        "WebDAV: The server has received and is processing the request, but no response is available yet.",
    ),
    103: (
        "Early Hints",
        "Used to return some response headers (such as Link headers) before the final HTTP message.",
    ),
    110: (
        "Response is Stale",
        "HTTP Warning header code: The response provided by a cache is stale (RFC 7234).",
    ),
    111: (
        "Revalidation Failed",
        "HTTP Warning header code: The cache was unable to validate the response due to an inability to reach the origin server.",
    ),
    112: (
        "Disconnected Operation",
        "HTTP Warning header code: The cache is intentionally disconnected from the rest of the network.",
    ),
    113: (
        "Heuristic Expiration",
        "HTTP Warning header code: The cache heuristically chose a freshness lifetime greater than 24 hours.",
    ),
    199: (
        "Miscellaneous Warning",
        "HTTP Warning header code: Arbitrary, non-specific warning information.",
    ),
    200: (
        "OK",
        "Standard response for successful HTTP requests.",
    ),
    201: (
        "Created",
        "The request has been fulfilled, resulting in the creation of a new resource.",
    ),
    202: (
        "Accepted",
        "The request has been accepted for processing, but the processing has not been completed.",
    ),
    203: (
        "Non-Authoritative Information",
        "The server is a transforming proxy that received a 200 OK from its origin, but is returning a modified version of the origin's response.",
    ),
    204: (
        "No Content",
        "The server successfully processed the request, and is not returning any content.",
    ),
    205: (
        "Reset Content",
        "The server successfully processed the request, asks that the requester reset its document view, and is not returning any content.",
    ),
    206: (
        "Partial Content",
        "The server is delivering only part of the resource (byte serving) due to a range header sent by the client.",
    ),
    207: (
        "Multi-Status",
        "WebDAV: The message body that follows is by default an XML message and can contain a number of separate response codes.",
    ),
    208: (
        "Already Reported",
        "WebDAV: The members of a DAV binding have already been enumerated in a preceding part of the (multistatus) response.",
    ),
    214: (
        "Transformation Applied",
        "HTTP Warning header code: Added by a proxy if it applies any transformation to the representation, such as changing the content-encoding.",
    ),
    218: (
        "This is fine",
        "Apache HTTP Server catch-all error code allowing a reverse proxy to pass through error bodies.",
    ),
    226: (
        "IM Used",
        "The server has fulfilled a request for the resource, and the response is a representation of the result of one or more instance-manipulations applied to the current instance.",
    ),
    299: (
        "Miscellaneous Persistent Warning",
        "HTTP Warning header code: Arbitrary persistent warning information.",
    ),
    300: (
        "Multiple Choices",
        "Indicates multiple options for the resource from which the client may choose (via agent-driven content negotiation).",
    ),
    301: (
        "Moved Permanently",
        "This and all future requests should be directed to the given URI.",
    ),
    302: (
        "Found",
        "Tells the client to look at (browse to) another URL temporarily.",
    ),
    303: (
        "See Other",
        "The response to the request can be found under another URI using the GET method.",
    ),
    304: (
        "Not Modified",
        "Indicates that the resource has not been modified since the version specified by the request headers If-Modified-Since or If-None-Match.",
    ),
    305: (
        "Use Proxy",
        "The requested resource is available only through a proxy, the address for which is provided in the response (deprecated).",
    ),
    306: (
        "Switch Proxy",
        "No longer used. Originally meant 'Subsequent requests should use the specified proxy.'",
    ),
    307: (
        "Temporary Redirect",
        "The request should be repeated with another URI, but future requests should still use the original URI. Does not allow the HTTP method to change.",
    ),
    308: (
        "Permanent Redirect",
        "This and all future requests should be directed to the given URI. Does not allow the HTTP method to change.",
    ),
    400: (
        "Bad Request",
        "The server cannot or will not process the request due to an apparent client error (e.g., malformed request syntax).",
    ),
    401: (
        "Unauthorized",
        "Similar to 403 Forbidden, but specifically for use when authentication is required and has failed or has not yet been provided.",
    ),
    402: (
        "Payment Required",
        "Reserved for future use. Widely used by digital payment systems and APIs to indicate an overdue account or required subscription.",
    ),
    403: (
        "Forbidden",
        "The request contained valid data and was understood by the server, but the server is refusing action.",
    ),
    404: (
        "Not Found",
        "The requested resource could not be found but may be available in the future.",
    ),
    405: (
        "Method Not Allowed",
        "A request method is not supported for the requested resource (e.g., a GET request on a form that requires data to be presented via POST).",
    ),
    406: (
        "Not Acceptable",
        "The requested resource is capable of generating only content not acceptable according to the Accept headers sent in the request.",
    ),
    407: (
        "Proxy Authentication Required",
        "The client must first authenticate itself with the proxy.",
    ),
    408: (
        "Request Timeout",
        "The server timed out waiting for the request from the client.",
    ),
    409: (
        "Conflict",
        "Indicates that the request could not be processed because of conflict in the current state of the resource, such as an edit conflict.",
    ),
    410: (
        "Gone",
        "Indicates that the resource requested was previously in use but is no longer available and will not be available again.",
    ),
    411: (
        "Length Required",
        "The request did not specify the length of its content, which is required by the requested resource.",
    ),
    412: (
        "Precondition Failed",
        "The server does not meet one of the preconditions that the requester put on the request header fields.",
    ),
    413: (
        "Payload Too Large",
        "The request is larger than the server is willing or able to process.",
    ),
    414: (
        "URI Too Long",
        "The URI provided was too long for the server to process.",
    ),
    415: (
        "Unsupported Media Type",
        "The request entity has a media type which the server or resource does not support.",
    ),
    416: (
        "Range Not Satisfiable",
        "The client has asked for a portion of the file (byte serving), but the server cannot supply that portion.",
    ),
    417: (
        "Expectation Failed",
        "The server cannot meet the requirements of the Expect request-header field.",
    ),
    418: (
        "I'm a teapot",
        "The server refuses the attempt to brew coffee with a teapot (RFC 2324, Hyper Text Coffee Pot Control Protocol).",
    ),
    419: (
        "Page Expired",
        "Laravel Framework / unofficial code used when a CSRF token is missing or has expired.",
    ),
    420: (
        "Enhance Your Calm",
        "Returned by Twitter Search and Trends API v1 when the client is being rate limited, or by Spring Framework when a method fails.",
    ),
    421: (
        "Misdirected Request",
        "The request was directed at a server that is not able to produce a response (for example because of connection reuse in HTTP/2).",
    ),
    422: (
        "Unprocessable Content",
        "WebDAV / RFC 9110: The request was well-formed but was unable to be followed due to semantic errors.",
    ),
    423: (
        "Locked",
        "WebDAV: The resource that is being accessed is locked.",
    ),
    424: (
        "Failed Dependency",
        "WebDAV: The request failed because it depended on another request and that request failed.",
    ),
    425: (
        "Too Early",
        "Indicates that the server is unwilling to risk processing a request that might be replayed (RFC 8470).",
    ),
    426: (
        "Upgrade Required",
        "The client should switch to a different protocol such as TLS/1.3, given in the Upgrade header field.",
    ),
    428: (
        "Precondition Required",
        "The origin server requires the request to be conditional, intended to prevent the 'lost update' problem.",
    ),
    429: (
        "Too Many Requests",
        "The user has sent too many requests in a given amount of time ('rate limiting').",
    ),
    430: (
        "Request Header Fields Too Large / Shopify Security Rejection",
        "Used by Shopify as a deprecated alias for 429 Too Many Requests when too many URLs are requested at once.",
    ),
    431: (
        "Request Header Fields Too Large",
        "The server is unwilling to process the request because either an individual header field, or all the header fields collectively, are too large.",
    ),
    440: (
        "Login Time-out",
        "Microsoft IIS extension: The client's session has expired and must log in again.",
    ),
    444: (
        "No Response",
        "Nginx internal code used to instruct the server to return no information to the client and close the connection immediately.",
    ),
    449: (
        "Retry With",
        "Microsoft IIS extension: The request should be retried after performing the appropriate action.",
    ),
    450: (
        "Blocked by Windows Parental Controls",
        "Microsoft extension code indicated when Windows Parental Controls are turned on and are blocking access to the given webpage.",
    ),
    451: (
        "Unavailable For Legal Reasons",
        "A server operator has received a legal demand to deny access to a resource or to a set of resources that includes the requested resource.",
    ),
    460: (
        "Client Closed Connection Prematurely",
        "AWS Elastic Load Balancer code: Client closed the connection with the load balancer before the idle timeout period elapsed.",
    ),
    463: (
        "Too Many Forwarded IP Addresses",
        "AWS Elastic Load Balancer code: The load balancer received an X-Forwarded-For request header with more than 30 IP addresses.",
    ),
    464: (
        "Incompatible Protocol Versions",
        "AWS Elastic Load Balancer code: Incompatible protocol versions between Client and Origin server.",
    ),
    494: (
        "Request Header Too Large",
        "Nginx internal code similar to 431, indicating the client sent too large of a request or too long of a header line.",
    ),
    495: (
        "SSL Certificate Error",
        "Nginx internal code used when an error has occurred with the client's SSL certificate.",
    ),
    496: (
        "SSL Certificate Required",
        "Nginx internal code used when a client failed to provide a required SSL certificate.",
    ),
    497: (
        "HTTP Request Sent to HTTPS Port",
        "Nginx internal code used when a plain HTTP request was sent to an HTTPS port.",
    ),
    498: (
        "Invalid Token",
        "Returned by ArcGIS for Server when a token has expired or is otherwise invalid.",
    ),
    499: (
        "Client Closed Request / Token Required",
        "Nginx internal code used when the client closes the connection while Nginx is processing the request (or ArcGIS 'Token Required').",
    ),
    500: (
        "Internal Server Error",
        "A generic error message, given when an unexpected condition was encountered and no more specific message is suitable.",
    ),
    501: (
        "Not Implemented",
        "The server either does not recognize the request method, or it lacks the ability to fulfil the request.",
    ),
    502: (
        "Bad Gateway",
        "The server was acting as a gateway or proxy and received an invalid response from the upstream server.",
    ),
    503: (
        "Service Unavailable",
        "The server cannot handle the request (because it is overloaded or down for maintenance).",
    ),
    504: (
        "Gateway Timeout",
        "The server was acting as a gateway or proxy and did not receive a timely response from the upstream server.",
    ),
    505: (
        "HTTP Version Not Supported",
        "The server does not support the HTTP protocol version used in the request.",
    ),
    506: (
        "Variant Also Negotiates",
        "Transparent content negotiation for the request results in a circular reference (RFC 2295).",
    ),
    507: (
        "Insufficient Storage",
        "WebDAV: The server is unable to store the representation needed to complete the request.",
    ),
    508: (
        "Loop Detected",
        "WebDAV: The server detected an infinite loop while processing the request.",
    ),
    509: (
        "Bandwidth Limit Exceeded",
        "Apache / cPanel extension: The server has exceeded the bandwidth specified by the server administrator.",
    ),
    510: (
        "Not Extended",
        "Further extensions to the request are required for the server to fulfil it (RFC 2774).",
    ),
    511: (
        "Network Authentication Required",
        "The client needs to authenticate to gain network access (e.g., captive portals on public Wi-Fi).",
    ),
    520: (
        "Web Server Returned an Unknown Error",
        "Cloudflare error: The origin server returned an empty, unknown, or unexpected response to Cloudflare.",
    ),
    521: (
        "Web Server Is Down",
        "Cloudflare error: The origin server refused connections from Cloudflare.",
    ),
    522: (
        "Connection Timed Out",
        "Cloudflare error: Cloudflare timed out contacting the origin server.",
    ),
    523: (
        "Origin Is Unreachable",
        "Cloudflare error: Cloudflare could not reach the origin server (e.g., if the DNS records for the origin server are incorrect).",
    ),
    524: (
        "A Timeout Occurred",
        "Cloudflare error: Cloudflare was able to complete a TCP connection to the origin server, but did not receive a timely HTTP response.",
    ),
    525: (
        "SSL Handshake Failed",
        "Cloudflare error: Cloudflare could not negotiate a SSL/TLS handshake with the origin server.",
    ),
    526: (
        "Invalid SSL Certificate",
        "Cloudflare error: Cloudflare could not validate the SSL certificate on the origin web server.",
    ),
    527: (
        "Railgun Error",
        "Cloudflare error: An interrupted connection between Cloudflare and the origin server's Railgun server.",
    ),
    529: (
        "Site is Overloaded",
        "Used by Qualys in the SSLLabs server testing API to signal that the site can't process the request.",
    ),
    530: (
        "Site is Frozen / Origin DNS Error",
        "Used by the Pantheon web platform to indicate a site that has been frozen due to inactivity, or by Cloudflare for Origin DNS errors (1xxx).",
    ),
    561: (
        "Unauthorized (AWS ELB)",
        "AWS Elastic Load Balancer error: An error around authentication was returned by a server registered with a load balancer.",
    ),
    598: (
        "Network Read Timeout Error",
        "Informal convention used by some HTTP proxies to signal a network read timeout behind the proxy to a client in front of the proxy.",
    ),
    599: (
        "Network Connect Timeout Error",
        "Informal convention used by some HTTP proxies to signal a network connect timeout behind the proxy to a client in front of the proxy.",
    ),
}
