
TIMEOUT_SECS = 60
LOG_DATA = False

RW_SEPARATOR = ">>>>>>>>>>>>>>>>>>>> <<<<<<<<<<<<<<<<<<<<"

TARGET_HOST = 'some_target.com'

HostReplace = [
    [ 'undesired_target.net', TARGET_HOST ]
]


IrrelevantTags = [
    'envelope',
    'body',
    'header',
]

# SOAP enveloping fields that are more or less always present, or their
# presence simply means nothing, so there's no point including them in the
# output if the replay parser checks for qualifiers
GarbageQualifiers = [
    'envelope',
    'body',
]

UselessTagNames = [
    'id',
    'name',
    'string',
    'int',
]

CERT_FILE = "cert.pem"
