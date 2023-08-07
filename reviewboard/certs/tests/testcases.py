"""Test case support for reviewboard.certs.

Version Added:
    6.0
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import Encoding
from cryptography.x509.oid import NameOID
from typing_extensions import Final

from reviewboard.testing import TestCase


TEST_CERT_PEM = b"""
Junk...

-----BEGIN CERTIFICATE-----
MIIEMTCCAxmgAwIBAgIUINE3GHxmshQ/dNCYst/vdY1A1FQwDQYJKoZIhvcNAQEL
BQAwgacxCzAJBgNVBAYTAlVTMRMwEQYDVQQIDApDYWxpZm9ybmlhMRIwEAYDVQQH
DAlQYWxvIEFsdG8xFjAUBgNVBAoMDUJlYW5iYWcsIEluYy4xHTAbBgNVBAsMFFNh
bXBsZSBEb2N1bWVudGF0aW9uMRQwEgYDVQQDDAtleGFtcGxlLmNvbTEiMCAGCSqG
SIb3DQEJARYTc3VwcG9ydEBleGFtcGxlLmNvbTAeFw0yMzA3MTQwNzUwMzBaFw0y
NDA3MTMwNzUwMzBaMIGnMQswCQYDVQQGEwJVUzETMBEGA1UECAwKQ2FsaWZvcm5p
YTESMBAGA1UEBwwJUGFsbyBBbHRvMRYwFAYDVQQKDA1CZWFuYmFnLCBJbmMuMR0w
GwYDVQQLDBRTYW1wbGUgRG9jdW1lbnRhdGlvbjEUMBIGA1UEAwwLZXhhbXBsZS5j
b20xIjAgBgkqhkiG9w0BCQEWE3N1cHBvcnRAZXhhbXBsZS5jb20wggEiMA0GCSqG
SIb3DQEBAQUAA4IBDwAwggEKAoIBAQCx3i72hGP0QiEFjz7D0RUKQdvGsS+8VRan
k/35rMgkfOMNDhOrMUuEViC5RsKUPu8d+8nDKXuKdhWvtIKUHjeXeSvTn7/aDZh9
vt1hxW/lXc9qornncLIgKyJ6rPUeO/Nt5W9nNDTHQO4KOymHmxR48dURT+O2Eluw
rXHcRNSQy3yzT+2KOlHyeUc+rXgKMwbKkm5kD6VSqYBgibcvJ27DZXiPoFRfP7cT
TJC9fcFhsOZKN2H1yYH2yEIMXe6gpxVQ9fEJpv5qlnAs9UneusIXEEfvGomTxpem
M2Y2Vc/KCq0rhBUFPUpQH4yfj79/dxTJPOdKlVapbDpScsPxp8WrAgMBAAGjUzBR
MB0GA1UdDgQWBBSb8YQ1CsPdeenp4A7LCpzyDtC/NTAfBgNVHSMEGDAWgBSb8YQ1
CsPdeenp4A7LCpzyDtC/NTAPBgNVHRMBAf8EBTADAQH/MA0GCSqGSIb3DQEBCwUA
A4IBAQAZ8oXMDH19AKg2uh/4NJtZJA5mRNUCv368R1EiNgw7dqQm6fhkCZCNu1z3
ISEHy2kFeiG+gEDGELOBW/vZrbzPCy0J3I0GobKBlbASEwi21wjQwP0e+tH90h0g
eH1z1ftbAuy06osMFoYcH81+Nb8B9cRVVxgVF/+S2jMUbO3lCAnuyxijH5ShGIt/
fXYd2Fc6Mzk0+krk3+IxluV2O8Pffx8+7zcwUgeDNalNcD6/xjRWkXzD8SuD5nUX
e8K8nyAoCVl6E0HJL7cKdQ9/SkCivQjCO5jK+s8ANOeBNDUSATgQvep9VAk8UWo+
17dcTQ+tCBoxo1eKt5zewpzlYYBV
-----END CERTIFICATE-----

More junk...
"""

TEST_KEY_PEM = b"""
Junk...

-----BEGIN PRIVATE KEY-----
MIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQCx3i72hGP0QiEF
jz7D0RUKQdvGsS+8VRank/35rMgkfOMNDhOrMUuEViC5RsKUPu8d+8nDKXuKdhWv
tIKUHjeXeSvTn7/aDZh9vt1hxW/lXc9qornncLIgKyJ6rPUeO/Nt5W9nNDTHQO4K
OymHmxR48dURT+O2EluwrXHcRNSQy3yzT+2KOlHyeUc+rXgKMwbKkm5kD6VSqYBg
ibcvJ27DZXiPoFRfP7cTTJC9fcFhsOZKN2H1yYH2yEIMXe6gpxVQ9fEJpv5qlnAs
9UneusIXEEfvGomTxpemM2Y2Vc/KCq0rhBUFPUpQH4yfj79/dxTJPOdKlVapbDpS
csPxp8WrAgMBAAECggEABFvTfssDwAqW0JIQEbBf+Z5fimDxMIZNRdIEmUe4p9w/
nCRKKxnMJfQOXTv0rLlWFsAC07uCgYQfR+z+fi63YgjgIBF8HBXVNM+mkSzLby17
VbujHp7OXqdv8t2mLBWAA6NptXe8C1319143yFDukYArnn78r4uHn67AaYtuQhYP
7zsIO5fa0GRLy4HJvOkT4A73P1HLjdM6Sqhaj/mjltivxkFZ1gXmrPHvVJ3mtYfR
qSBPSG/2RJFjbTsY73yw+MYntl+rwlB2Lk7lSOS1Lqqqvg3h4Jefqd5Yq3JwQ5at
XLHMAX8yaNrIHvWhoFa6i4UZh60p0tyRdCoeNKCiEQKBgQC76hDqoocw6PxMwSlC
Pn4aVIGUaYR3pmMpZKjNX8MfVBN778pc9N3kc7KsdChjbofugN0VBbR4wkBun9wN
kniUpvn/TmYkDMuHeVGU0h/ky8SZ9wiTMVyCV/pVQ4Udec5HxAq2pr9G+du0VMTl
95cL5HRbZNKs0ITtku1e67bh/wKBgQDyUEPhAxpbVsfeJelkOtbpF5DNf/Th26br
PwsereKgVXP/+yc/PxENyURogJvuI9paJX3xAMfF2l0bX/2MeqJ5aq5lsSZe/cwa
8zqRDtZ4A5axXGTcze5Yp3yRJA2iXm6dnSrUwhYZAekmHyfY5d2piBFipeOUe8AJ
XRQo+BlEVQKBgFg0NCCOjXqNwe+dM2qevr5JMFGjfcRT23PQhdNwwbvw0Px5v7kG
TykujY2ZMGQLu85dumhltyJ/u5Kxgq70M5lDD1GhURxWzSoX7g023DWe1/eVFvdQ
UiX0edKP0OnXBNZ21LiLaHk+SrxIleuD3eh9IYjMuH7ZmauSLc1CQyOtAoGAO6kX
jWc+Lg8H1uJuvIbgMzPiKza+DH4QcwtqqXsWuXNQxE4KM8BLaqGLfk9sFQ4uzNM+
VwBiL4y8L+lKfDQVnN9vYQpk8C58+oW4fc6xb4sypyigjN0HOjzCptnBoaCui5AO
46OF3VJjHUe+f+DY2sztuuQtTHnLpoKMXCn5zqECgYA2Tfl2W6b1CM2WE19AAOpF
8yN2IJOgVgkkI/dt0qJvr3Kc5er9rvNxlJXFdm+NuteJ7/YffHlffBilYarjTaWV
h+SSpyEeltkqJ5D109FjM2UkendmrGyrnqcusrlqJ/QAyKLTWQFv5VZiWiXy43Ve
9Gp0sLp58Abaa3a/cGt7JQ==
-----END PRIVATE KEY-----

More junk...
"""

TEST_CERT_BUNDLE_PEM = b"""
Here's a cert bundle.

-----BEGIN CERTIFICATE-----
MIIFYDCCBEigAwIBAgIQQAF3ITfU6UK47naqPGQKtzANBgkqhkiG9w0BAQsFADA/
MSQwIgYDVQQKExtEaWdpdGFsIFNpZ25hdHVyZSBUcnVzdCBDby4xFzAVBgNVBAMT
DkRTVCBSb290IENBIFgzMB4XDTIxMDEyMDE5MTQwM1oXDTI0MDkzMDE4MTQwM1ow
TzELMAkGA1UEBhMCVVMxKTAnBgNVBAoTIEludGVybmV0IFNlY3VyaXR5IFJlc2Vh
cmNoIEdyb3VwMRUwEwYDVQQDEwxJU1JHIFJvb3QgWDEwggIiMA0GCSqGSIb3DQEB
AQUAA4ICDwAwggIKAoICAQCt6CRz9BQ385ueK1coHIe+3LffOJCMbjzmV6B493XC
ov71am72AE8o295ohmxEk7axY/0UEmu/H9LqMZshftEzPLpI9d1537O4/xLxIZpL
wYqGcWlKZmZsj348cL+tKSIG8+TA5oCu4kuPt5l+lAOf00eXfJlII1PoOK5PCm+D
LtFJV4yAdLbaL9A4jXsDcCEbdfIwPPqPrt3aY6vrFk/CjhFLfs8L6P+1dy70sntK
4EwSJQxwjQMpoOFTJOwT2e4ZvxCzSow/iaNhUd6shweU9GNx7C7ib1uYgeGJXDR5
bHbvO5BieebbpJovJsXQEOEO3tkQjhb7t/eo98flAgeYjzYIlefiN5YNNnWe+w5y
sR2bvAP5SQXYgd0FtCrWQemsAXaVCg/Y39W9Eh81LygXbNKYwagJZHduRze6zqxZ
Xmidf3LWicUGQSk+WT7dJvUkyRGnWqNMQB9GoZm1pzpRboY7nn1ypxIFeFntPlF4
FQsDj43QLwWyPntKHEtzBRL8xurgUBN8Q5N0s8p0544fAQjQMNRbcTa0B7rBMDBc
SLeCO5imfWCKoqMpgsy6vYMEG6KDA0Gh1gXxG8K28Kh8hjtGqEgqiNx2mna/H2ql
PRmP6zjzZN7IKw0KKP/32+IVQtQi0Cdd4Xn+GOdwiK1O5tmLOsbdJ1Fu/7xk9TND
TwIDAQABo4IBRjCCAUIwDwYDVR0TAQH/BAUwAwEB/zAOBgNVHQ8BAf8EBAMCAQYw
SwYIKwYBBQUHAQEEPzA9MDsGCCsGAQUFBzAChi9odHRwOi8vYXBwcy5pZGVudHJ1
c3QuY29tL3Jvb3RzL2RzdHJvb3RjYXgzLnA3YzAfBgNVHSMEGDAWgBTEp7Gkeyxx
+tvhS5B1/8QVYIWJEDBUBgNVHSAETTBLMAgGBmeBDAECATA/BgsrBgEEAYLfEwEB
ATAwMC4GCCsGAQUFBwIBFiJodHRwOi8vY3BzLnJvb3QteDEubGV0c2VuY3J5cHQu
b3JnMDwGA1UdHwQ1MDMwMaAvoC2GK2h0dHA6Ly9jcmwuaWRlbnRydXN0LmNvbS9E
U1RST09UQ0FYM0NSTC5jcmwwHQYDVR0OBBYEFHm0WeZ7tuXkAXOACIjIGlj26Ztu
MA0GCSqGSIb3DQEBCwUAA4IBAQAKcwBslm7/DlLQrt2M51oGrS+o44+/yQoDFVDC
5WxCu2+b9LRPwkSICHXM6webFGJueN7sJ7o5XPWioW5WlHAQU7G75K/QosMrAdSW
9MUgNTP52GE24HGNtLi1qoJFlcDyqSMo59ahy2cI2qBDLKobkx/J3vWraV0T9VuG
WCLKTVXkcGdtwlfFRjlBz4pYg1htmf5X6DYO8A4jqv2Il9DjXA6USbW1FzXSLr9O
he8Y4IWS6wY7bCkjCWDcRQJMEhg76fsO3txE+FiYruq9RUWhiF1myv4Q6W+CyBFC
Dfvp7OOGAN6dEOM4+qR9sdjoSYKEBpsr6GtPAQw4dy753ec5
-----END CERTIFICATE-----

Another entry:
-----BEGIN CERTIFICATE-----
MIIFFjCCAv6gAwIBAgIRAJErCErPDBinU/bWLiWnX1owDQYJKoZIhvcNAQELBQAw
TzELMAkGA1UEBhMCVVMxKTAnBgNVBAoTIEludGVybmV0IFNlY3VyaXR5IFJlc2Vh
cmNoIEdyb3VwMRUwEwYDVQQDEwxJU1JHIFJvb3QgWDEwHhcNMjAwOTA0MDAwMDAw
WhcNMjUwOTE1MTYwMDAwWjAyMQswCQYDVQQGEwJVUzEWMBQGA1UEChMNTGV0J3Mg
RW5jcnlwdDELMAkGA1UEAxMCUjMwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEK
AoIBAQC7AhUozPaglNMPEuyNVZLD+ILxmaZ6QoinXSaqtSu5xUyxr45r+XXIo9cP
R5QUVTVXjJ6oojkZ9YI8QqlObvU7wy7bjcCwXPNZOOftz2nwWgsbvsCUJCWH+jdx
sxPnHKzhm+/b5DtFUkWWqcFTzjTIUu61ru2P3mBw4qVUq7ZtDpelQDRrK9O8Zutm
NHz6a4uPVymZ+DAXXbpyb/uBxa3Shlg9F8fnCbvxK/eG3MHacV3URuPMrSXBiLxg
Z3Vms/EY96Jc5lP/Ooi2R6X/ExjqmAl3P51T+c8B5fWmcBcUr2Ok/5mzk53cU6cG
/kiFHaFpriV1uxPMUgP17VGhi9sVAgMBAAGjggEIMIIBBDAOBgNVHQ8BAf8EBAMC
AYYwHQYDVR0lBBYwFAYIKwYBBQUHAwIGCCsGAQUFBwMBMBIGA1UdEwEB/wQIMAYB
Af8CAQAwHQYDVR0OBBYEFBQusxe3WFbLrlAJQOYfr52LFMLGMB8GA1UdIwQYMBaA
FHm0WeZ7tuXkAXOACIjIGlj26ZtuMDIGCCsGAQUFBwEBBCYwJDAiBggrBgEFBQcw
AoYWaHR0cDovL3gxLmkubGVuY3Iub3JnLzAnBgNVHR8EIDAeMBygGqAYhhZodHRw
Oi8veDEuYy5sZW5jci5vcmcvMCIGA1UdIAQbMBkwCAYGZ4EMAQIBMA0GCysGAQQB
gt8TAQEBMA0GCSqGSIb3DQEBCwUAA4ICAQCFyk5HPqP3hUSFvNVneLKYY611TR6W
PTNlclQtgaDqw+34IL9fzLdwALduO/ZelN7kIJ+m74uyA+eitRY8kc607TkC53wl
ikfmZW4/RvTZ8M6UK+5UzhK8jCdLuMGYL6KvzXGRSgi3yLgjewQtCPkIVz6D2QQz
CkcheAmCJ8MqyJu5zlzyZMjAvnnAT45tRAxekrsu94sQ4egdRCnbWSDtY7kh+BIm
lJNXoB1lBMEKIq4QDUOXoRgffuDghje1WrG9ML+Hbisq/yFOGwXD9RiX8F6sw6W4
avAuvDszue5L3sz85K+EC4Y/wFVDNvZo4TYXao6Z0f+lQKc0t8DQYzk1OXVu8rp2
yJMC6alLbBfODALZvYH7n7do1AZls4I9d1P4jnkDrQoxB3UqQ9hVl3LEKQ73xF1O
yK5GhDDX8oVfGKF5u+decIsH4YaTw7mP3GFxJSqv3+0lUFJoi5Lc5da149p90Ids
hCExroL1+7mryIkXPeFM5TgO9r0rvZaBFOvV2z0gp35Z0+L4WPlbuEjN/lxPFin+
HlUjr8gRsI3qfJOQFy/9rKIJR0Y/8Omwt/8oTWgy1mdeHmmjk7j1nYsvC9JSQ6Zv
MldlTTKB3zhThV1+XWYp6rjd5JW1zbVWEkLNxE7GJThEUG3szgBVGP7pSWTUTsqX
nLRbwHOoq7hHwg==
-----END CERTIFICATE-----

And another:
-----BEGIN CERTIFICATE-----
MIIGUDCCBTigAwIBAgISBI+q2t/HklIfG4tA8/oK77gKMA0GCSqGSIb3DQEBCwUA
MDIxCzAJBgNVBAYTAlVTMRYwFAYDVQQKEw1MZXQncyBFbmNyeXB0MQswCQYDVQQD
EwJSMzAeFw0yMzA2MjAwNDUwNDdaFw0yMzA5MTgwNDUwNDZaMBoxGDAWBgNVBAMT
D3Jldmlld2JvYXJkLm9yZzCCAiIwDQYJKoZIhvcNAQEBBQADggIPADCCAgoCggIB
AL6ZFX3tNiWkZhU/2I1tjYqdnZkRX8XQdg4eEe7zikcQftltWmtgdmkBjSE2HaIk
Y89k23LfL5DHgQeEWnZU1My51YpvAqnUm/sQ+wipzmbPJ9IcKy9YJ3gvkwtZmNXE
RvJUN9r5Vl45RepytRGhhF4F4K4eCubvN798XEbgqghj5Z1JtaUk3ewHSRW0gGMU
nOQhBtN7NXsQh3GNu/caNm4yvXHmqoxrop+be/ZYJRhthMFh0rgFEAsu7TeAUHnr
FTseFj0Rj7AhcdAg5LzdkGFhq4heeHNGQgz6M+fBK189tlRFqsl8C4augC0tTE9Z
a/CeBbHdhGAsoRD6DGsuHdvwu+WmQOZbgNqEuwaFpYfuJpRwlf227Hx6gswFbBfz
Dj9YB8QX/1/C4IDvmy58oFwxqAObRJTLWt9VW5zeOITpRFhoRtcZqZMfLLrN841m
c5ybP7ShKoLVP9BWyQ87Y3pDx17xeS6Kh/fB4IEiCMdEGnmUQ7aWfBROQfDD7cGe
dVk+14VLcy/McvLnc9PNWMEEeI2yO/ZCawdGcUWIRkN0LUTQRKYlm+fVgxjhhDbU
LVb8ceH3W7POKhCIp0G7c8V+eXOaSkOBlsQRr8IoD9urhyXH4tuZ46uPb6SAk2bt
cd1MyuU/K8960M0a8G4+WBOVQK2QsvCH9JKn+188zq8/AgMBAAGjggJ2MIICcjAO
BgNVHQ8BAf8EBAMCBaAwHQYDVR0lBBYwFAYIKwYBBQUHAwEGCCsGAQUFBwMCMAwG
A1UdEwEB/wQCMAAwHQYDVR0OBBYEFBY+a+mumhqtoVXIyLDyBpvM0CNoMB8GA1Ud
IwQYMBaAFBQusxe3WFbLrlAJQOYfr52LFMLGMFUGCCsGAQUFBwEBBEkwRzAhBggr
BgEFBQcwAYYVaHR0cDovL3IzLm8ubGVuY3Iub3JnMCIGCCsGAQUFBzAChhZodHRw
Oi8vcjMuaS5sZW5jci5vcmcvMH8GA1UdEQR4MHaCEHJldmlldy1ib2FyZC5uZXSC
EHJldmlldy1ib2FyZC5vcmeCD3Jldmlld2JvYXJkLm9yZ4IUd3d3LnJldmlldy1i
b2FyZC5uZXSCFHd3dy5yZXZpZXctYm9hcmQub3JnghN3d3cucmV2aWV3Ym9hcmQu
b3JnMBMGA1UdIAQMMAowCAYGZ4EMAQIBMIIBBAYKKwYBBAHWeQIEAgSB9QSB8gDw
AHYAejKMVNi3LbYg6jjgUh7phBZwMhOFTTvSK8E6V6NS61IAAAGI11sJQwAABAMA
RzBFAiEAigvbRUqjNAK/OtlO3D2gbKEzGrI6cjNy2Gzu+9MRLaICIHoQN5y/2XvS
Lzw2r6aPyaC12jzYPcreUkzhivIDAmegAHYAtz77JN+cTbp18jnFulj0bF38Qs96
nzXEnh0JgSXttJkAAAGI11sJTwAABAMARzBFAiACLdcZBHQyjxoC66VuL1Ml7teR
i8RWM4ItVxXTVdstbgIhALRj4ubSbynvZlF9coEvzZwRG0NhhVP15y5EcktHEZGW
MA0GCSqGSIb3DQEBCwUAA4IBAQBbPEpF1kIkua+U/u+3zxel/YE4B43nHi8VI8Lx
Pxzz1u9YsL9q/Kv7+MTR/lqxdYm9+Tgy581mq8GVl4vyXZGS6Z4QM+NqbpUYkbKE
Is9ckyoby3lVet00iVIObU8j9zxNpc6bWdusmuSIKwy4dJusI+wRx0m79fXmffUT
HFXdjGoo/7WyKHKpZIrUiQCEaxyg0d/PR0h6L53Uty5lzC8UqqQPVsYKHde41tgd
pYqtPwuigULIIwPjyCH5aqN9gsJL1mj0oaUKwat8GD+xRAexcaaXtHvStlWMzDmD
R/VelCH+wHaDm4EoroX1lKyRi94bOMDXcDVo0kqBt65rYwrK
-----END CERTIFICATE-----"""

TEST_SHA1 = 'F2:35:0F:BB:34:40:84:78:8B:20:1D:40:B1:4A:17:0C:DE:36:2F:D5'
TEST_SHA1_2 = '00:11:22:33:44:55:66:77:88:99:AA:BB:CC:DD:EE:FF:00:11:22:33'

TEST_SHA256 = (
    '79:19:70:AE:A6:1B:EB:BC:35:7C:B8:54:B1:6A:AD:79:FF:F7:28:69:02:5E:C3:'
    '6F:B3:C2:B4:FD:84:66:DF:8F'
)
TEST_SHA256_2 = (
    '00:11:22:33:44:55:66:77:88:99:AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:'
    '77:88:99:AA:BB:CC:DD:EE:FF'
)


class CertificateTestCase(TestCase):
    """Base test case for certificate unit tests.

    Version Aded:
        6.0
    """

    #: Path to the base cert testdata directory.
    base_testdata_dir: Final[str] = os.path.abspath(
        os.path.join(__file__, '..', 'testdata'))

    def build_x509_cert(
        self,
        *,
        subject: str = 'example.com',
        issuer: str = 'example.com',
        not_valid_before_delta: timedelta = -timedelta(days=1),
        not_valid_after_delta: timedelta = timedelta(days=1),
    ) -> x509.Certificate:
        """Return a new Cryptography X.509 certificate object.

        Args:
            subject (str, optional):
                The subject name for the certificate.

            issuer (str, optional):
                The issuer name for the certificate.

            not_valid_before_delta (datetime.timedelta, optional):
                The delta relative to now indicating when the certificate is
                first valid.

            not_valid_after_delta (datetime.timedelta, optional):
                The delta relative to now indicating when the certificate
                expires.

        Returns:
            cryptography.x509.Certificate:
            The resulting certificate.
        """
        private_key = rsa.generate_private_key(public_exponent=65537,
                                               key_size=2048)

        return (
            x509.CertificateBuilder()
            .subject_name(x509.Name([
                x509.NameAttribute(NameOID.COMMON_NAME, subject),
            ]))
            .issuer_name(x509.Name([
                x509.NameAttribute(NameOID.COMMON_NAME, issuer),
            ]))
            .not_valid_before(datetime.utcnow() + not_valid_before_delta)
            .not_valid_after(datetime.utcnow() + not_valid_after_delta)
            .serial_number(x509.random_serial_number())
            .public_key(private_key.public_key())
            .sign(private_key=private_key,
                  algorithm=hashes.SHA256())
        )

    def build_x509_cert_pem(self, **kwargs) -> bytes:
        """Return a new certificate as PEM content.

        Args:
            **kwargs (dict):
                Keyword arguments to pass to :py:meth:`build_x509_cert`.

        Returns:
            bytes:
            The PEM content for the certificate.
        """
        return self.build_x509_cert(**kwargs).public_bytes(Encoding.PEM)
