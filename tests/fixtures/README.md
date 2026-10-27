# Test-only certificate

`test-ca.pem` is a generated self-signed public CA used only to exercise certificate
parsing and normalization. It does not identify any organization. Its private key
is not tracked. Never install this fixture as a real trusted organization CA.
