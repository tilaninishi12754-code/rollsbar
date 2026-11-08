import base64,hashlib,paramiko
HOST_FINGERPRINT="USxyLBp+ya1El/PT7cq9PKmpOUHd+uLBF1uCGvXnv94="
class PinnedHostKey(paramiko.MissingHostKeyPolicy):
    def missing_host_key(self, client, hostname, key):
        if base64.b64encode(hashlib.sha256(key.asbytes()).digest()).decode()!=HOST_FINGERPRINT: raise RuntimeError("SSH key mismatch")
