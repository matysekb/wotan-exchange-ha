"""Install the verified official Linux ARM64 release during image build."""
import hashlib
import io
import struct
import urllib.request
import zipfile
from pathlib import Path

VERSION = 'v0.0.16'
ASSET = 'tunnel-client-v0.0.16-linux-arm64.zip'
SHA256 = '963d0384aaa7c798778479c45673f9051a4039dd891aef8f8978d2a1a628b74f'
URL = f'https://github.com/openai/tunnel-client/releases/download/{VERSION}/{ASSET}'


def main():
    data = urllib.request.urlopen(URL, timeout=120).read()
    if hashlib.sha256(data).hexdigest() != SHA256:
        raise RuntimeError('Tunnel release checksum mismatch')
    archive = zipfile.ZipFile(io.BytesIO(data))
    binary = archive.read('tunnel-client')
    if binary[:4] != b'\x7fELF' or binary[4:6] != b'\x02\x01' or struct.unpack('<H', binary[18:20])[0] != 183:
        raise RuntimeError('Expected Linux ELF64 little-endian AArch64')
    dest = Path('/usr/local/bin/tunnel-client')
    dest.write_bytes(binary)
    dest.chmod(0o755)
    notices = Path('/usr/local/share/tunnel-client')
    notices.mkdir(parents=True, exist_ok=True)
    for name in ('LICENSE', 'NOTICE', 'tunnel-client-v0.0.16-linux-arm64-licenses.txt'):
        (notices / name).write_bytes(archive.read(name))


if __name__ == '__main__':
    main()
